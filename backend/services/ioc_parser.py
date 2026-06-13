from fastapi import APIRouter
from google import genai
import asyncio
from pathlib import Path
import os

CUBEMXPROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "CubeMXPrompt.txt"
cubemxprompt = CUBEMXPROMPT_PATH.read_text()

router = APIRouter()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

@router.get("/cubemx_parse")
def cubemx_parse():
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=cubemxprompt
    )
    return response.text