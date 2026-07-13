import subprocess

def deploy_free5gc():
    """Déploie free5GC via Helm"""
    command = "helm install free5gc-helm ~/free5gc-helm/charts/free5gc --namespace free5gc --create-namespace"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def clean_free5gc():
    """Désinstalle free5GC"""
    command = "helm uninstall free5gc-helm --namespace free5gc"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr
