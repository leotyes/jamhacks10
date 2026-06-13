import json
import os
import random
import re
import time
from pathlib import Path
from typing import Optional

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
    wire_id:        str
    signal_type:    str              # VCC | GND | CLK | DAT
    wire_color:     str
    from_comp:      str
    from_header:    Optional[str] = None   # CN7 | CN8 | CN9 | CN10 | PERFBOARD
    from_pin_label: str
    to_comp:        str
    to_header:      Optional[str] = None   # CN7 | CN8 | CN9 | CN10 | PERFBOARD
    to_pin_label:   str

class CircuitAnalysis(BaseModel):
    circuit_description: str
    components: list[Component]
    connections: list[Connection]

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_ANALYSIS_PROMPT = """
You are an expert embedded systems vision engineer. Your task is to produce a flat, relational netlist — one entry per visible physical wire segment — from photos of a prototype STM32 assembly.

━━━ IMAGE CONTEXT ━━━
You are given FOUR images:
  Image 1 — Side-view photo of the board assembly.
  Image 2 — Top-view photo of the same board assembly.
  Use both perspectives together to resolve depth, occlusion, and wire routing ambiguities.
  Image 3 — CN8/CN9 pinout diagram (LEFT morpho headers): reference for exact pin labels (e.g., 3V3, GND, PC_3, PE_9, PE_4).
  Image 4 — CN7/CN10 pinout diagram (RIGHT morpho headers): reference for exact pin labels (e.g., PC_1, PC_5, PE_10, PE_12).

━━━ BOARD CONTEXT ━━━
The assembly consists of:
  • NUCLEO: STM32 Nucleo-144 development board with left (CN8/CN9) and right (CN7/CN10) morpho headers.
  • CENTRAL_PERFBOARD: a custom perfboard acting as a wiring hub — all 4 lines (VCC, GND, CLK, DAT) from each microphone may route here first before jumping onward to the NUCLEO, or wires may go directly to the NUCLEO. Detect what is physically present.
  • HEX_NW, HEX_NE, HEX_E, HEX_SE, HEX_S, HEX_SW (or however many are present): PDM microphone breakout boards at hexagonal vertices.

━━━ YOUR TASK ━━━
Enumerate every distinct visible wire segment. Each segment is an independent connection object with a unique wire_id. Assign signal_type (VCC, GND, CLK, or DAT) based on the wire's function in the circuit.

For each segment:
  1. Identify the physical origin component and, if it terminates on a header or perfboard, the specific header name and pin label.
  2. Identify the physical destination component and its header/pin label.
  3. Cross-reference header positions against the pinout diagrams (Images 3 and 4) for exact GPIO or power labels.
  4. Record the observed wire color.

━━━ RULES ━━━
- Report ALL components you can identify; do not limit to a fixed count.
- Report ALL wire segments you can see; do not limit to a fixed count.
- from_header / to_header must be one of: CN7, CN8, CN9, CN10, PERFBOARD, or null if not applicable.
- from_pin_label / to_pin_label must match the pinout diagram text exactly. Use "UNKNOWN" only when physically obscured.
- wire_id must be unique per segment (e.g. "W01", "W02", …).
- Your response MUST be a single JSON object with exactly these three top-level keys:
    {
      "circuit_description": "<one sentence summary>",
      "components": [ ... ],
      "connections": [ ... ]
    }
- Do NOT return a bare array. Do NOT wrap in markdown fences.
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


def _call_gemini(hw_images: list[tuple[bytes, str]]) -> CircuitAnalysis:
    api_key = os.environ.get("GEMINI_API_KEY")
    client  = genai.Client(api_key=api_key)
    delay   = _BASE_DELAY

    cn8_9_bytes  = _load_bytes(_CN8_9_PATH)
    cn7_10_bytes = _load_bytes(_CN7_10_PATH)

    labels = ["Side-view", "Top-view"] + [f"Hardware view {i+1}" for i in range(2, len(hw_images))]
    contents = [types.Part.from_text(text=_ANALYSIS_PROMPT)]
    for i, (img_bytes, mime_type) in enumerate(hw_images):
        contents.append(types.Part.from_text(text=f"Image {i + 1} — {labels[i]} photo:"))
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
    ref_offset = len(hw_images) + 1
    contents += [
        types.Part.from_text(text=f"Image {ref_offset} — CN8/CN9 pinout (LEFT headers):"),
        types.Part.from_bytes(data=cn8_9_bytes,  mime_type="image/png"),
        types.Part.from_text(text=f"Image {ref_offset + 1} — CN7/CN10 pinout (RIGHT headers):"),
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

def _mime_from_path(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        ext, "image/jpeg"
    )

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_HW_STEMS = ("side-view", "top-view")


def analyze_board(project_folder: str) -> dict:
    """Analyze a project folder containing side-view and top-view photos."""
    folder = Path(project_folder)
    hw_images: list[tuple[bytes, str]] = []
    for stem in _HW_STEMS:
        matches = sorted(folder.glob(f"{stem}.*"))
        if not matches:
            raise FileNotFoundError(f"No image matching '{stem}.*' in {folder}")
        path = matches[0]
        hw_images.append((_load_bytes(path), _mime_from_path(str(path))))
    return _call_gemini(hw_images).model_dump()


def analyze_board_from_bytes(images: list[tuple[bytes, str]]) -> dict:
    """Analyze pre-loaded image bytes. Each tuple is (image_bytes, mime_type)."""
    return _call_gemini(images).model_dump()


analyze_breadboard            = analyze_board
analyze_breadboard_from_bytes = analyze_board_from_bytes
