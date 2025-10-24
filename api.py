from fastapi import FastAPI
from pydantic import BaseModel
from agentic_components.agent import run  # Import your run() function from agent.py

# Initialize FastAPI app
app = FastAPI()

# Define input schema
class MessageRequest(BaseModel):
    message: str

# Define endpoint
@app.post("/run")
async def run_agent(request: MessageRequest):
    response = run(request.message)
    return {"response": response}

@app.get("/health")
async def health():
    return {"response":"API is running perfect"}

@app.get("/")
async def info():
    return{"response":"The project is working and this is the agentic ai project and we have two different apis"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8080, reload=True)