"""
Deployment orchestration routes.
Handles Free5GC deployment lifecycle management.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.helm_service import deploy_free5gc, clean_free5gc, build_helm_values, get_deployment_status
from app.services.kubernetes_service import check_deployment_status
from app.models.deployment import DeploymentConfig, DeploymentResponse, DeploymentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/core", tags=["Orchestration"])


@router.post("/deploy", response_model=DeploymentResponse)
async def deploy(config: DeploymentConfig, background_tasks: BackgroundTasks):
    """
    Deploy Free5GC with the provided configuration.
    
    Accepts deployment parameters and initiates Helm installation.
    Parameters are validated by Pydantic before processing.
    
    Args:
        config: DeploymentConfig with all deployment parameters
        
    Returns:
        DeploymentResponse with status and deployment information
    """
    try:
        logger.info(f"Starting deployment: {config.deployment_name} in namespace {config.namespace}")
        
        # Convert configuration to Helm values
        helm_values = build_helm_values(config)
        
        # Execute Helm deployment
        success, stdout, stderr = deploy_free5gc(
            deployment_name=config.deployment_name,
            namespace=config.namespace,
            chart_path=config.helm_chart_path,
            values=helm_values,
            create_namespace=True
        )
        
        if success:
            logger.info(f"Deployment {config.deployment_name} initiated successfully")
            return DeploymentResponse(
                status="Success",
                message=f"Deployment '{config.deployment_name}' initiated successfully",
                deployment_name=config.deployment_name,
                namespace=config.namespace,
                output=stdout
            )
        else:
            logger.error(f"Deployment failed: {stderr}")
            raise HTTPException(
                status_code=400,
                detail=f"Deployment failed: {stderr}"
            )
    
    except Exception as e:
        logger.error(f"Error in deployment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Deployment error: {str(e)}"
        )


@router.delete("/clean", response_model=DeploymentResponse)
async def clean(deployment_name: str = "free5gc-helm", namespace: str = "free5gc"):
    """
    Clean up and remove Free5GC deployment.
    
    Uninstalls the Helm release and removes associated resources.
    
    Args:
        deployment_name: Helm release name to remove
        namespace: Kubernetes namespace
        
    Returns:
        DeploymentResponse with cleanup status
    """
    try:
        logger.info(f"Starting cleanup for deployment: {deployment_name} in namespace {namespace}")
        
        success, stdout, stderr = clean_free5gc(
            deployment_name=deployment_name,
            namespace=namespace
        )
        
        if success:
            logger.info(f"Deployment {deployment_name} cleaned up successfully")
            return DeploymentResponse(
                status="Success",
                message=f"Deployment '{deployment_name}' removed successfully",
                output=stdout
            )
        else:
            logger.error(f"Cleanup failed: {stderr}")
            # Don't fail if deployment doesn't exist
            if "not found" in stderr.lower():
                return DeploymentResponse(
                    status="Success",
                    message="Deployment not found or already removed"
                )
            raise HTTPException(
                status_code=400,
                detail=f"Cleanup failed: {stderr}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup error: {str(e)}"
        )


@router.get("/status", response_model=DeploymentStatus)
async def get_status(namespace: str = "free5gc"):
    """
    Get the current status of Free5GC deployment.
    
    Returns comprehensive deployment status including pod information
    and cluster health.
    
    Args:
        namespace: Kubernetes namespace to check
        
    Returns:
        DeploymentStatus with detailed deployment information
    """
    try:
        status = check_deployment_status(namespace=namespace)
        return DeploymentStatus(**status)
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving deployment status: {str(e)}"
        )
