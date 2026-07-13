"""
Kubernetes service for managing and monitoring 5G Core deployments.
Handles pod management, node information, and cluster status.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configure logging
logger = logging.getLogger(__name__)

# Load Kubernetes configuration
try:
    config.load_kube_config()
    logger.info("Kubernetes configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load Kubernetes configuration: {e}")
    raise

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


def list_pods(namespace: str = "free5gc") -> List[Dict[str, Any]]:
    """
    Retrieve all pods in the specified namespace.
    
    Args:
        namespace: Kubernetes namespace to query
        
    Returns:
        List of pod information dictionaries
    """
    try:
        pods = v1.list_namespaced_pod(namespace=namespace)
        result = []
        for pod in pods.items:
            # Calculate pod age
            age = _calculate_age(pod.metadata.creation_timestamp)
            
            result.append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip,
                "namespace": namespace,
                "age": age,
                "restart_count": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                "containers": len(pod.spec.containers) if pod.spec.containers else 0
            })
        logger.info(f"Retrieved {len(result)} pods from namespace {namespace}")
        return result
    except ApiException as e:
        logger.error(f"Kubernetes API error listing pods: {e}")
        return []
    except Exception as e:
        logger.error(f"Error listing pods: {e}")
        return []


def get_node_status() -> List[Dict[str, Any]]:
    """
    Retrieve node information and cluster health status.
    
    Returns:
        List of node information dictionaries
    """
    try:
        nodes = v1.list_node()
        node_list = []
        
        for node in nodes.items:
            # Get node status
            status = "Unknown"
            for condition in node.status.conditions:
                if condition.type == "Ready":
                    status = "Ready" if condition.status == "True" else "NotReady"
                    break
            
            node_list.append({
                "hostname": node.metadata.name,
                "status": status,
                "os": node.status.node_info.os_image,
                "kernel": node.status.node_info.kernel_version,
                "kubelet_version": node.status.node_info.kubelet_version,
                "cpu_capacity": node.status.capacity.get("cpu"),
                "memory_capacity": node.status.capacity.get("memory"),
                "allocatable_cpu": node.status.allocatable.get("cpu"),
                "allocatable_memory": node.status.allocatable.get("memory")
            })
        logger.info(f"Retrieved information for {len(node_list)} nodes")
        return node_list
    except ApiException as e:
        logger.error(f"Kubernetes API error getting node status: {e}")
        return []
    except Exception as e:
        logger.error(f"Error getting node status: {e}")
        return []


def delete_specific_pod(pod_name: str, namespace: str = "free5gc") -> Tuple[bool, str]:
    """
    Delete a specific pod (triggers automatic restart via Kubernetes).
    
    Args:
        pod_name: Name of the pod to delete
        namespace: Kubernetes namespace
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        v1.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            grace_period_seconds=30
        )
        message = f"Pod '{pod_name}' deleted successfully. Kubernetes will recreate it."
        logger.info(message)
        return True, message
    except ApiException as e:
        if e.status == 404:
            message = f"Pod '{pod_name}' not found in namespace '{namespace}'"
        else:
            message = f"Failed to delete pod: {e.reason}"
        logger.error(message)
        return False, message
    except Exception as e:
        message = f"Error deleting pod: {str(e)}"
        logger.error(message)
        return False, message


def get_pod_logs(
    pod_name: str,
    namespace: str = "free5gc",
    tail_lines: int = 100,
    previous: bool = False
) -> str:
    """
    Retrieve logs from a specific pod.
    
    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        tail_lines: Number of lines to retrieve
        previous: Get logs from previous container instance
        
    Returns:
        Pod logs as string
    """
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            previous=previous
        )
        logger.info(f"Retrieved logs from pod '{pod_name}'")
        return logs if logs else "No logs available"
    except ApiException as e:
        message = f"Failed to retrieve logs: {e.reason}"
        logger.error(message)
        return message
    except Exception as e:
        message = f"Error retrieving logs: {str(e)}"
        logger.error(message)
        return message


def check_deployment_status(namespace: str = "free5gc") -> Dict[str, Any]:
    """
    Check overall deployment status in the namespace.
    
    Args:
        namespace: Kubernetes namespace
        
    Returns:
        Dictionary with deployment status information
    """
    try:
        pods = list_pods(namespace)
        
        if not pods:
            return {
                "deployed": False,
                "pods_total": 0,
                "pods_running": 0,
                "pods_failed": 0
            }
        
        pods_running = sum(1 for pod in pods if pod["status"] == "Running")
        pods_failed = sum(1 for pod in pods if pod["status"] != "Running")
        
        return {
            "deployed": True,
            "pods_total": len(pods),
            "pods_running": pods_running,
            "pods_failed": pods_failed,
            "pod_list": pods,
            "node_info": get_node_status()[0] if get_node_status() else None
        }
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")
        return {
            "deployed": False,
            "pods_total": 0,
            "pods_running": 0,
            "pods_failed": 0,
            "error": str(e)
        }


def _calculate_age(creation_timestamp) -> str:
    """
    Calculate how long a pod has been running.
    
    Args:
        creation_timestamp: Pod creation timestamp from Kubernetes
        
    Returns:
        Human-readable age string
    """
    try:
        if creation_timestamp is None:
            return "Unknown"
        
        # Handle timezone-aware datetime
        if creation_timestamp.tzinfo is not None:
            age_delta = datetime.now(creation_timestamp.tzinfo) - creation_timestamp
        else:
            age_delta = datetime.utcnow() - creation_timestamp
        
        total_seconds = int(age_delta.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m"
        elif total_seconds < 86400:
            return f"{total_seconds // 3600}h"
        else:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            return f"{days}d {hours}h"
    except Exception as e:
        logger.warning(f"Error calculating pod age: {e}")
        return "Unknown"


def scale_deployment(
    deployment_name: str,
    replicas: int,
    namespace: str = "free5gc"
) -> Tuple[bool, str]:
    """
    Scale a Kubernetes deployment to a specific number of replicas.
    
    Args:
        deployment_name: Name of the deployment to scale
        replicas: Target number of replicas
        namespace: Kubernetes namespace
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        deployment.spec.replicas = replicas
        apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
        message = f"Scaled deployment '{deployment_name}' to {replicas} replicas"
        logger.info(message)
        return True, message
    except ApiException as e:
        if e.status == 404:
            message = f"Deployment '{deployment_name}' not found in namespace '{namespace}'"
        else:
            message = f"Failed to scale deployment: {e.reason}"
        logger.error(message)
        return False, message
    except Exception as e:
        message = f"Error scaling deployment: {str(e)}"
        logger.error(message)
        return False, message


def restart_deployment(
    deployment_name: str,
    namespace: str = "free5gc"
) -> Tuple[bool, str]:
    """
    Restart a deployment by triggering a rollout restart (pod recreation).
    
    Args:
        deployment_name: Name of the deployment to restart
        namespace: Kubernetes namespace
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        
        # Trigger a rollout restart by updating pod spec annotation
        deployment.spec.template.metadata.annotations = deployment.spec.template.metadata.annotations or {}
        deployment.spec.template.metadata.annotations['kubectl.kubernetes.io/restartedAt'] = datetime.now().isoformat()
        
        apps_v1.patch_namespaced_deployment(deployment_name, namespace, deployment)
        message = f"Restarted deployment '{deployment_name}'"
        logger.info(message)
        return True, message
    except ApiException as e:
        if e.status == 404:
            message = f"Deployment '{deployment_name}' not found in namespace '{namespace}'"
        else:
            message = f"Failed to restart deployment: {e.reason}"
        logger.error(message)
        return False, message
    except Exception as e:
        message = f"Error restarting deployment: {str(e)}"
        logger.error(message)
        return False, message


def wait_for_pods(
    namespace: str = "free5gc",
    expected_count: int = 1,
    timeout_seconds: int = 300
) -> Tuple[bool, int]:
    """
    Wait for a specific number of pods to be in Running state.
    
    Args:
        namespace: Kubernetes namespace
        expected_count: Expected number of Running pods
        timeout_seconds: Maximum time to wait
        
    Returns:
        Tuple of (success: bool, actual_count: int)
    """
    import time
    start_time = datetime.utcnow()
    
    while True:
        pods = list_pods(namespace)
        running_count = sum(1 for pod in pods if pod["status"] == "Running")
        
        if running_count >= expected_count:
            logger.info(f"Found {running_count} running pods in namespace {namespace}")
            return True, running_count
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        if elapsed > timeout_seconds:
            logger.warning(f"Timeout waiting for {expected_count} running pods. Current: {running_count}")
            return False, running_count
        
        time.sleep(5)  # Check every 5 seconds


def delete_specific_pod(pod_name: str, namespace: str = "free5gc") -> Tuple[bool, str]:
    """
    Delete a specific pod (triggers automatic restart via Kubernetes).
    
    Args:
        pod_name: Name of the pod to delete
        namespace: Kubernetes namespace
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        v1.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            grace_period_seconds=30
        )
        message = f"Pod '{pod_name}' deleted successfully. Kubernetes will recreate it."
        logger.info(message)
        return True, message
    except ApiException as e:
        if e.status == 404:
            message = f"Pod '{pod_name}' not found in namespace '{namespace}'"
        else:
            message = f"Failed to delete pod: {e.reason}"
        logger.error(message)
        return False, message
    except Exception as e:
        message = f"Error deleting pod: {str(e)}"
        logger.error(message)
        return False, message


def get_pod_logs(
    pod_name: str,
    namespace: str = "free5gc",
    tail_lines: int = 100,
    previous: bool = False
) -> str:
    """
    Retrieve logs from a specific pod.
    
    Args:
        pod_name: Name of the pod
        namespace: Kubernetes namespace
        tail_lines: Number of lines to retrieve
        previous: Get logs from previous container instance
        
    Returns:
        Pod logs as string
    """
    try:
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            tail_lines=tail_lines,
            previous=previous
        )
        logger.info(f"Retrieved logs from pod '{pod_name}'")
        return logs if logs else "No logs available"
    except ApiException as e:
        message = f"Failed to retrieve logs: {e.reason}"
        logger.error(message)
        return message
    except Exception as e:
        message = f"Error retrieving logs: {str(e)}"
        logger.error(message)
        return message


def check_deployment_status(namespace: str = "free5gc") -> Dict[str, Any]:
    """
    Check overall deployment status in the namespace.
    
    Args:
        namespace: Kubernetes namespace
        
    Returns:
        Dictionary with deployment status information
    """
    try:
        pods = list_pods(namespace)
        
        if not pods:
            return {
                "deployed": False,
                "pods_total": 0,
                "pods_running": 0,
                "pods_failed": 0
            }
        
        pods_running = sum(1 for pod in pods if pod["status"] == "Running")
        pods_failed = sum(1 for pod in pods if pod["status"] != "Running")
        
        return {
            "deployed": True,
            "pods_total": len(pods),
            "pods_running": pods_running,
            "pods_failed": pods_failed,
            "pod_list": pods,
            "node_info": get_node_status()[0] if get_node_status() else None
        }
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}")
        return {
            "deployed": False,
            "pods_total": 0,
            "pods_running": 0,
            "pods_failed": 0,
            "error": str(e)
        }
