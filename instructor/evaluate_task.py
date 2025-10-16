import requests
from fastapi import FastAPI

app = FastAPI()

@app.post("/evaluate_task")
async def evaluate_task(payload: dict):
    print(payload)


