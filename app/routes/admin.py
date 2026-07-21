from fastapi import APIRouter, HTTPException
from app.services import kubernetes_service as k8s
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Huawei Infrastructure Admin"])

@router.get("/overview")
async def get_overview():
    """Résumé global pour les cartes du haut du dashboard"""
    try:
        health = k8s.get_cluster_health()
        operators = k8s.get_operator_namespaces()
        pods_stats = k8s.get_all_pods_stats()
        
        return {
            "cluster_status": health["status"],
            "nodes_ready": f"{health['nodes_ready']}/{health['nodes_total']}",
            "total_operators": len(operators),
            "pods_running": pods_stats["Running"],
            "pods_pending": pods_stats["Pending"],
            "pods_failed": pods_stats["Failed"]
        }
    except Exception as e:
        logger.error(f"Error in admin overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/operators")
async def get_operators_list():
    """Liste détaillée des opérateurs pour le tableau"""
    try:
        from app.services import kubernetes_service as k8s
        return k8s.get_operator_status_detailed()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/resources")
async def get_resources():
    """Métriques CPU/RAM réelles du cluster"""
    try:
        return k8s.get_cluster_resources()
    except Exception as e:
        return {"cpu": 0, "ram": 0, "error": "Metrics Server non disponible"}