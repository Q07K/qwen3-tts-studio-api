from fastapi import FastAPI

from app.routers import voices

app = FastAPI()

app.include_router(prefix="/api/voices", router=voices.router)
