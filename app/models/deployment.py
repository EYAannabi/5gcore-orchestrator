"""
Pydantic models for deployment configuration and API responses.
Provides type validation and automatic OpenAPI documentation.
"""

import re
from enum import Enum 
from typing import Optional, List
from pydantic import BaseModel, Field, validator

# --- ENUMS (Doivent être définis avant d'être utilisés dans les modèles) ---

class DeploymentMode(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class SliceType(str, Enum):
    """Network slice types for 5G"""
    EMBB = "eMBB"  # Enhanced Mobile Broadband
    URLLC = "URLLC"  # Ultra-Reliable Low-Latency
    MMTC = "mMTC"  # Massive Machine-Type Communications

# --- MODÈLES DE CONFIGURATION ---

class DeploymentConfig(BaseModel):
    """Complete deployment configuration from frontend"""
    
    # Information de l'opérateur (Crucial pour ton architecture Multi-Tenant)
    operator_name: str = Field(
        ..., 
        description="Nom de l'opérateur (orange, ooredoo, tunisie-telecom)"
    )

    # Basic information
    deployment_name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Kubernetes deployment name (alphanumeric, hyphens allowed)"
    )
    namespace: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Kubernetes namespace de l'opérateur"
    )
    
    # PLMN Configuration
    mcc: str = Field(
        default="208",
        min_length=3,
        max_length=3,
        description="Mobile Country Code (3 digits)"
    )
    mnc: str = Field(
        default="93",
        min_length=2,
        max_length=3,
        description="Mobile Network Code (2-3 digits)"
    )
    
    # Network configuration
    num_subscribers: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Number of simulated subscribers"
    )
    
    # Replica counts
    num_upf_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of UPF replicas"
    )
    num_smf_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of SMF replicas"
    )
    num_upf_replicas: int = Field( # Correction : était écrit deux fois UPF dans ton brouillon
        default=1,
        ge=1,
        le=10,
        description="Number of UPF replicas"
    )
    num_amf_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of AMF replicas"
    )
    
    # Features
    slice_type: SliceType = Field(
        default=SliceType.EMBB,
        description="Network slice type"
    )
    
    # Monitoring and exposure
    monitoring_enabled: bool = Field(default=True)
    expose_webui: bool = Field(default=True)
    enable_prometheus: bool = Field(default=True)
    
    # Deployment mode
    deployment_mode: DeploymentMode = Field(default=DeploymentMode.DEVELOPMENT)
    
    # Optional helm chart path
    helm_chart_path: Optional[str] = Field(default=None)
    
    # --- VALIDATEURS (NetDevOps logic) ---

    @validator('deployment_name')
    def validate_deployment_name(cls, v):
        """Vérifie que le nom respecte les standards Kubernetes"""
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', v):
            raise ValueError('Le nom du déploiement doit être en minuscules, alphanumérique avec des tirets.')
        return v.lower()
    
    @validator('mcc')
    def validate_mcc(cls, v):
        if not v.isdigit() or len(v) != 3:
            raise ValueError('MCC doit contenir exactement 3 chiffres')
        return v
    
    @validator('mnc')
    def validate_mnc(cls, v):
        if not v.isdigit() or len(v) not in [2, 3]:
            raise ValueError('MNC doit contenir 2 ou 3 chiffres')
        return v

# --- MODÈLES DE RÉPONSE API ---

class DeploymentResponse(BaseModel):
    status: str
    message: str
    deployment_name: Optional[str] = None
    namespace: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None

class PodInfo(BaseModel):
    name: str
    status: str
    ip: Optional[str]
    namespace: str
    age: Optional[str] = None
    restart_count: Optional[int] = 0

class NodeInfo(BaseModel):
    hostname: str
    status: str
    os: str
    kernel: str
    kubelet_version: str
    cpu_capacity: str
    memory_capacity: str

class DeploymentStatus(BaseModel):
    deployed: bool
    deployment_name: Optional[str] = None
    namespace: Optional[str] = None
    pods_total: int = 0
    pods_running: int = 0
    pods_failed: int = 0
    pod_list: List[PodInfo] = []
    node_info: Optional[NodeInfo] = None

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