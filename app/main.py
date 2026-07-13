from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # ← Ajoute cet import
from fastapi.responses import FileResponse  # ← Ajoute cet import
from app.routes import pods, deploy, logs

app = FastAPI(
    title="5G Core Orchestrator",
    description="Automation & Orchestration Platform for Free5GC Cloud-Native",
    version="2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routes API
app.include_router(pods.router)
app.include_router(deploy.router)
app.include_router(logs.router)

# 🛠️ Configuration du dossier statique pour l'interface utilisateur
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", tags=["Système"])
def read_root():
    """Redirige l'accueil de l'API directement vers l'interface Web graphique"""
    return FileResponse("app/static/index.html")
