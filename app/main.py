from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, usuarios, vehiculos, talleres, tecnicos,incidentes
import app.models

app = FastAPI(
    title=settings.app_name,
    description="Backend - Plataforma Inteligente de Emergencias Vehiculares | Ciclo 1",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar todos los routers del Ciclo 1
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(usuarios.roles_router)
app.include_router(usuarios.permisos_router)
app.include_router(vehiculos.router)
app.include_router(talleres.router)
app.include_router(tecnicos.router)
app.include_router(incidentes.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "sistema": settings.app_name,
        "ciclo": "Ciclo 1 — CU01 al CU10",
        "docs": "/docs",
        "estado": "✅ Backend corriendo"
    }