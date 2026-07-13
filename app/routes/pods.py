"""
Pod management and cluster status routes.
Provides real-time monitoring of 5G Core components.
"""

import logging
from typing import List
from fastapi import APIRouter, HTTPException
from app.services.kubernetes_service import (
    list_pods,
    get_node_status,
    delete_specific_pod,
    check_deployment_status
)
from app.models.deployment import PodInfo, NodeInfo, DeploymentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["Supervision"])


@router.get("/pods", response_model=dict)
async def get_pods_status(namespace: str = "free5gc"):
    """
    Get the list of all running pods in the namespace.
    
    Returns real-time pod information including status, IP, age, and restart count.
    
    Args:
        namespace: Kubernetes namespace to query
        
    Returns:
        Dictionary containing list of PodInfo objects
    """
    try:
        pods = list_pods(namespace=namespace)
        return {"pods": pods, "total": len(pods)}
    except Exception as e:
        logger.error(f"Error fetching pod status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving pods: {str(e)}")


@router.get("/node", response_model=dict)
async def get_node_info():
    """
    Get information about Kubernetes cluster nodes.
    
    Returns hardware specifications, OS information, and cluster health status.
    
    Returns:
        Dictionary containing list of NodeInfo objects
    """
    try:
        nodes = get_node_status()
        if not nodes:
            return {"node": [], "message": "No nodes found"}
        return {"node": nodes, "total": len(nodes)}
    except Exception as e:
        logger.error(f"Error fetching node status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving node info: {str(e)}")


@router.get("/deployment", response_model=DeploymentStatus)
async def get_deployment_status(namespace: str = "free5gc"):
    """
    Get comprehensive deployment status.
    
    Combines pod and node information to provide complete deployment overview.
    
    Args:
        namespace: Kubernetes namespace
        
    Returns:
        DeploymentStatus with all deployment information
    """
    try:
        status = check_deployment_status(namespace=namespace)
        return DeploymentStatus(**status)
    except Exception as e:
        logger.error(f"Error fetching deployment status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving deployment status: {str(e)}")


@router.post("/restart/{pod_name}", response_model=dict)
async def restart_pod(pod_name: str, namespace: str = "free5gc"):
    """
    Restart a specific pod by deleting it.
    
    Kubernetes will automatically recreate the pod via its replica set/deployment.
    This implements the self-healing capability of Kubernetes.
    
    Args:
        pod_name: Name of the pod to restart
        namespace: Kubernetes namespace
        
    Returns:
        Dictionary with operation status and message
    """
    try:
        logger.info(f"Restarting pod: {pod_name} in namespace {namespace}")
        success, message = delete_specific_pod(pod_name, namespace=namespace)
        
        return {
            "status": "Success" if success else "Error",
            "message": message,
            "pod_name": pod_name
        }
    except Exception as e:
        logger.error(f"Error restarting pod: {e}")
        raise HTTPException(status_code=500, detail=f"Error restarting pod: {str(e)}")
