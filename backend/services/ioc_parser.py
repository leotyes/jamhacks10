from fastapi import APIRouter
from google import genai
from pathlib import Path
import os

CUBEMXPROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "CubeMXPrompt.txt"
cubemxprompt = CUBEMXPROMPT_PATH.read_text(encoding="utf-8")

router = APIRouter()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))

def parse_ioc_content(ioc_file_content: str) -> str:
    full_prompt = f"{cubemxprompt} \n{ioc_file_content}"
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=full_prompt
    )
    return response.text

@router.post("/cubemx_parse")
def cubemx_parse(ioc_content: str):
    return parse_ioc_content(ioc_content)