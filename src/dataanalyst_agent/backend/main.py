import uvicorn
from fastapi import FastAPI
from dataanalyst_agent.backend.api.routes import router
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    app.state.datasets = {}
    yield


app = FastAPI(title="Data Analyst Agent API", lifespan=lifespan_manager)


app.include_router(router)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
