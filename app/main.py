from fastapi import FastAPI
import os

def round1():
    # write code with llm
    # create github repo 
    # enable github pages 
    # deploy github pages
    # push files to repo
    pass

def round2():
    pass

app = FastAPI()

def validate_secret(secret: str) -> bool:
    print(os.getenv("SECRET"))
    return secret == os.getenv("SECRET")


@app.post("/handle_task")
async def handle_task(data: dict):
    if not validate_secret(data.get("secret", "")):
        return {"error": "Invalid secret"}
    else:
        if data.get("round") == 1:
            round1()
        elif data.get("round") == 2:
            round2()
        else:
            return {"error": "Invalid round"}
        pass
    print(data)
    return {"message": "Task recieved", "data": data} 
    

# @app.get("/")
# def read_root():
#     return {"Hello": "World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
