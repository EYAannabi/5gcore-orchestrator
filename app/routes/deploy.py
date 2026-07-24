"""
Deployment orchestration routes.
Handles Free5GC deployment lifecycle management with Multi-Operator isolation.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from app.services.helm_service import (
    deploy_free5gc, 
    build_helm_values,
    # On va utiliser une nouvelle fonction de nettoyage complet
    clean_operator_environment 
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
        logger.info(f"--- Requête de déploiement NetDevOps ---")
        logger.info(f"Utilisateur: {config.operator_name} | Namespace: {config.namespace}")
        
        # Préparation des paramètres Helm (Smart Sizing + Port Mapping)
        helm_values = build_helm_values(config)
        
        # Exécution du déploiement du Cœur
        success, stdout, stderr = deploy_free5gc(
            deployment_name=config.deployment_name,
            namespace=config.namespace,
            chart_path=config.helm_chart_path,
            values=helm_values,
            create_namespace=True
        )
        
        if success:
            logger.info(f"✅ Réseau 5G '{config.deployment_name}' initialisé pour {config.operator_name}")
            return DeploymentResponse(
                status="Success",
                message=f"Le réseau de {config.operator_name} (Site: {config.deployment_name}) est en cours de création.",
                deployment_name=config.deployment_name,
                namespace=config.namespace,
                output="Helm deployment triggered successfully"
            )
        else:
            logger.error(f"❌ Échec Helm : {stderr}")
            raise HTTPException(status_code=400, detail=f"Erreur Helm: {stderr}")
    
    except Exception as e:
        logger.error(f"💥 Erreur Critique Deploy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur Interne: {str(e)}")

@router.delete("/clean", response_model=DeploymentResponse)
async def clean(
    namespace: str = Query(..., description="Namespace de l'opérateur à nettoyer totalement")
):
    """
    Nettoyage Radical : Supprime TOUTES les releases (Cœur + RAN) et le NAMESPACE.
    C'est ce qui permet de libérer les ressources et de faire disparaître l'opérateur du Dashboard Admin.
    """
    try:
        logger.info(f"🗑️ Nettoyage TOTAL demandé pour le namespace : {namespace}")
        
        # Appel de la fonction de nettoyage global (Core + UERANSIM + NS)
        success, message = clean_operator_environment(namespace)
        
        if success:
            return DeploymentResponse(
                status="Success",
                message=message,
                namespace=namespace
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        logger.error(f"💥 Erreur lors du nettoyage : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=DeploymentStatus)
async def get_status(namespace: str = Query(..., description="Namespace à surveiller")):
    """
    Retourne l'état des microservices pour l'opérateur.
    """
    try:
        status_data = check_deployment_status(namespace=namespace)
        return DeploymentStatus(**status_data)
    except Exception as e:
        logger.error(f"Erreur status pour {namespace}: {e}")
        raise HTTPException(status_code=500, detail="Impossible de lire les données Kubernetes")