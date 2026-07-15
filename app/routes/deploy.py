"""
Deployment orchestration routes.
Handles Free5GC deployment lifecycle management with Multi-Operator isolation.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from app.services.helm_service import (
    deploy_free5gc, 
    clean_free5gc, 
    build_helm_values, 
    get_deployment_status
)
from app.services.kubernetes_service import check_deployment_status
from app.models.deployment import DeploymentConfig, DeploymentResponse, DeploymentStatus

logger = logging.getLogger(__name__)

# On garde le préfixe /core pour la cohérence avec ton frontend
router = APIRouter(prefix="/core", tags=["Orchestration"])

@router.post("/deploy", response_model=DeploymentResponse)
async def deploy(config: DeploymentConfig):
    """
    Déploie un cœur 5G pour un opérateur spécifique.
    Le namespace est envoyé par le frontend (basé sur le login de l'utilisateur).
    """
    try:
        # On logue l'intention de déploiement
        logger.info(f"--- Nouveau Déploiement ---")
        logger.info(f"Opérateur: {config.operator_name}")
        logger.info(f"Nom Release: {config.deployment_name}")
        logger.info(f"Namespace Cible: {config.namespace}")

        # Conversion de la config en valeurs Helm
        helm_values = build_helm_values(config)
        
        # Exécution du déploiement via Helm
        # create_namespace=True garantit que si c'est le premier déploiement d'Orange, 
        # le namespace orange-5g sera créé automatiquement.
        success, stdout, stderr = deploy_free5gc(
            deployment_name=config.deployment_name,
            namespace=config.namespace,
            chart_path=config.helm_chart_path,
            values=helm_values,
            create_namespace=True
        )
        
        if success:
            logger.info(f"✅ Déploiement {config.deployment_name} réussi dans {config.namespace}")
            return DeploymentResponse(
                status="Success",
                message=f"Le réseau 5G '{config.deployment_name}' a été déployé avec succès.",
                deployment_name=config.deployment_name,
                namespace=config.namespace,
                output=stdout
            )
        else:
            logger.error(f"❌ Échec Helm: {stderr}")
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lors de l'installation Helm: {stderr}"
            )
    
    except Exception as e:
        logger.error(f"💥 Erreur système: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne du serveur: {str(e)}"
        )

@router.delete("/clean", response_model=DeploymentResponse)
async def clean(
    deployment_name: str = Query(..., description="Le nom de la release à supprimer"), 
    namespace: str = Query(..., description="Le namespace de l'opérateur")
):
    """
    Supprime un déploiement spécifique. 
    Les paramètres sont obligatoires (Query(...,)) pour éviter les erreurs.
    """
    try:
        logger.info(f"Suppression du réseau {deployment_name} dans {namespace}")
        
        success, stdout, stderr = clean_free5gc(
            deployment_name=deployment_name,
            namespace=namespace
        )
        
        if success:
            return DeploymentResponse(
                status="Success",
                message=f"Réseau '{deployment_name}' supprimé de l'espace {namespace}",
                output=stdout
            )
        else:
            # Si le déploiement n'existe déjà plus, on ne renvoie pas d'erreur
            if "not found" in stderr.lower():
                return DeploymentResponse(
                    status="Success",
                    message="Réseau déjà supprimé ou introuvable."
                )
            raise HTTPException(status_code=400, detail=stderr)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=DeploymentStatus)
async def get_status(namespace: str = Query(..., description="Namespace à surveiller")):
    """
    Récupère le statut des microservices d'un opérateur.
    """
    try:
        # On vérifie uniquement le namespace de l'opérateur connecté
        status = check_deployment_status(namespace=namespace)
        return DeploymentStatus(**status)
    except Exception as e:
        logger.error(f"Erreur status namespace {namespace}: {e}")
        raise HTTPException(status_code=500, detail="Impossible de récupérer l'état des Pods")