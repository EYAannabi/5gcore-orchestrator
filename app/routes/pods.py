from fastapi import APIRouter
from app.services.kubernetes_service import list_pods, get_node_status, delete_specific_pod

# On regroupe tout sous le préfixe /status pour la supervision
router = APIRouter(prefix="/status", tags=["Supervision"])

@router.get("/pods")
def get_pods_status():
    """Récupère la liste en temps réel des fonctions réseau 5G (Pods)"""
    return {"pods": list_pods()}

@router.get("/node")
def get_node_info():
    """Récupère les specs matérielles et l'état de la VM hôte K3s"""
    return {"node": get_node_status()}

@router.post("/restart/{pod_name}")
def restart_pod(pod_name: str):
    """Force le redémarrage (self-healing) d'un composant spécifié"""
    success, message = delete_specific_pod(pod_name)
    return {"status": "Success" if success else "Error", "message": message}
