from dotenv import load_dotenv
load_dotenv()
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

MODEL = "gemini-3.5-flash"

_PIN_DIAGRAMS_DIR = Path(__file__).parent / "pin_diagrams"

# ---------------------------------------------------------------------------
# Schema for pin-diagram folder resolution
# ---------------------------------------------------------------------------

class PinDiagramResolution(BaseModel):
    folder_name: str          # exact name of the chosen subfolder under pin_diagrams/
    diagram_files: list[str]  # ordered list of filenames inside that folder to use as reference images
    description: str          # short human-readable rationale for the choice

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

# Built dynamically by _build_analysis_prompt() based on resolved diagram files.
_ANALYSIS_PROMPT_TEMPLATE = """
You are an expert embedded systems vision engineer. Your task is to produce a flat, relational netlist — one entry per visible physical wire segment — from photos of a prototype board assembly.

━━━ IMAGE CONTEXT ━━━
You are given {total_images} images:
{hw_image_labels}
  Use both perspectives together to resolve depth, occlusion, and wire routing ambiguities.
{diagram_image_labels}

━━━ BOARD CONTEXT ━━━
The assembly consists of:
  • NUCLEO: The MCU development board. Reference the pinout diagrams provided to identify exact header and pin labels.
  • CENTRAL_PERFBOARD: a custom perfboard acting as a wiring hub — all 4 lines (VCC, GND, CLK, DAT) from each microphone may route here first before jumping onward to the NUCLEO, or wires may go directly to the NUCLEO. Detect what is physically present.
  • HEX_NW, HEX_NE, HEX_E, HEX_SE, HEX_S, HEX_SW (or however many are present): PDM microphone breakout boards at hexagonal vertices.
{parts_context}
━━━ YOUR TASK ━━━
Enumerate every distinct visible wire segment. Each segment is an independent connection object with a unique wire_id. Assign signal_type (VCC, GND, CLK, or DAT) based on the wire's function in the circuit.

For each segment:
  1. Identify the physical origin component and, if it terminates on a header or perfboard, the specific header name and pin label.
  2. Identify the physical destination component and its header/pin label.
  3. Cross-reference header positions against the pinout diagrams provided for exact GPIO or power labels.
  4. Record the observed wire color.

━━━ RULES ━━━
- Report ALL components you can identify; do not limit to a fixed count.
- Report ALL wire segments you can see; do not limit to a fixed count.
- from_header / to_header must be one of: CN7, CN8, CN9, CN10, PERFBOARD, or null if not applicable.
- from_pin_label / to_pin_label must match the pinout diagram text exactly. Use "UNKNOWN" only when physically obscured.
- wire_id must be unique per segment (e.g. "W01", "W02", …).
- Your response MUST be a single JSON object with exactly these three top-level keys:
    {{
      "circuit_description": "<one sentence summary>",
      "components": [ ... ],
      "connections": [ ... ]
    }}
- Do NOT return a bare array. Do NOT wrap in markdown fences.
""".strip()


def _build_analysis_prompt(
    num_hw_images: int,
    diagram_filenames: list[str],
    parts_info: dict | None = None,
) -> str:
    """Render the analysis prompt with dynamic image indices, diagram labels,
    and an optional section listing known component pin interfaces."""
    hw_labels = ["Side-view", "Top-view"] + [f"Hardware view {i+1}" for i in range(2, num_hw_images)]
    hw_image_labels = "".join(
        f"  Image {i+1} — {hw_labels[i]} photo of the board assembly.\n"
        for i in range(num_hw_images)
    )
    ref_offset = num_hw_images + 1
    diagram_image_labels = "".join(
        f"  Image {ref_offset + j} — Pinout diagram '{name}': reference for exact pin/header labels.\n"
        for j, name in enumerate(diagram_filenames)
    )
    total_images = num_hw_images + len(diagram_filenames)

    # Build the optional known-components section
    parts_context = ""
    if parts_info:
        lines = ["\n━━━ KNOWN COMPONENTS (from Bill of Materials) ━━━"]
        lines.append(
            "Use this information to correctly identify signal types when tracing wires "
            "to/from these components:"
        )
        for part_name, info in parts_info.items():
            if not isinstance(info, dict):
                continue
            pins = info.get("pins", [])
            notes = info.get("wiring_notes", "")
            pin_str = ", ".join(pins) if pins else "unknown"
            lines.append(f"  • {part_name}: pins = [{pin_str}]" + (f" — {notes}" if notes else ""))
        parts_context = "\n".join(lines) + "\n"

    return _ANALYSIS_PROMPT_TEMPLATE.format(
        total_images=total_images,
        hw_image_labels=hw_image_labels.rstrip(),
        diagram_image_labels=diagram_image_labels.rstrip(),
        parts_context=parts_context,
    )

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


def _resolve_pin_diagram_folder(client: genai.Client, mcu_type: str) -> PinDiagramResolution:
    """Ask Gemini to pick the best-matching pin_diagrams subfolder for the given mcu_type."""
    available_folders: dict[str, list[str]] = {}
    for folder in sorted(_PIN_DIAGRAMS_DIR.iterdir()):
        if folder.is_dir():
            available_folders[folder.name] = sorted(f.name for f in folder.iterdir() if f.is_file())

    folder_listing = json.dumps(available_folders, indent=2)
    resolution_prompt = (
        f"You are a hardware identification assistant.\n"
        f"The user has an MCU/board described as: \"{mcu_type}\"\n\n"
        f"The following pin diagram folders are available (folder -> list of files inside):\n"
        f"{folder_listing}\n\n"
        f"Choose the single best-matching folder for this MCU type. "
        f"Return the exact folder_name, an ordered list of diagram_files (all files in that folder "
        f"that should be used as pinout reference images, in a logical order), "
        f"and a brief description explaining your choice."
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[types.Part.from_text(text=resolution_prompt)],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PinDiagramResolution,
            temperature=0.0,
        ),
    )
    if response.parsed is not None:
        resolution: PinDiagramResolution = response.parsed
    else:
        resolution = PinDiagramResolution.model_validate(json.loads(response.text))

    print(f"[cv_layer] resolved pin diagrams: folder='{resolution.folder_name}', "
          f"files={resolution.diagram_files} — {resolution.description}")
    print(resolution)
    return resolution


def _call_gemini(
    hw_images: list[tuple[bytes, str]],
    mcu_type: str = "stm32",
    parts_info: dict | None = None,
) -> CircuitAnalysis:
    api_key = os.environ.get("GEMINI_API_KEY")
    client  = genai.Client(api_key=api_key)
    delay   = _BASE_DELAY

    # --- Step 1: resolve which pin diagram folder & files to use ---
    resolution   = _resolve_pin_diagram_folder(client, mcu_type)
    diagram_dir  = _PIN_DIAGRAMS_DIR / resolution.folder_name
    diagram_files = resolution.diagram_files  # ordered list of filenames

    # --- Step 2: build dynamic prompt & content list ---
    analysis_prompt = _build_analysis_prompt(len(hw_images), diagram_files, parts_info=parts_info)

    hw_labels = ["Side-view", "Top-view"] + [f"Hardware view {i+1}" for i in range(2, len(hw_images))]
    contents = [types.Part.from_text(text=analysis_prompt)]
    for i, (img_bytes, mime_type) in enumerate(hw_images):
        contents.append(types.Part.from_text(text=f"Image {i + 1} — {hw_labels[i]} photo:"))
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

    ref_offset = len(hw_images) + 1
    for j, fname in enumerate(diagram_files):
        diagram_path = diagram_dir / fname
        diagram_bytes = _load_bytes(diagram_path)
        mime = _mime_from_path(fname)
        contents.append(types.Part.from_text(text=f"Image {ref_offset + j} — Pinout diagram '{fname}':"))
        contents.append(types.Part.from_bytes(data=diagram_bytes, mime_type=mime))

    # --- Step 3: main circuit analysis call (with retries) ---
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


def analyze_board(project_folder: str, mcu_type: str = "nucleoh7a3ziq", parts_info: dict | None = None) -> dict:
    """Analyze a project folder containing side-view and top-view photos."""
    folder = Path(project_folder)
    hw_images: list[tuple[bytes, str]] = []
    for stem in _HW_STEMS:
        matches = sorted(folder.glob(f"{stem}.*"))
        if not matches:
            raise FileNotFoundError(f"No image matching '{stem}.*' in {folder}")
        path = matches[0]
        hw_images.append((_load_bytes(path), _mime_from_path(str(path))))
    return _call_gemini(hw_images, mcu_type=mcu_type, parts_info=parts_info).model_dump()


def analyze_board_from_bytes(
    images: list[tuple[bytes, str]],
    mcu_type: str = "nucleoh7a3ziq",
    parts_info: dict | None = None,
) -> dict:
    """Analyze pre-loaded image bytes. Each tuple is (image_bytes, mime_type)."""
    return _call_gemini(images, mcu_type=mcu_type, parts_info=parts_info).model_dump()


analyze_breadboard            = analyze_board
analyze_breadboard_from_bytes = analyze_board_from_bytes
