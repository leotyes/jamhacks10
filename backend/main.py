from dotenv import load_dotenv
load_dotenv()

import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ai_vision.cv_layer import analyze_breadboard_from_bytes
from schematic_generator import simplify_to_production, generate_netlist
from schematic_geometry_generator import generate_kicad_pcb
from hex_mic_array_generator import generate_hex_mic_board
try:
    from services.ioc_parser import router as ioc_parser_router, parse_ioc_content
    from services.oauth3legtest import router as oauth3_router, get_access_token, product_search, enrich_product
    _ioc_parser_available = True
except Exception:
    _ioc_parser_available = False
    parse_ioc_content = None
    get_access_token = None
    product_search = None
from google import genai

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

app = FastAPI(title="Hardware Recon AI Backend")

FUSIONPROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "FusionPrompt.txt"
fusionprompt = FUSIONPROMPT_PATH.read_text(encoding="utf-8")

UPLOAD_DIR = "uploads"
SCHEMATICS_DIR = "schematics"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SCHEMATICS_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------

class ReconciliationResponse(BaseModel):
    confidence: float
    reasoning_log: str
    netlist: dict
    schematic_url: Optional[str] = None
    geometry_url: Optional[str] = None

class NetlistRequest(BaseModel):
    netlist: dict


# ---------- Endpoints ----------

@app.get("/")
def read_root():
    return {"message": "Hello World"}


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    image_bytes = await file.read()
    result = analyze_breadboard_from_bytes([(image_bytes, file.content_type)])
    return result


@app.post("/api/reconcile", response_model=ReconciliationResponse)
async def reconcile_hardware(
    ioc_file: UploadFile = File(...),
    side_image: UploadFile = File(...),
    top_image: UploadFile = File(...),
    parts: Optional[str] = Form(None)
):
    if not ioc_file.filename.endswith('.ioc'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone A upload must be a valid STM32 .ioc configuration file."
        )
    if not side_image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Side image must be a valid JPEG or PNG image."
        )
    if not top_image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Top image must be a valid JPEG or PNG image."
        )

    try:
        ioc_contents = await ioc_file.read()
        side_image_bytes = await side_image.read()
        top_image_bytes = await top_image.read()

        session_id = str(uuid.uuid4())
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        with open(os.path.join(session_dir, ioc_file.filename), "wb") as f:
            f.write(ioc_contents)
        with open(os.path.join(session_dir, side_image.filename), "wb") as f:
            f.write(side_image_bytes)
        with open(os.path.join(session_dir, top_image.filename), "wb") as f:
            f.write(top_image_bytes)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File I/O failure: {str(e)}"
        )

    parsed_parts = []
    if parts:
        try:
            parsed_parts = json.loads(parts)
        except json.JSONDecodeError:
            pass

    # ioc_text = ioc_contents.decode("utf-8", errors="replace")
    # ioc_result = parse_ioc_content(ioc_text) if parse_ioc_content else ""
    ioc_result = """{
        "mcu": "STM32H7A3ZIT6Q",

        "pin_map": {
            "PC14-OSC32_IN": {
            "function": "RCC_OSC32_IN",
            "peripheral": "RCC",
            "semantic_hint": "clock_signal",
            "confidence": 0.99
            },
            "PC15-OSC32_OUT": {
            "function": "RCC_OSC32_OUT",
            "peripheral": "RCC",
            "semantic_hint": "clock_signal",
            "confidence": 0.99
            },
            "PH0-OSC_IN": {
            "function": "RCC_OSC_IN",
            "peripheral": "RCC",
            "semantic_hint": "clock_signal",
            "confidence": 0.99
            },
            "PH1-OSC_OUT": {
            "function": "RCC_OSC_OUT",
            "peripheral": "RCC",
            "semantic_hint": "clock_signal",
            "confidence": 0.99
            },
            "PC1": {
            "function": "DFSDM1_DATIN0",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PC3_C": {
            "function": "DFSDM1_DATIN1",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PC5": {
            "function": "DFSDM1_DATIN2",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PE4": {
            "function": "DFSDM1_DATIN3",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PE10": {
            "function": "DFSDM1_DATIN4",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PE12": {
            "function": "DFSDM1_DATIN5",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PE9": {
            "function": "DFSDM1_CKOUT",
            "peripheral": "DFSDM1",
            "semantic_hint": "digital_bus",
            "confidence": 0.98
            },
            "PD8": {
            "function": "USART3_TX",
            "peripheral": "USART3",
            "semantic_hint": "serial_communication",
            "confidence": 0.99
            },
            "PD9": {
            "function": "USART3_RX",
            "peripheral": "USART3",
            "semantic_hint": "serial_communication",
            "confidence": 0.99
            }
        },

        "peripherals": {
            "USART3": {
            "TX": "PD8",
            "RX": "PD9"
            },
            "DFSDM1": {
            "DATIN0": "PC1",
            "DATIN1": "PC3_C",
            "DATIN2": "PC5",
            "DATIN3": "PE4",
            "DATIN4": "PE10",
            "DATIN5": "PE12",
            "CKOUT": "PE9"
            },
            "RCC": {
            "OSC32_IN": "PC14-OSC32_IN",
            "OSC32_OUT": "PC15-OSC32_OUT",
            "OSC_IN": "PH0-OSC_IN",
            "OSC_OUT": "PH1-OSC_OUT"
            }
        },

        "notes": [
            "No physical wiring inferred",
            "Power assumed to be handled externally by development board",
            "All mappings derived strictly from CubeMX configuration"
        ]
    }"""

    parts_search_results = {'4346 mems microphone': {'photo_url': 'https://mm.digikey.com/Volume0/opasdata/d220001/medias/images/4845/1528_4346.jpg', 'pins': ['VDD', 'GND', 'DAT', 'CLK'], 'wiring_notes': 'The Adafruit 4346 PDM Microphone Breakout connects via a 4-pin JST SH connector or solder pads. It requires a 1.8V to 3.3V power supply (VDD), ground (GND), a clock input (CLK) of 1 to 3.25 MHz, and provides a pulse density modulation data output (DAT). An on-board solder jumper allows selecting between Left and Right channels.'}}
    # if parsed_parts and get_access_token and product_search:
    #     try:
    #         token = get_access_token()
    #         for part in parsed_parts:
    #             try:
    #                 search_result = product_search(part, token)
    #                 products = search_result.get("Products", [])
    #                 if products:
    #                     parts_search_results[part] = enrich_product(products[0])
    #                 else:
    #                     parts_search_results[part] = None
    #             except Exception as e:
    #                 parts_search_results[part] = {"error": str(e)}
    #     except Exception as e:
    #         parts_search_results = {"error": f"DigiKey auth failed: {str(e)}"}

    # 1. CV — run the side and top photos together through the analysis pipeline,
    #    passing the enriched parts info so the model knows each component's pins.
    mcu_type = ""
    if ioc_result:
        try:
            clean_json = ioc_result.strip()
            if clean_json.startswith("```"):
                lines = clean_json.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_json = "\n".join(lines).strip()
            parsed = json.loads(clean_json)
            if isinstance(parsed, dict):
                mcu_type = parsed.get("mcu", "")
        except Exception as e:
            print(f"[ioc_parser] Failed to parse JSON from ioc_result: {e}")
    # cv_result = analyze_breadboard_from_bytes(
    #     [(side_image_bytes, side_image.content_type),
    #      (top_image_bytes, top_image.content_type)],
    #     mcu_type=mcu_type,
    #     parts_info=parts_search_results if isinstance(parts_search_results, dict) else None,
    # )
    cv_result = {'circuit_description': 'A hexagonal array of six Adafruit 4346 PDM microphones connected via a central routing perfboard to an STM32 Nucleo-H7A3ZI-Q development board.', 'components': [{'id': 'NUCLEO', 'type': 'MCU_BOARD', 'hardware_model': 'NUCLEO-H7A3ZI-Q'}, {'id': 'CENTRAL_PERFBOARD', 'type': 'PERFBOARD', 'hardware_model': 'CUSTOM_PERFBOARD'}, {'id': 'HEX_N', 'type': 'MICROPHONE_BREAKOUT', 'hardware_model': 'Adafruit_4346_PDM_Microphone'}, {'id': 'HEX_NE', 'type': 'MICROPHONE_BREAKOUT', 'hardware_model': 'Adafruit_4346_PDM_Microphone'}, {'id': 'HEX_SE', 'type': 'MICROPHONE_BREAKOUT', 'hardware_model': 'Adafruit_4346_PDM_Microphone'}, {'id': 'HEX_S', 'type': 'MICROPHONE_BREAKOUT', 'hardware_model': 'Adafruit_4346_PDM_Microphone'}, {'id': 'HEX_SW', 'type': 'MICROPHONE_BREAKOUT', 'hardware_model': 'Adafruit_4346_PDM_Microphone'}, {'id': 'HEX_NW', 'type': 'MICROPHONE_BREAKOUT', 'hardware_model': 'Adafruit_4346_PDM_Microphone'}], 'connections': [{'wire_id': 'W01', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'HEX_N', 'from_header': None, 'from_pin_label': 'VDD', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'VDD'}, {'wire_id': 'W02', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'HEX_N', 'from_header': None, 'from_pin_label': 'GND', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'GND'}, {'wire_id': 'W03', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'HEX_N', 'from_header': None, 'from_pin_label': 'CLK', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'CLK'}, {'wire_id': 'W04', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'HEX_N', 'from_header': None, 'from_pin_label': 'DAT', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'DAT'}, {'wire_id': 'W05', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'HEX_NE', 'from_header': None, 'from_pin_label': 'VDD', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'VDD'}, {'wire_id': 'W06', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'HEX_NE', 'from_header': None, 'from_pin_label': 'GND', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'GND'}, {'wire_id': 'W07', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'HEX_NE', 'from_header': None, 'from_pin_label': 'CLK', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'CLK'}, {'wire_id': 'W08', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'HEX_NE', 'from_header': None, 'from_pin_label': 'DAT', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'DAT'}, {'wire_id': 'W09', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'HEX_SE', 'from_header': None, 'from_pin_label': 'VDD', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'VDD'}, {'wire_id': 'W10', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'HEX_SE', 'from_header': None, 'from_pin_label': 'GND', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'GND'}, {'wire_id': 'W11', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'HEX_SE', 'from_header': None, 'from_pin_label': 'CLK', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'CLK'}, {'wire_id': 'W12', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'HEX_SE', 'from_header': None, 'from_pin_label': 'DAT', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'DAT'}, {'wire_id': 'W13', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'HEX_S', 'from_header': None, 'from_pin_label': 'VDD', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'VDD'}, {'wire_id': 'W14', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'HEX_S', 'from_header': None, 'from_pin_label': 'GND', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'GND'}, {'wire_id': 'W15', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'HEX_S', 'from_header': None, 'from_pin_label': 'CLK', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'CLK'}, {'wire_id': 'W16', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'HEX_S', 'from_header': None, 'from_pin_label': 'DAT', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'DAT'}, {'wire_id': 'W17', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'HEX_SW', 'from_header': None, 'from_pin_label': 'VDD', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'VDD'}, {'wire_id': 'W18', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'HEX_SW', 'from_header': None, 'from_pin_label': 'GND', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'GND'}, {'wire_id': 'W19', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'HEX_SW', 'from_header': None, 'from_pin_label': 'CLK', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'CLK'}, {'wire_id': 'W20', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'HEX_SW', 'from_header': None, 'from_pin_label': 'DAT', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'DAT'}, {'wire_id': 'W21', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'HEX_NW', 'from_header': None, 'from_pin_label': 'VDD', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'VDD'}, {'wire_id': 'W22', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'HEX_NW', 'from_header': None, 'from_pin_label': 'GND', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'GND'}, {'wire_id': 'W23', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'HEX_NW', 'from_header': None, 'from_pin_label': 'CLK', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'CLK'}, {'wire_id': 'W24', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'HEX_NW', 'from_header': None, 'from_pin_label': 'DAT', 'to_comp': 'CENTRAL_PERFBOARD', 'to_header': 'PERFBOARD', 'to_pin_label': 'DAT'}, {'wire_id': 'W25', 'signal_type': 'VCC', 'wire_color': 'Red', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'VDD', 'to_comp': 'NUCLEO', 'to_header': 'CN8', 'to_pin_label': '3V3'}, {'wire_id': 'W26', 'signal_type': 'GND', 'wire_color': 'Black', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'GND', 'to_comp': 'NUCLEO', 'to_header': 'CN9', 'to_pin_label': 'GND'}, {'wire_id': 'W27', 'signal_type': 'CLK', 'wire_color': 'Yellow', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'CLK', 'to_comp': 'NUCLEO', 'to_header': 'CN9', 'to_pin_label': 'PC_3'}, {'wire_id': 'W28', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'DAT', 'to_comp': 'NUCLEO', 'to_header': 'CN9', 'to_pin_label': 'PE_9'}, {'wire_id': 'W29', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'DAT', 'to_comp': 'NUCLEO', 'to_header': 'CN9', 'to_pin_label': 'PE_4'}, {'wire_id': 'W30', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'DAT', 'to_comp': 'NUCLEO', 'to_header': 'CN7', 'to_pin_label': 'PC_1'}, {'wire_id': 'W31', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'DAT', 'to_comp': 'NUCLEO', 'to_header': 'CN7', 'to_pin_label': 'PC_5'}, {'wire_id': 'W32', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'DAT', 'to_comp': 'NUCLEO', 'to_header': 'CN10', 'to_pin_label': 'PE_10'}, {'wire_id': 'W33', 'signal_type': 'DAT', 'wire_color': 'Blue', 'from_comp': 'CENTRAL_PERFBOARD', 'from_header': 'PERFBOARD', 'from_pin_label': 'DAT', 'to_comp': 'NUCLEO', 'to_header': 'CN10', 'to_pin_label': 'PE_12'}]}

    # 2. DigiKey keyword search — one call per part in the manifest
    print("Digikey: ")
    print(parts_search_results)
    print("IOC: ")
    print(ioc_result)
    print("CV: ")
    print(cv_result)

    prompt = fusionprompt.format(
        ioc_result=json.dumps(ioc_result, indent=2) if not isinstance(ioc_result, str) else ioc_result,
        cv_result=json.dumps(cv_result, indent=2),
        digikey_result=json.dumps(parts_search_results, indent=2),
    )
    
    # response = client.models.generate_content(
    #     model="gemini-2.5-flash",
    #     contents=prompt
    # )

    # # Clean up code fences and load as a dictionary
    # try:
    #     resp_text = response.text.strip()
    #     if "```" in resp_text:
    #         resp_text = resp_text.split("```")[1].replace("json", "", 1).strip()
    #     netlist_dict = json.loads(resp_text)
    # except Exception as e:
    #     print(f"[fusion] Failed to parse JSON: {e}")
    #     # Fallback to avoid crashing the response validation schema
    #     netlist_dict = {"error": f"Parsing failed: {str(e)}", "raw_response": response.text}
    netlist_dict = {
  "components": [
    {
      "id": "NUCLEO",
      "type": "MCU_BOARD",
      "hardware_model": "NUCLEO-H7A3ZI-Q",
      "pins": {
        "3V3": "VCC_3V3",
        "GND": "GND",
        "PE9": "DFSDM1_CKOUT",
        "PC3": "DFSDM1_DATIN1_PC3",
        "PE10": "DFSDM1_DATIN4",
        "PE12": "DFSDM1_DATIN5",
        "PE4": "DFSDM1_DATIN3",
        "PC5": "DFSDM1_DATIN2",
        "PC1": "DFSDM1_DATIN0"
      }
    },
    {
      "id": "HEX_N",
      "type": "MICROPHONE",
      "hardware_model": "Adafruit 4346 PDM Microphone",
      "pins": {
        "VDD": "VCC_3V3",
        "GND": "GND",
        "CLK": "DFSDM1_CKOUT",
        "DAT": "DFSDM1_DATIN1_PC3"
      }
    },
    {
      "id": "HEX_NE",
      "type": "MICROPHONE",
      "hardware_model": "Adafruit 4346 PDM Microphone",
      "pins": {
        "VDD": "VCC_3V3",
        "GND": "GND",
        "CLK": "DFSDM1_CKOUT",
        "DAT": "DFSDM1_DATIN4"
      }
    },
    {
      "id": "HEX_SE",
      "type": "MICROPHONE",
      "hardware_model": "Adafruit 4346 PDM Microphone",
      "pins": {
        "VDD": "VCC_3V3",
        "GND": "GND",
        "CLK": "DFSDM1_CKOUT",
        "DAT": "DFSDM1_DATIN5"
      }
    },
    {
      "id": "HEX_S",
      "type": "MICROPHONE",
      "hardware_model": "Adafruit 4346 PDM Microphone",
      "pins": {
        "VDD": "VCC_3V3",
        "GND": "GND",
        "CLK": "DFSDM1_CKOUT",
        "DAT": "DFSDM1_DATIN3"
      }
    },
    {
      "id": "HEX_SW",
      "type": "MICROPHONE",
      "hardware_model": "Adafruit 4346 PDM Microphone",
      "pins": {
        "VDD": "VCC_3V3",
        "GND": "GND",
        "CLK": "DFSDM1_CKOUT",
        "DAT": "DFSDM1_DATIN2"
      }
    },
    {
      "id": "HEX_NW",
      "type": "MICROPHONE",
      "hardware_model": "Adafruit 4346 PDM Microphone",
      "pins": {
        "VDD": "VCC_3V3",
        "GND": "GND",
        "CLK": "DFSDM1_CKOUT",
        "DAT": "DFSDM1_DATIN0"
      }
    }
  ],
  "nets": [
    {
      "name": "VCC_3V3",
      "description": "Shared 3.3V supply, bussed through perfboard to all mics",
      "connections": [
        "HEX_N.VDD",
        "HEX_NE.VDD",
        "HEX_NW.VDD",
        "HEX_S.VDD",
        "HEX_SE.VDD",
        "HEX_SW.VDD",
        "NUCLEO.3V3"
      ]
    },
    {
      "name": "GND",
      "description": "Shared ground, bussed through perfboard to all mics",
      "connections": [
        "HEX_N.GND",
        "HEX_NE.GND",
        "HEX_NW.GND",
        "HEX_S.GND",
        "HEX_SE.GND",
        "HEX_SW.GND",
        "NUCLEO.GND"
      ]
    },
    {
      "name": "DFSDM1_CKOUT",
      "description": "IOC: DFSDM1_CKOUT on PE9, bussed through perfboard to all mic CLK pins",
      "connections": [
        "HEX_N.CLK",
        "HEX_NE.CLK",
        "HEX_NW.CLK",
        "HEX_S.CLK",
        "HEX_SE.CLK",
        "HEX_SW.CLK",
        "NUCLEO.PE9"
      ]
    },
    {
      "name": "DFSDM1_DATIN1_PC3",
      "description": "IOC: DFSDM1_DATIN1 configured on PC3_C, but CV shows wired to PC3",
      "connections": [
        "HEX_N.DAT",
        "NUCLEO.PC3"
      ]
    },
    {
      "name": "DFSDM1_DATIN4",
      "description": "IOC: DFSDM1_DATIN4 on PE10",
      "connections": [
        "HEX_NE.DAT",
        "NUCLEO.PE10"
      ]
    },
    {
      "name": "DFSDM1_DATIN5",
      "description": "IOC: DFSDM1_DATIN5 on PE12",
      "connections": [
        "HEX_SE.DAT",
        "NUCLEO.PE12"
      ]
    },
    {
      "name": "DFSDM1_DATIN3",
      "description": "IOC: DFSDM1_DATIN3 on PE4",
      "connections": [
        "HEX_S.DAT",
        "NUCLEO.PE4"
      ]
    },
    {
      "name": "DFSDM1_DATIN2",
      "description": "IOC: DFSDM1_DATIN2 on PC5",
      "connections": [
        "HEX_SW.DAT",
        "NUCLEO.PC5"
      ]
    },
    {
      "name": "DFSDM1_DATIN0",
      "description": "IOC: DFSDM1_DATIN0 on PC1",
      "connections": [
        "HEX_NW.DAT",
        "NUCLEO.PC1"
      ]
    }
  ],
  "notes": [
    "IOC pin_map lists DFSDM1_DATIN1 on PC3_C, but CV shows HEX_N's DAT wired to PC3 (different pin) -- net DFSDM1_DATIN1_PC3 reflects CV wiring.",
    "CV connection W27 reports 'CLK' signal type from CENTRAL_PERFBOARD to NUCLEO.PC_3, but the circuit's functional intent (and IOC config of PE9 as DFSDM1_CKOUT) suggests PE9 is the clock source for mics. This netlist assumes PE9 as the CLK source and PC3 as a DATIN, as per example output.",
    "CV connection W28 reports 'DAT' signal type from CENTRAL_PERFBOARD to NUCLEO.PE_9, but the circuit's functional intent (and IOC config of PE9 as DFSDM1_CKOUT) suggests PE9 is the clock source, not a data input. This netlist assigns PE9 to DFSDM1_CKOUT, as per example output."
  ]
}

    # Simplify to production-ready netlist and generate .net file
    download_url = ""
    geometry_url = ""
    try:
        production_netlist = simplify_to_production(netlist_dict)
        uid = uuid.uuid4().hex[:8]
        net_filename = f"circuit_{uid}.net"
        output_path = os.path.join(SCHEMATICS_DIR, net_filename)
        generate_netlist(production_netlist, output_file=output_path)
        download_url = f"http://127.0.0.1:8000/api/download-netlist/{net_filename}"
    except Exception as e:
        print(f"[schematic_generator] Failed to simplify/generate netlist: {e}")

    try:
        geo_filename = f"circuit_{uuid.uuid4().hex[:8]}.kicad_pcb"
        geo_output_path = os.path.join(SCHEMATICS_DIR, geo_filename)
        generate_kicad_pcb(netlist_dict, cv_result, output_file=geo_output_path)
        geometry_url = f"http://127.0.0.1:8000/api/download-geometry/{geo_filename}"
    except Exception as e:
        print(f"[schematic_geometry_generator] Failed to generate .kicad_pcb: {e}")

    return {
        "confidence": 1.0,
        "reasoning_log": json.dumps(ioc_result, indent=2) if isinstance(ioc_result, dict) else ioc_result,
        "netlist": netlist_dict,
        "schematic_url": download_url,
        "geometry_url": geometry_url,
    }


@app.post("/generate-schematic")
async def generate_schematic_endpoint(request: NetlistRequest):
    output_path = os.path.join(SCHEMATICS_DIR, f"circuit_{uuid.uuid4().hex[:8]}.net")
    try:
        generate_netlist(request.netlist, output_file=output_path)
        return FileResponse(
            output_path,
            media_type="application/octet-stream",
            filename="circuit.net"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/download-netlist/{filename}")
def download_netlist(filename: str):
    file_path = os.path.join(SCHEMATICS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename="circuit.net"
    )


@app.get("/api/download-geometry/{filename}")
def download_geometry(filename: str):
    file_path = os.path.join(SCHEMATICS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename="circuit.kicad_pcb"
    )


class HexBoardResponse(BaseModel):
    net_url: str
    pcb_url: str


@app.post("/api/generate-hex-board", response_model=HexBoardResponse)
def generate_hex_board():
    try:
        net_path, pcb_path = generate_hex_mic_board(output_dir=SCHEMATICS_DIR)
        net_filename = os.path.basename(net_path)
        pcb_filename = os.path.basename(pcb_path)
        return {
            "net_url": f"http://127.0.0.1:8000/api/download-netlist/{net_filename}",
            "pcb_url": f"http://127.0.0.1:8000/api/download-geometry/{pcb_filename}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if _ioc_parser_available:
    app.include_router(ioc_parser_router, prefix="/preprocess_ioc")
    app.include_router(oauth3_router, prefix="/test")
