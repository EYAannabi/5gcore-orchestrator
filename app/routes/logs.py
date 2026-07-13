from fastapi import APIRouter
from app.services.kubernetes_service import get_pod_logs

router = APIRouter(prefix="/logs", tags=["Logs & Debugging"])

@router.get("/{pod_name}")
def get_logs(pod_name: str, lines: int = 50):
    """Récupère les logs d'un composant 5G (ex: free5gc-amf-xxxx)"""
    logs_content = get_pod_logs(pod_name=pod_name, tail_lines=lines)
    return {"pod": pod_name, "logs": logs_content.split("\n")}
