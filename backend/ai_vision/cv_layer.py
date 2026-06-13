import json
import os
import random
import re
import time
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel

MODEL = "gemini-2.5-flash"

_PIN_DIAGRAMS_DIR = Path(__file__).parent / "pin_diagrams"
_CN8_9_PATH  = _PIN_DIAGRAMS_DIR / "cn8_9.PNG"
_CN7_10_PATH = _PIN_DIAGRAMS_DIR / "cn7_10.PNG"

# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class Component(BaseModel):
    id: str             # NUCLEO | CENTRAL_PERFBOARD | HEX_NW | HEX_NE | HEX_E | HEX_SE | HEX_S | HEX_SW
    type: str           # mcu_development_board | perfboard | sensor_module | other
    hardware_model: str # e.g. "STM32 Nucleo-144", "PDM Mic breakout", "custom perfboard"

class Connection(BaseModel):
    from_comp:    str           # source component id
    from_pin:     str           # pin function on source: VCC | GND | CLK | DAT
    to_comp:      str           # destination component id (NUCLEO or CENTRAL_PERFBOARD)
    to_header:    str           # CN7 | CN8 | CN9 | CN10 | PERFBOARD
    to_pin_label: str           # exact GPIO label from pinout diagram, e.g. PE_9, 3V3, GND
    wire_color:   str           # observed wire color

class CircuitAnalysis(BaseModel):
    circuit_description: str
    components: list[Component]
    connections: list[Connection]

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """
You are an expert embedded systems vision engineer performing precise pin-level wiring analysis of a prototype STM32 assembly.

━━━ IMAGE CONTEXT ━━━
You are given THREE images:
  Image 1 — Hardware photo (top-down): hexagonal 3D-printed frame containing:
    • NUCLEO: STM32 Nucleo-144 development board (large white PCB, blue STM logo, dual-row
              female morpho headers on left AND right sides, ST-LINK programmer at top)
    • CENTRAL_PERFBOARD: small custom perfboard mounted on top of the Nucleo, acting as
              power/GND distribution hub routing 3V3 and GND to all six mics
    • HEX_NW, HEX_NE, HEX_E, HEX_SE, HEX_S, HEX_SW: six PDM microphone breakout boards
              (small black PCBs with 4-pin JST connectors), one at each hexagon vertex,
              clockwise from top-left
    • Each mic has a 4-wire harness from its JST jack: VCC (red), GND (black/blue), CLK (yellow), DAT (blue/other)

  Image 2 — CN8 (top) + CN9 (bottom) pinout diagram: LEFT-SIDE morpho headers of the Nucleo-144.
             Use this to identify exact GPIO/power labels for any wire terminating on the left headers.

  Image 3 — CN7 (top) + CN10 (bottom) pinout diagram: RIGHT-SIDE morpho headers of the Nucleo-144.
             Use this to identify exact GPIO/power labels for any wire terminating on the right headers.

━━━ YOUR TASK ━━━
Produce ONE connection entry per individual wire. For each wire:
  1. Identify its source component and the PDM pin function (VCC / GND / CLK / DAT)
  2. Trace it visually to where it terminates on the Nucleo header or perfboard
  3. Cross-reference that physical header position with the pinout diagram (Images 2 or 3)
     to determine the exact pin label (e.g. PE_9, PC_7, 3V3, GND)
  4. Record the observed wire color

━━━ RULES ━━━
- Output exactly 8 components: NUCLEO, CENTRAL_PERFBOARD, and all 6 HEX_* mics
- Output exactly 24 connections: 4 wires × 6 mics (VCC, GND, CLK, DAT each)
  • VCC and GND wires from mics typically go to CENTRAL_PERFBOARD first, not directly to NUCLEO
  • CLK and DAT wires go directly to NUCLEO morpho header pins
- to_header must be one of: CN7, CN8, CN9, CN10, PERFBOARD
- to_pin_label must be the exact label from the pinout diagram (e.g. PE_9, PA_3, 3V3, GND)
  Use "UNKNOWN" only if the wire endpoint is genuinely not traceable
- wire_color must be the observed color of that specific wire
- Return ONLY the raw JSON object — no markdown fences, no extra text
""".strip()

# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

_RETRYABLE = ("429", "quota", "resource exhausted", "rate limit", "too many requests")
_MAX_RETRIES = 5
_BASE_DELAY = 2.0


def _is_retryable(exc: Exception) -> tuple[bool, float]:
    msg = str(exc).lower()
    if not any(k in msg for k in _RETRYABLE):
        return False, 0.0
    m = re.search(r"retry.after['\"]?\s*:\s*['\"]?(\d+)", msg, re.IGNORECASE)
    return True, float(m.group(1)) if m else 0.0


def _load_bytes(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _call_gemini(image_bytes: bytes, mime_type: str) -> CircuitAnalysis:
    api_key = os.environ.get("GEMINI_API_KEY")
    client  = genai.Client(api_key=api_key)
    delay   = _BASE_DELAY

    cn8_9_bytes  = _load_bytes(_CN8_9_PATH)
    cn7_10_bytes = _load_bytes(_CN7_10_PATH)

    contents = [
        types.Part.from_text(text=_ANALYSIS_PROMPT),
        types.Part.from_text(text="Image 1 — Hardware photo:"),
        types.Part.from_bytes(data=image_bytes,  mime_type=mime_type),
        types.Part.from_text(text="Image 2 — CN8 (left-top) + CN9 (left-bottom) pinout:"),
        types.Part.from_bytes(data=cn8_9_bytes,  mime_type="image/png"),
        types.Part.from_text(text="Image 3 — CN7 (right-top) + CN10 (right-bottom) pinout:"),
        types.Part.from_bytes(data=cn7_10_bytes, mime_type="image/png"),
    ]

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CircuitAnalysis,
                    temperature=0.1,
                ),
            )
            if response.parsed is not None:
                return response.parsed
            return CircuitAnalysis.model_validate(json.loads(response.text))

        except Exception as exc:
            retryable, hint = _is_retryable(exc)
            if not retryable or attempt == _MAX_RETRIES - 1:
                raise
            sleep_for = hint if hint > 0 else delay + random.uniform(0, 1)
            print(f"[cv_layer] rate-limited — waiting {sleep_for:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
            time.sleep(sleep_for)
            delay = min(delay * 2, 60)

    raise RuntimeError("unreachable")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_image_bytes(image_path: str) -> bytes:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return _load_bytes(path)


def _mime_from_path(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "image/jpeg"
    )

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_board(image_path: str) -> dict:
    image_bytes = _load_image_bytes(image_path)
    return _run_analysis(image_bytes, _mime_from_path(image_path))


def analyze_board_from_bytes(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    return _run_analysis(image_bytes, mime_type)


analyze_breadboard          = analyze_board
analyze_breadboard_from_bytes = analyze_board_from_bytes


def _run_analysis(image_bytes: bytes, mime_type: str) -> dict:
    result = _call_gemini(image_bytes, mime_type)
    return result.model_dump()
