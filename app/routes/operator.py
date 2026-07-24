import logging
import subprocess
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services import deployment_orchestrator
import re

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
    imsi = "imsi-208930000000001"
    
    # On utilise la commande -e status qui renvoie l'état dynamique
    command = f"./nr-cli {imsi} -e status" 
    
    kube_cmd = ["kubectl", "exec", "-n", namespace, pod_name, "--", "sh", "-c", command]
    
    try:
        process = subprocess.run(kube_cmd, capture_output=True, text=True, timeout=10)
        output = process.stdout
        
        # LOGIQUE DE VALIDATION ROBUSTE :
        # On vérifie les deux états clés pour confirmer que la 5G fonctionne
        is_registered = "RM-REGISTERED" in output and "MM-REGISTERED" in output
        
        logger.info(f"Diagnostic UE {imsi} : {'SUCCÈS' if is_registered else 'ÉCHEC'}")

        return {
            "registered": is_registered,
            "output": output, # On renvoie tout pour que l'ingénieur puisse lire s'il veut
            "details": {
                "cm_state": "CONNECTED" if "CM-CONNECTED" in output else "IDLE",
                "rm_state": "REGISTERED" if "RM-REGISTERED" in output else "DEREGISTERED",
                "ue_ip": "10.60.0.1" if is_registered else None
            }
        }
    except Exception as e:
        logger.error(f"Erreur lors du diagnostic UE : {e}")
        return {"registered": False, "error": str(e)}
        
# --- 3. SECTION MONITORING / LOGS ---

@router.get("/test")
async def operator_test(deployment_name: str, namespace: str):
    """Verdict de santé global (utilisé pour le statut résumé du dashboard)"""
    return await deployment_orchestrator.test_network(deployment_name, namespace)
@router.get("/network/diagnostic-full")
async def diagnostic_full(pod_name: str, namespace: str, imsi: str = "imsi-208930000000001"):
    results = {}
    
    # 1. État NAS (Signalisation)
    # On utilise l'IMSI passé en paramètre
    cmd_status = f"./nr-cli {imsi} -e status"
    exec_status = subprocess.run(["kubectl", "exec", "-n", namespace, pod_name, "--", "sh", "-c", cmd_status], capture_output=True, text=True)
    out = exec_status.stdout
    results["registration"] = "REGISTERED" if "MM-REGISTERED" in out else "DEREGISTERED"
    
    # 2. IP 5G (On cherche l'interface uesimtun0)
    cmd_ip = "ip addr show uesimtun0"
    exec_ip = subprocess.run(["kubectl", "exec", "-n", namespace, pod_name, "--", "sh", "-c", cmd_ip], capture_output=True, text=True)
    
    # On améliore la détection de l'IP
    if "inet " in exec_ip.stdout:
        # Extrait l'IP entre 'inet ' et '/'
        results["ue_ip"] = exec_ip.stdout.split("inet ")[1].split("/")[0]
    else:
        results["ue_ip"] = "No IP (PDU Session Failed)"

    # 3. Test DNS (Seulement si on a une IP)
    if "No IP" not in results["ue_ip"]:
        cmd_dns = "nslookup google.com"
        exec_dns = subprocess.run(["kubectl", "exec", "-n", namespace, pod_name, "--", "sh", "-c", cmd_dns], capture_output=True, text=True)
        results["dns"] = "SUCCESS" if exec_dns.returncode == 0 else "FAILED"
    else:
        results["dns"] = "SKIPPED"

    results["plmn"] = "208/93" # Peut être extrait via Regex aussi
    return results
@router.post("/network/deploy-ran")
async def deploy_ran(site_name: str, namespace: str, operator_name: str):
    """Déploie automatiquement l'antenne (gNB) et le téléphone (UE)"""
    try:
        # On détermine le nom de la release RAN (ex: ueransim-orange)
        ran_release_name = f"ueransim-{operator_name}"
        
        # On construit la commande exacte que tu utilisais en manuel
        # On automatise le lien avec le cœur (sfax-core, sousse-core...)
        command = [
            "helm", "install", ran_release_name, "./ueransim/",
            "-n", namespace,
            "--set", f"global.free5gcReleaseName={site_name}-core",
            "--set", "gnb.amf.n2if.serviceName=free5gc-amf-amf-n2",
            "--set", "global.n2network.masterIf=ens33",
            "--set", "global.n3network.masterIf=ens33"
        ]
        
        # Exécution (dans le dossier des charts)
        import os
        chart_dir = os.path.expanduser("~/free5gc-helm/charts")
        process = subprocess.run(command, cwd=chart_dir, capture_output=True, text=True)
        
        if process.returncode == 0:
            return {"status": "success", "message": "Antenne gNodeB et UE activés avec succès."}
        else:
            return {"status": "error", "message": process.stderr}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}