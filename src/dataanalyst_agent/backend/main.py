import uvicorn
from fastapi import FastAPI
from dataanalyst_agent.backend.api.routes import router


app = FastAPI(title="Data Analyst Agent API")

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)