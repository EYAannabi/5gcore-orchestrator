"""
Pydantic models for deployment configuration and API responses.
Provides type validation and automatic OpenAPI documentation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum


class DeploymentMode(str, Enum):
    """Deployment environment modes"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class SliceType(str, Enum):
    """Network slice types for 5G"""
    EMBB = "eMBB"  # Enhanced Mobile Broadband
    URLLC = "URLLC"  # Ultra-Reliable Low-Latency
    MMTC = "mMTC"  # Massive Machine-Type Communications


class DeploymentConfig(BaseModel):
    """Complete deployment configuration from frontend"""
    
    # Basic information
    deployment_name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Kubernetes deployment name (alphanumeric, hyphens allowed)"
    )
    namespace: str = Field(
        default="free5gc",
        min_length=1,
        max_length=63,
        description="Kubernetes namespace"
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
        default=10,
        ge=1,
        le=10000,
        description="Number of simulated subscribers"
    )
    
    # Replica counts
    num_upf_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of UPF (User Plane Function) replicas"
    )
    num_smf_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of SMF (Session Management Function) replicas"
    )
    num_amf_replicas: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Number of AMF (Access and Mobility Management Function) replicas"
    )
    
    # Features
    slice_type: SliceType = Field(
        default=SliceType.EMBB,
        description="Network slice type"
    )
    
    # Monitoring and exposure
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable Prometheus monitoring"
    )
    expose_webui: bool = Field(
        default=True,
        description="Expose Free5GC WebUI through ingress"
    )
    enable_prometheus: bool = Field(
        default=True,
        description="Deploy Prometheus for metrics collection"
    )
    
    # Deployment mode
    deployment_mode: DeploymentMode = Field(
        default=DeploymentMode.DEVELOPMENT,
        description="Development or Production mode"
    )
    
    # Optional helm chart path
    helm_chart_path: Optional[str] = Field(
        default=None,
        description="Custom Helm chart path (if None, uses default)"
    )
    
    @validator('deployment_name')
    def validate_deployment_name(cls, v):
        """Validate Kubernetes-compliant deployment name"""
        import re
        if not re.match(r'^[a-z0-9]([-a-z0-9]*[a-z0-9])?$', v):
            raise ValueError('Deployment name must start/end with alphanumeric, contain only alphanumeric and hyphens')
        return v.lower()
    
    @validator('mcc')
    def validate_mcc(cls, v):
        """Validate MCC format"""
        if not v.isdigit() or len(v) != 3:
            raise ValueError('MCC must be exactly 3 digits')
        return v
    
    @validator('mnc')
    def validate_mnc(cls, v):
        """Validate MNC format"""
        if not v.isdigit() or len(v) not in [2, 3]:
            raise ValueError('MNC must be 2 or 3 digits')
        return v


class DeploymentResponse(BaseModel):
    """Response from deployment API"""
    status: str = Field(..., description="Success or Error")
    message: str = Field(..., description="Status message")
    deployment_name: Optional[str] = None
    namespace: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


class PodInfo(BaseModel):
    """Information about a Kubernetes pod"""
    name: str
    status: str
    ip: Optional[str]
    namespace: str = "free5gc"
    age: Optional[str] = None
    restart_count: Optional[int] = 0
    containers: Optional[int] = 1
    
    class Config:
        schema_extra = {
            "example": {
                "name": "free5gc-amf-0",
                "status": "Running",
                "ip": "10.42.0.15",
                "namespace": "free5gc",
                "age": "2h 30m",
                "restart_count": 0
            }
        }


class NodeInfo(BaseModel):
    """Information about a Kubernetes node"""
    hostname: str
    status: str
    os: str
    kernel: str
    kubelet_version: str
    cpu_capacity: str
    memory_capacity: str
    
    class Config:
        schema_extra = {
            "example": {
                "hostname": "k3s-master",
                "status": "Ready",
                "os": "Ubuntu 22.04 LTS",
                "kernel": "5.15.0",
                "kubelet_version": "v1.27.0",
                "cpu_capacity": "4",
                "memory_capacity": "8Gi"
            }
        }


class DeploymentStatus(BaseModel):
    """Current deployment status"""
    deployed: bool
    deployment_name: Optional[str] = None
    namespace: Optional[str] = None
    pods_total: int = 0
    pods_running: int = 0
    pods_failed: int = 0
    pod_list: List[PodInfo] = []
    node_info: Optional[NodeInfo] = None


class SettingsModel(BaseModel):
    """Application settings"""
    default_namespace: str = Field(default="free5gc")
    default_helm_chart_path: str = Field(default="~/free5gc-helm/charts/free5gc")
    refresh_interval: int = Field(default=5, ge=1, le=60, description="Refresh interval in seconds")
    dark_mode: bool = Field(default=True)
    auto_deploy_monitoring: bool = Field(default=True)
    
    class Config:
        schema_extra = {
            "example": {
                "default_namespace": "free5gc",
                "default_helm_chart_path": "~/free5gc-helm/charts/free5gc",
                "refresh_interval": 5,
                "dark_mode": True,
                "auto_deploy_monitoring": True
            }
        }


class ApiResponse(BaseModel):
    """Standard API response wrapper"""
    status: str = Field(..., description="success or error")
    message: str = Field(..., description="Status message")
    data: Optional[dict] = None
    error_details: Optional[str] = None
