"""
Deployment orchestration routes.
Handles Free5GC deployment lifecycle management with Multi-Operator isolation.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from app.services.helm_service import (
    deploy_free5gc, 
    clean_free5gc, 
    build_helm_values
)
from app.services.kubernetes_service import check_deployment_status
from app.models.deployment import DeploymentConfig, DeploymentResponse, DeploymentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core", tags=["Orchestration"])

@router.post("/deploy", response_model=DeploymentResponse)
async def deploy(config: DeploymentConfig):
    """
    Déploie un cœur 5G isolé pour Orange, Ooredoo ou Tunisie Telecom.
    """
    try:
        # 1. Logs de traçabilité (Audit Trail)
        logger.info(f"--- Requête de déploiement NetDevOps ---")
        logger.info(f"Utilisateur: {config.operator_name}")
        logger.info(f"Namespace: {config.namespace}")
        
        # 2. Préparation des paramètres Helm
        helm_values = build_helm_values(config)
        
        # 3. Exécution du déploiement
        # On utilise create_namespace=True pour automatiser la création des espaces isolés
        success, stdout, stderr = deploy_free5gc(
            deployment_name=config.deployment_name,
            namespace=config.namespace,
            chart_path=config.helm_chart_path,
            values=helm_values,
            create_namespace=True
        )
        
        if success:
            logger.info(f"✅ Réseau 5G déployé pour {config.operator_name}")
            return DeploymentResponse(
                status="Success",
                message=f"Réseau 5G de {config.operator_name} (Site: {config.deployment_name}) initialisé.",
                deployment_name=config.deployment_name,
                namespace=config.namespace,
                output="Helm install completed successfully"
            )
        else:
            logger.error(f"❌ Échec Helm pour {config.operator_name}: {stderr}")
            raise HTTPException(status_code=400, detail=f"Erreur Helm: {stderr}")
    
    except Exception as e:
        logger.error(f"💥 Erreur Critique Deploy: {str(e)}")
        # C'est ici que l'erreur 'operator_name' disparaîtra après avoir mis à jour le modèle
        raise HTTPException(status_code=500, detail=f"Erreur Interne: {str(e)}")

@router.delete("/clean", response_model=DeploymentResponse)
async def clean(
    deployment_name: str = Query(..., description="Nom de la release"), 
    namespace: str = Query(..., description="Namespace de l'opérateur")
):
    """
    Supprime proprement le réseau d'un opérateur sans toucher aux autres.
    """
    try:
        logger.info(f"Nettoyage demandé par l'opérateur dans {namespace}")
        success, stdout, stderr = clean_free5gc(deployment_name, namespace)
        
        if success:
            return DeploymentResponse(
                status="Success",
                message=f"Le réseau {deployment_name} a été supprimé du namespace {namespace}.",
                output=stdout
            )
        else:
            if "not found" in stderr.lower():
                return DeploymentResponse(status="Success", message="Réseau déjà inexistant.")
            raise HTTPException(status_code=400, detail=stderr)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=DeploymentStatus)
async def get_status(namespace: str = Query(..., description="Namespace à surveiller")):
    """
    Retourne l'état des Pods pour l'opérateur connecté.
    """
    try:
        status_data = check_deployment_status(namespace=namespace)
        return DeploymentStatus(**status_data)
    except Exception as e:
        logger.error(f"Erreur status pour {namespace}: {e}")
        raise HTTPException(status_code=500, detail="Impossible de lire les données Kubernetes")