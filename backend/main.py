"""

Para ejecutar:
    cd backend
    uvicorn main:app --reload --port 8000

despues abrir
    http://localhost:8000
"""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Permitimos importar los paquetes locales (api, services, models, algorithms)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.rutas import router  # noqa: E402

app = FastAPI(
    title="PCB Router",
    description="Herramienta de trazado automatico de circuitos impresos",
    version="1.0.0",
)

# CORS abierto para desarrollo local; en produccion se debe restringir
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montamos la API bajo /api
app.include_router(router, prefix="/api")

# Ruta a la carpeta del frontend (un nivel arriba de backend)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(RAIZ, "frontend")


@app.get("/")
def inicio():
    """Sirve la pagina principal."""
    return FileResponse(os.path.join(FRONTEND, "index.html"))


# Servimos css, js y assets como archivos estaticos
if os.path.isdir(FRONTEND):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND, "js")), name="js")
    assets = os.path.join(FRONTEND, "assets")
    if os.path.isdir(assets):
        app.mount("/assets", StaticFiles(directory=assets), name="assets")


@app.get("/health")
def salud():
    """Endpoint simple para comprobar que el servidor responde."""
    return {"estado": "ok"}
