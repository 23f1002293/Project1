from fastapi import FastAPI
import os
from lib import validate_secret, round1, round2

# Initialize the FastAPI application
app = FastAPI(
    title="TDS-Project1",
    description="App builder",
    version="1.0.0"
)

# Get the port from the environment variable (default to 8080 if not set)
# Cloud Run automatically injects the PORT environment variable.
port = int(os.environ.get("PORT", 8080))

@app.get("/")
async def root():
    """
    Root endpoint that returns a simple welcome message.
    """
    return {"message": "Hello from FastAPI on Cloud Run!",
            "status": "Online",
            "server_port": port}

@app.get("/health")
async def health_check():
    """
    A simple health check endpoint.
    """
    return {"status": "ok"}

@app.post("/handle_task")
async def handle_task(payload: dict):
    sha = ""
    print("🚀 Starting Auto App Builder...\n")

    if not validate_secret(payload.get("secret", "")):
        return {"error": "Invalid secret"}
    else:
        if payload.get("round") == 1:
            message = round1(payload)
            return message
        elif payload.get("round") == 2:
            # Handle round 2 tasks (e.g., improvements, bug fixes)
            message = round2(payload)
            return {"message": "🔄 Round 2 task completed and updates published into the repository."}


