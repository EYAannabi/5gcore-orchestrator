"""
Pod logging and debugging routes.
Provides access to pod logs for troubleshooting and monitoring.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.services.kubernetes_service import get_pod_logs, list_pods

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Logs & Debugging"])


@router.get("/{pod_name}")
async def get_logs(pod_name: str, lines: int = 100, namespace: str = "free5gc", previous: bool = False):
    """
    Retrieve logs from a specific pod.
    
    Can retrieve current or previous (crashed) pod logs for debugging.
    Supports limiting the number of lines returned.
    
    Args:
        pod_name: Name of the pod to retrieve logs from
        lines: Number of log lines to retrieve (1-1000)
        namespace: Kubernetes namespace
        previous: Get logs from previous pod instance (if crashed)
        
    Returns:
        Dictionary with pod logs split into lines
    """
    try:
        if lines < 1 or lines > 1000:
            lines = 100
        
        logger.info(f"Retrieving {lines} lines of logs from pod: {pod_name}")
        
        logs_content = get_pod_logs(
            pod_name=pod_name,
            namespace=namespace,
            tail_lines=lines,
            previous=previous
        )
        
        return {
            "pod": pod_name,
            "namespace": namespace,
            "lines": logs_content.split("\n") if logs_content else [],
            "total_lines": len(logs_content.split("\n")) if logs_content else 0,
            "previous_instance": previous
        }
    except Exception as e:
        logger.error(f"Error retrieving logs for pod {pod_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")


@router.get("/")
async def list_pod_options(namespace: str = "free5gc"):
    """
    List all available pods for logging.
    
    Provides a list of pods from which logs can be retrieved.
    
    Args:
        namespace: Kubernetes namespace
        
    Returns:
        Dictionary with list of available pods
    """
    try:
        pods = list_pods(namespace=namespace)
        pod_names = [pod["name"] for pod in pods]
        
        return {
            "namespace": namespace,
            "available_pods": pod_names,
            "total": len(pod_names)
        }
    except Exception as e:
        logger.error(f"Error listing pods: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing pods: {str(e)}")
