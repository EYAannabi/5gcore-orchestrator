"""
Helm service for deploying and managing Free5GC through Helm charts.
Handles dynamic configuration and lifecycle management.
"""

import subprocess
import logging
import os
from typing import Tuple, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HelmCommandError(Exception):
    """Custom exception for Helm command failures"""
    pass


def deploy_free5gc(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc",
    chart_path: Optional[str] = None,
    values: Optional[Dict[str, Any]] = None,
    create_namespace: bool = True
) -> Tuple[bool, str, str]:
    """
    Deploy Free5GC using Helm with dynamic configuration.
    
    Args:
        deployment_name: Release name for Helm deployment
        namespace: Kubernetes namespace to deploy into
        chart_path: Path to Helm chart (uses default if None)
        values: Dictionary of Helm values to override
        create_namespace: Whether to create namespace if it doesn't exist
        
    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    try:
        if chart_path is None:
            chart_path = os.path.expanduser("~/free5gc-helm/charts/free5gc")
        
        # Verify chart exists
        if not Path(chart_path).exists():
            raise HelmCommandError(f"Helm chart not found at: {chart_path}")
        
        # Build Helm command
        cmd = ["helm", "install", deployment_name, chart_path]
        cmd.extend(["--namespace", namespace])
        
        if create_namespace:
            cmd.append("--create-namespace")
        
        # Add values overrides
        if values:
            for key, value in values.items():
                cmd.extend(["--set", f"{key}={_format_helm_value(value)}"])
        
        logger.info(f"Executing Helm command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info(f"Successfully deployed {deployment_name} in namespace {namespace}")
            return True, result.stdout, result.stderr
        else:
            error_msg = f"Helm deployment failed: {result.stderr}"
            logger.error(error_msg)
            return False, result.stdout, error_msg
            
    except subprocess.TimeoutExpired:
        error = "Helm deployment timed out after 5 minutes"
        logger.error(error)
        return False, "", error
    except HelmCommandError as e:
        logger.error(str(e))
        return False, "", str(e)
    except Exception as e:
        error = f"Unexpected error during Helm deployment: {str(e)}"
        logger.error(error)
        return False, "", error


def clean_free5gc(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
) -> Tuple[bool, str, str]:
    """
    Uninstall Free5GC Helm release and clean up.
    
    Args:
        deployment_name: Release name to uninstall
        namespace: Kubernetes namespace
        
    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    try:
        cmd = ["helm", "uninstall", deployment_name, "--namespace", namespace]
        
        logger.info(f"Executing cleanup command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info(f"Successfully uninstalled {deployment_name} from namespace {namespace}")
            return True, result.stdout, result.stderr
        else:
            error_msg = f"Helm cleanup failed: {result.stderr}"
            logger.error(error_msg)
            return False, result.stdout, error_msg
            
    except subprocess.TimeoutExpired:
        error = "Helm cleanup timed out after 2 minutes"
        logger.error(error)
        return False, "", error
    except Exception as e:
        error = f"Error during Helm cleanup: {str(e)}"
        logger.error(error)
        return False, "", error


def get_deployment_status(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
) -> Optional[Dict[str, Any]]:
    """
    Get the status of a Helm release.
    
    Args:
        deployment_name: Release name
        namespace: Kubernetes namespace
        
    Returns:
        Dictionary with deployment status or None if not found
    """
    try:
        cmd = ["helm", "status", deployment_name, "--namespace", namespace, "-o", "json"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            status = json.loads(result.stdout)
            logger.info(f"Retrieved status for {deployment_name}")
            return status
        else:
            logger.warning(f"Could not retrieve status for {deployment_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return None


def get_helm_values(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
) -> Optional[Dict[str, Any]]:
    """
    Get the current Helm values for a release.
    
    Args:
        deployment_name: Release name
        namespace: Kubernetes namespace
        
    Returns:
        Dictionary with Helm values or None if not found
    """
    try:
        cmd = ["helm", "get", "values", deployment_name, "--namespace", namespace, "-o", "json"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            values = json.loads(result.stdout)
            logger.info(f"Retrieved values for {deployment_name}")
            return values
        else:
            logger.warning(f"Could not retrieve values for {deployment_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting Helm values: {e}")
        return None


def build_helm_values(config) -> Dict[str, str]:
    """
    Convert deployment configuration to Helm values.
    
    Args:
        config: DeploymentConfig object
        
    Returns:
        Dictionary of Helm key-value pairs
    """
    values = {
        # Global configuration
        "global.projectName": config.deployment_name,
        
        # PLMN configuration
        "global.mcc": config.mcc,
        "global.mnc": config.mnc,
        
        # Slice configuration
        "slice.type": config.slice_type.value,
        
        # Replica counts
        "upf.replicas": str(config.num_upf_replicas),
        "smf.replicas": str(config.num_smf_replicas),
        "amf.replicas": str(config.num_amf_replicas),
        
        # Features
        "webui.enabled": "true" if config.expose_webui else "false",
        "prometheus.enabled": "true" if config.enable_prometheus else "false",
        
        # Monitoring
        "monitoring.enabled": "true" if config.monitoring_enabled else "false",
    }
    
    # Add deployment mode specific settings
    if config.deployment_mode.value == "production":
        values["resources.requests.cpu"] = "500m"
        values["resources.requests.memory"] = "512Mi"
        values["affinity.enabled"] = "true"
    else:
        values["resources.requests.cpu"] = "100m"
        values["resources.requests.memory"] = "128Mi"
        values["affinity.enabled"] = "false"
    
    logger.info(f"Built Helm values for deployment: {config.deployment_name}")
    logger.debug(f"Helm values: {values}")
    
    return values


def _format_helm_value(value: Any) -> str:
    """
    Format Python value for Helm --set parameter.
    
    Args:
        value: Value to format
        
    Returns:
        Formatted string for Helm
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        # Escape special characters
        return f'"{value}"' if any(c in value for c in ' "\'$') else value
    else:
        return str(value)
