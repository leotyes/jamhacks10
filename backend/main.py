from fastapi import FastAPI
from services.ioc_parser import router as ioc_parser_router

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

app.include_router(ioc_parser_router, prefix="/preprocess")