from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from fastapi.staticfiles import StaticFiles
from app.routers import auth, usuarios, vehiculos, talleres, tecnicos,incidentes, bitacora,evidencias,ia,asignacion,dashboard
import app.models

app = FastAPI(
    title=settings.app_name,
    description="Backend - Plataforma Inteligente de Emergencias Vehiculares | Ciclo 1",
    version="1.0.0",
    redirect_slashes=False  # ✅ ESTO EVITA EL 307    
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
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
app.include_router(bitacora.router)
app.include_router(evidencias.router)
app.include_router(ia.router)
app.include_router(asignacion.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "sistema": settings.app_name,
        "ciclo": "Ciclo 1 — CU01 al CU10",
        "docs": "/docs",
        "estado": "✅ Backend corriendo"
    }

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "message": "Backend funcionando correctamente"}

