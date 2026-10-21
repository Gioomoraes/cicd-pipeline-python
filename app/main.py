import os

from fastapi import FastAPI

app = FastAPI()

ITEMS = [
    {"id": 1, "name": "widget"},
    {"id": 2, "name": "gadget"},
    {"id": 3, "name": "doohickey"},
]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": os.getenv("APP_VERSION", "dev")}


@app.get("/items")
def items():
    return ITEMS
