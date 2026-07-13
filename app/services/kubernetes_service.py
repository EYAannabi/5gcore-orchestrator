from kubernetes import client, config

# Authentification unique au lancement
config.load_kube_config()
v1 = client.CoreV1Api()

def list_pods(namespace="free5gc"):
    pods = v1.list_namespaced_pod(namespace=namespace)
    result = []
    for pod in pods.items:
        result.append({
            "name": pod.metadata.name,
            "status": pod.status.phase,
            "ip": pod.status.pod_ip
        })
    return result

def get_node_status():
    """Récupère l'état de santé et les specs de la VM (Node)"""
    try:
        nodes = v1.list_node()
        node_list = []
        for node in nodes.items:
            node_list.append({
                "hostname": node.metadata.name,
                "status": node.status.conditions[-1].type,
                "os": node.status.node_info.os_image,
                "kernel": node.status.node_info.kernel_version,
                "kubelet_version": node.status.node_info.kubelet_version,
                "cpu_capacity": node.status.capacity.get("cpu"),
                "memory_capacity": node.status.capacity.get("memory")
            })
        return node_list
    except Exception as e:
        return {"error": str(e)}

def delete_specific_pod(pod_name, namespace="free5gc"):
    """Supprime un pod spécifique (Provoque un redémarrage automatique via K3s)"""
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return True, f"Le pod {pod_name} a été supprimé. K3s va le recréer."
    except Exception as e:
        return False, str(e)

def get_pod_logs(pod_name, namespace="free5gc", tail_lines=100):
    """Récupère les X dernières lignes de logs d'un pod spécifique"""
    try:
        logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, tail_lines=tail_lines)
        return logs
    except Exception as e:
        return f"Impossible de lire les logs : {str(e)}"
