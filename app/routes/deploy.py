from fastapi import APIRouter
from app.services.helm_service import deploy_free5gc, clean_free5gc

router = APIRouter(prefix="/core", tags=["Orchestration du Cœur"])

@router.post("/deploy")
def deploy():
    """Lance le déploiement automatique de la 5G"""
    success, out, err = deploy_free5gc()
    if success:
        return {"status": "Success", "message": "Cœur 5G déployé avec succès !", "output": out}
    return {"status": "Error", "error": err}

@router.delete("/clean")
def clean():
    """Supprime proprement le cœur 5G pour réinitialiser la VM"""
    success, out, err = clean_free5gc()
    if success:
        return {"status": "Success", "message": "Cluster nettoyé."}
    return {"status": "Error", "error": err}
