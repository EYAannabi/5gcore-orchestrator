import logging
import subprocess
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services import deployment_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operator", tags=["Operator Actions"])

# --- MODÈLES DE REQUÊTE ---

class ReconfigureRequest(BaseModel):
    network_function: str
    replicas: int
    deployment_name: str
    namespace: str

# --- 1. SECTION OPÉRATIONS (L'existant amélioré) ---

@router.post("/deploy")
async def operator_deploy(deployment_name: str, namespace: str):
    """Pipeline complet : Déploiement + Validation automatique"""
    logger.info(f"Pipeline de déploiement lancé pour {deployment_name} dans {namespace}")
    return await deployment_orchestrator.deploy_and_validate(deployment_name, namespace)

@router.post("/reconfigure")
async def operator_reconfigure(request: ReconfigureRequest):
    """Pipeline d'Upscaling : Change les réplicas + Validation + Rollback si échec"""
    logger.info(f"Pipeline d'upscaling pour {request.network_function} ({request.replicas} réplicas)")
    return await deployment_orchestrator.reconfigure_with_safety(
        network_function=request.network_function,
        replicas=request.replicas,
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )

# --- 2. SECTION VALIDATION & DIAGNOSTIC (Le nouveau module) ---

@router.get("/network/ping")
async def run_ping(pod_name: str, namespace: str, target: str = "8.8.8.8"):
    """Exécute un ping RÉEL depuis le Pod UE à travers le tunnel 5G"""
    # Commande UERANSIM : on force l'interface 5G 'uesimtun0'
    command = f"ping -I uesimtun0 -c 4 {target}"
    kube_cmd = ["kubectl", "exec", "-n", namespace, pod_name, "--", "sh", "-c", command]
    
    try:
        process = subprocess.run(kube_cmd, capture_output=True, text=True, timeout=15)
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "status": "success" if process.returncode == 0 else "failed"
        }
    except Exception as e:
        logger.error(f"Erreur lors du ping : {e}")
        return {"status": "error", "message": str(e)}

@router.get("/network/ue-status")
async def check_ue_status(pod_name: str, namespace: str):
    """Vérifie l'enregistrement IMSI via l'outil nr-cli d'UERANSIM"""
    # On utilise l'outil interne d'UERANSIM pour voir si l'UE est 'Registered'
    command = "./nr-cli --dump" 
    kube_cmd = ["kubectl", "exec", "-n", namespace, pod_name, "--", "sh", "-c", command]
    
    try:
        process = subprocess.run(kube_cmd, capture_output=True, text=True, timeout=10)
        is_registered = "Registered" in process.stdout
        return {
            "registered": is_registered,
            "output": process.stdout
        }
    except Exception as e:
        logger.error(f"Erreur check UE status : {e}")
        return {"registered": False, "error": str(e)}

# --- 3. SECTION MONITORING / LOGS ---

@router.get("/test")
async def operator_test(deployment_name: str, namespace: str):
    """Verdict de santé global (utilisé pour le statut résumé du dashboard)"""
    return await deployment_orchestrator.test_network(deployment_name, namespace)