"""
Kubernetes service for managing and monitoring 5G Core deployments.
Handles pod management, node information, and cluster status.
"""

import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configure logging
logger = logging.getLogger(__name__)

# Load Kubernetes configuration. The API must still start on machines that do
# not have kubeconfig available; route handlers will report empty/error results.
KUBE_CONFIGURED = False
try:
    config.load_kube_config()
    KUBE_CONFIGURED = True
    logger.info("Kubernetes configuration loaded successfully")
except Exception as e:
    try:
        config.load_incluster_config()
        KUBE_CONFIGURED = True
        logger.info("In-cluster Kubernetes configuration loaded successfully")
    except Exception:
        logger.warning(f"Kubernetes configuration not available: {e}")

v1 = client.CoreV1Api() if KUBE_CONFIGURED else None
apps_v1 = client.AppsV1Api() if KUBE_CONFIGURED else None


def list_pods(namespace: str = "free5gc") -> List[Dict[str, Any]]:
    """
    Retrieve all pods in the specified namespace, or across all namespaces
    if namespace is None (used by the admin multi-operator dashboard).

    Args:
        namespace: Kubernetes namespace to query, or None for all namespaces

    Returns:
        List of pod information dictionaries
    """
    try:
        if not v1:
            logger.warning("Kubernetes client is not configured; returning no pods")
            return []

        if namespace is None:
            pods = v1.list_pod_for_all_namespaces()
        else:
            pods = v1.list_namespaced_pod(namespace=namespace)

        result = []
        for pod in pods.items:
            age = _calculate_age(pod.metadata.creation_timestamp)

            result.append({
                "name": pod.metadata.name,
                "status": pod.status.phase,
                "ip": pod.status.pod_ip,
                "namespace": pod.metadata.namespace,  # toujours le vrai namespace du pod
                "age": age,
                "restart_count": pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                "containers": len(pod.spec.containers) if pod.spec.containers else 0
            })
        logger.info(f"Retrieved {len(result)} pods from namespace {namespace or 'ALL'}")
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
        if not v1:
            logger.warning("Kubernetes client is not configured; returning no nodes")
            return []

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
        if not v1:
            message = "Kubernetes client is not configured"
            logger.error(message)
            return False, message

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
        if not v1:
            message = "Kubernetes client is not configured"
            logger.error(message)
            return message

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
        if not apps_v1:
            message = "Kubernetes client is not configured"
            logger.error(message)
            return False, message

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


def list_deployments(namespace: str = "free5gc") -> List[Dict[str, Any]]:
    """
    Retrieve Kubernetes deployments in a namespace.

    Args:
        namespace: Kubernetes namespace to query

    Returns:
        List of deployment dictionaries with name and replica information.
    """
    try:
        if not apps_v1:
            logger.warning("Kubernetes client is not configured; returning no deployments")
            return []

        deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
        return [
            {
                "name": deployment.metadata.name,
                "namespace": namespace,
                "replicas": deployment.spec.replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
            }
            for deployment in deployments.items
        ]
    except ApiException as e:
        logger.error(f"Kubernetes API error listing deployments: {e}")
        return []
    except Exception as e:
        logger.error(f"Error listing deployments: {e}")
        return []


def find_network_function_deployments(
    deployment_name: str,
    network_function: str,
    namespace: str = "free5gc"
) -> List[str]:
    """
    Find Kubernetes Deployment names for a Free5GC network function.

    Free5GC Helm charts often create names like:
    free5gc-helm-free5gc-ausf-ausf, not free5gc-helm-ausf.
    """
    nf = network_function.lower()
    release = deployment_name.lower()
    candidates = []

    for deployment in list_deployments(namespace):
        name = deployment["name"]
        lowered = name.lower()
        tokens = lowered.split("-")

        if release not in lowered:
            continue

        if nf in tokens or lowered.endswith(f"-{nf}") or f"-{nf}-" in lowered:
            candidates.append(name)

    def sort_key(name: str):
        lowered = name.lower()
        exact_tail = lowered.endswith(f"-{nf}")
        repeated_component = f"-{nf}-{nf}" in lowered
        return (not exact_tail, not repeated_component, len(lowered))

    candidates.sort(key=sort_key)
    return candidates


def scale_network_function(
    deployment_name: str,
    network_function: str,
    replicas: int,
    namespace: str = "free5gc"
) -> Tuple[bool, str, List[str]]:
    """Scale all Kubernetes deployments matching a Free5GC network function."""
    deployments = find_network_function_deployments(deployment_name, network_function, namespace)
    if not deployments:
        message = (
            f"No Kubernetes Deployment found for network function '{network_function}' "
            f"under release '{deployment_name}' in namespace '{namespace}'"
        )
        logger.error(message)
        return False, message, []

    failures = []
    for name in deployments:
        success, message = scale_deployment(name, replicas, namespace)
        if not success:
            failures.append(message)

    if failures:
        return False, "; ".join(failures), deployments

    message = f"Scaled {network_function} deployment(s) {deployments} to {replicas} replicas"
    logger.info(message)
    return True, message, deployments


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
        if not apps_v1:
            message = "Kubernetes client is not configured"
            logger.error(message)
            return False, message

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


def restart_network_function(
    deployment_name: str,
    network_function: str,
    namespace: str = "free5gc"
) -> Tuple[bool, str, List[str]]:
    """Restart all Kubernetes deployments matching a Free5GC network function."""
    deployments = find_network_function_deployments(deployment_name, network_function, namespace)
    if not deployments:
        message = (
            f"No Kubernetes Deployment found for network function '{network_function}' "
            f"under release '{deployment_name}' in namespace '{namespace}'"
        )
        logger.error(message)
        return False, message, []

    failures = []
    for name in deployments:
        success, message = restart_deployment(name, namespace)
        if not success:
            failures.append(message)

    if failures:
        return False, "; ".join(failures), deployments

    message = f"Restarted {network_function} deployment(s): {deployments}"
    logger.info(message)
    return True, message, deployments


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
def get_operator_namespaces():
    """Liste les namespaces des opérateurs (*-5g)"""
    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace().items
    return [ns.metadata.name for ns in namespaces if ns.metadata.name.endswith("-5g")]

def get_cluster_health():
    """Vérifie si les nodes sont Ready"""
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    ready_nodes = 0
    for node in nodes:
        if any(c.type == "Ready" and c.status == "True" for c in node.status.conditions):
            ready_nodes += 1
    
    status = "Healthy" if ready_nodes == len(nodes) else "Warning"
    if ready_nodes == 0: status = "Critical"
    
    return {"status": status, "nodes_ready": ready_nodes, "nodes_total": len(nodes)}

def get_all_pods_stats():
    """Compte les pods par statut dans TOUT le cluster"""
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces().items
    stats = {"Running": 0, "Pending": 0, "Failed": 0}
    for pod in pods:
        phase = pod.status.phase
        if phase in stats:
            stats[phase] += 1
    return stats

def get_operator_status_detailed():
    v1 = client.CoreV1Api()
    operators = get_operator_namespaces()
    detailed_list = []
    
    for ns in operators:
        pods = v1.list_namespaced_pod(ns).items
        running_pods = [p for p in pods if p.status.phase == "Running"]
        
        # Récupérer le préfixe/nom de release depuis le premier pod trouvé
        deployment_name = "free5gc-helm"
        if len(pods) > 0:
            # Ex: si le pod s'appelle 'sousse-core-free5gc-amf-...', on extrait 'sousse-core'
            first_pod = pods[0].metadata.name
            if "-free5gc-" in first_pod:
                deployment_name = first_pod.split("-free5gc-")[0]

        status = "Running" if len(running_pods) == len(pods) and len(pods) > 0 else "Degraded"
        if len(pods) == 0: status = "Stopped"
        
        detailed_list.append({
            "name": ns.replace("-5g", "").upper(),
            "namespace": ns,
            "deployment_name": deployment_name, # <--- ON AJOUTE LE VRAI NOM
            "pod_count": len(pods),
            "running_count": len(running_pods),
            "status": status,
            "webui_url": f"http://192.168.140.128:30600"
        })
    return detailed_list

def get_cluster_resources():
    """Récupère l'utilisation CPU/RAM (Nécessite metrics-server)"""
    try:
        custom_api = client.CustomObjectsApi()
        metrics = custom_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        
        # Calcul simplifié pour la démo
        total_cpu = 0
        total_mem = 0
        for node in metrics['items']:
            # Conversion brute (nanocores et kibibytes)
            total_cpu += int(node['usage']['cpu'].replace('n', '')) / 1000000
            total_mem += int(node['usage']['memory'].replace('Ki', '')) / 1024
            
        return {
            "cpu_usage_mhz": round(total_cpu, 2),
            "mem_usage_mb": round(total_mem, 2)
        }
    except:
        return {"cpu": "N/A", "ram": "N/A"}