from fastapi import FastAPI

app = FastAPI()

@app.post("/handle_task")
async def handle_task(data: dict):
    print(data)
    return {"status": "Task received", "data": data}

# @app.get("/")
# def read_root():
#     return {"Hello": "World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)