"""
Pydantic models for deployment configuration and API responses.
"""
import re
from enum import Enum 
from typing import Optional, List
from pydantic import BaseModel, Field, validator

class DeploymentMode(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class SliceType(str, Enum):
    EMBB = "eMBB"
    URLLC = "URLLC"
    MMTC = "mMTC"

class DeploymentConfig(BaseModel):
    operator_name: str = Field(..., description="Nom de l'opérateur")
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