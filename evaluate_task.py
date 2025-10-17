import requests
from fastapi import FastAPI

app = FastAPI()

@app.post("/evaluate_task")
async def evaluate_task(payload: dict):
    print("📩 Evaluation payload received:")
    print(payload)

    return {"message": "Evaluation received"}   

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)