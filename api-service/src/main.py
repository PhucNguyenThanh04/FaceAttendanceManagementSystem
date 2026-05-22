from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the FastAPI application!"}


@app.on_event("startup")
async def startup_event():
    print("Startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutdown complete")

