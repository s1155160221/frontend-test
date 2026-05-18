from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import api_router


app = FastAPI()

# CORS configuration to allow the frontend served by VS Code Live Server
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://s1155160221.github.io",
    # add other frontend origins here if needed, e.g. Vite dev server:
    # "http://127.0.0.1:5173",
    # "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)