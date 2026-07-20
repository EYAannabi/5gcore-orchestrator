"""
Pydantic models for deployment configuration and API responses.
Version complète incluant les modèles de supervision (PodInfo, NodeInfo).
"""
import re
from enum import Enum 
from typing import Optional, List
from pydantic import BaseModel, Field, validator

# --- ENUMS ---

class DeploymentMode(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class SliceType(str, Enum):
    EMBB = "eMBB"
    URLLC = "URLLC"
    MMTC = "mMTC"

# --- MODÈLES POUR LE DÉPLOIEMENT (Utilisés par deploy.py) ---

class DeploymentConfig(BaseModel):
    operator_name: str = Field(..., description="Nom de l'opérateur (orange, ooredoo, tunisie-telecom)")
    deployment_name: str = Field(..., min_length=1, max_length=63)
    namespace: str = Field(..., min_length=1, max_length=63)
    
    mcc: str = Field(default="208")
    mnc: str = Field(default="93")
    num_subscribers: int = Field(default=1000)
    
    num_upf_replicas: int = Field(default=1)
    num_smf_replicas: int = Field(default=1)
    num_amf_replicas: int = Field(default=1)
    
    slice_type: SliceType = Field(default=SliceType.EMBB)
    monitoring_enabled: bool = Field(default=True)
    expose_webui: bool = Field(default=True)
    enable_prometheus: bool = Field(default=True)
    deployment_mode: DeploymentMode = Field(default=DeploymentMode.DEVELOPMENT)
    helm_chart_path: Optional[str] = Field(default=None)
    
    @validator('deployment_name')
    def validate_deployment_name(cls, v):
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', v):
            raise ValueError('Nom invalide (minuscules et tirets uniquement)')
        return v.lower()

class DeploymentResponse(BaseModel):
    status: str
    message: str
    deployment_name: Optional[str] = None
    namespace: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None

# --- MODÈLES POUR LA SUPERVISION (Utilisés par pods.py) ---

class PodInfo(BaseModel):
    """Information sur un Pod Kubernetes"""
    name: str
    status: str
    ip: Optional[str] = "N/A"
    namespace: str = "default"
    age: Optional[str] = "N/A"
    restart_count: Optional[int] = 0

class NodeInfo(BaseModel):
    """Information sur un Node du cluster"""
    hostname: str
    status: str
    os: str
    kernel: str
    kubelet_version: str
    cpu_capacity: str
    memory_capacity: str

class DeploymentStatus(BaseModel):
    """État global du déploiement"""
    deployed: bool
    deployment_name: Optional[str] = None
    namespace: Optional[str] = None
    pods_total: int = 0
    pods_running: int = 0
    pods_failed: int = 0
    pod_list: List[PodInfo] = []
    node_info: Optional[NodeInfo] = None

# --- AUTRES MODÈLES ---

class SettingsModel(BaseModel):
    default_namespace: str = "free5gc"
    default_helm_chart_path: str = "~/free5gc-helm/charts/free5gc"
    refresh_interval: int = 5
    dark_mode: bool = True

class ApiResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None
    error_details: Optional[str] = None