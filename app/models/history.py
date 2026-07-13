"""
Data models for deployment history, operations, and validation results.
Provides type-safe storage and tracking of all platform operations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OperationType(str, Enum):
    """Types of deployment operations"""
    DEPLOY = "deploy"
    UPGRADE = "upgrade"
    SCALE = "scale"
    RESTART = "restart"
    ROLLBACK = "rollback"
    DELETE = "delete"
    MODIFY_PARAMS = "modify_params"


class OperationStatus(str, Enum):
    """Status of an operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ValidationTestType(str, Enum):
    """Types of validation tests"""
    POD_HEALTH = "pod_health"  # Check all pods Running
    AMF_REGISTRATION = "amf_registration"  # Verify AMF has registered devices
    UE_REGISTRATION = "ue_registration"  # Verify UE registered via UERANSIM
    PDU_SESSION = "pdu_session"  # Verify PDU session established
    CONNECTIVITY = "connectivity"  # Verify internet connectivity via uesimtun0


class TestStatus(str, Enum):
    """Result of a validation test"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class OperationHistory(BaseModel):
    """Record of a deployment operation"""
    
    id: Optional[int] = None  # Database primary key
    operation_type: OperationType = Field(..., description="Type of operation performed")
    deployment_name: str = Field(..., description="Deployment name (or deployment identifier)")
    namespace: str = Field(default="free5gc", description="Kubernetes namespace")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When operation occurred")
    status: OperationStatus = Field(default=OperationStatus.PENDING, description="Operation outcome")
    
    # Operation details
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters (what was changed)")
    result: Optional[str] = Field(None, description="Operation result/output")
    error_message: Optional[str] = Field(None, description="Error if operation failed")
    duration_seconds: Optional[float] = Field(None, description="How long operation took")
    
    # Helm-specific
    helm_revision: Optional[int] = Field(None, description="Helm release revision number")
    previous_revision: Optional[int] = Field(None, description="Previous revision (for rollback)")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "operation_type": "deploy",
                "deployment_name": "free5gc-helm",
                "namespace": "free5gc",
                "timestamp": "2026-07-13T09:30:00Z",
                "status": "success",
                "parameters": {"mcc": "208", "mnc": "93", "deployment_mode": "production"},
                "result": "Deployment successful",
                "helm_revision": 1,
                "duration_seconds": 45.5
            }
        }


class ValidationTestResult(BaseModel):
    """Result of a single validation test"""
    
    test_name: str = Field(..., description="Display name of the test")
    test_type: ValidationTestType = Field(..., description="Type of validation test")
    status: TestStatus = Field(..., description="Test outcome")
    
    # Test details
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: Optional[float] = Field(None, description="How long test took")
    
    # Result details
    details: Dict[str, Any] = Field(default_factory=dict, description="Test-specific details")
    error_message: Optional[str] = Field(None, description="Error if test failed")
    
    # Affected resources
    checked_pods: Optional[List[str]] = Field(None, description="Pods that were checked")
    expected_count: Optional[int] = Field(None, description="Expected resource count")
    actual_count: Optional[int] = Field(None, description="Actual resource count")
    
    class Config:
        schema_extra = {
            "example": {
                "test_name": "Pod Health Check",
                "test_type": "pod_health",
                "status": "passed",
                "timestamp": "2026-07-13T09:35:00Z",
                "duration_seconds": 2.5,
                "details": {"total_pods": 5, "running_pods": 5, "failed_pods": 0},
                "checked_pods": ["free5gc-amf-0", "free5gc-smf-0", "free5gc-upf-0"],
                "expected_count": 5,
                "actual_count": 5
            }
        }


class ValidationReport(BaseModel):
    """Complete validation report for a deployment"""
    
    id: Optional[int] = None  # Database primary key
    deployment_name: str = Field(..., description="Deployment being validated")
    namespace: str = Field(default="free5gc", description="Kubernetes namespace")
    
    # Report metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When validation was run")
    total_duration_seconds: Optional[float] = Field(None, description="Total time for all tests")
    
    # Test results
    tests: List[ValidationTestResult] = Field(default_factory=list, description="Individual test results")
    
    # Summary
    tests_passed: int = Field(default=0, description="Number of tests passed")
    tests_failed: int = Field(default=0, description="Number of tests failed")
    tests_skipped: int = Field(default=0, description="Number of tests skipped")
    tests_total: int = Field(default=0, description="Total tests run")
    
    # Overall status
    overall_status: TestStatus = Field(..., description="PASSED if all passed, FAILED if any failed")
    summary: str = Field(default="", description="Human-readable summary of results")
    
    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "deployment_name": "free5gc-helm",
                "namespace": "free5gc",
                "timestamp": "2026-07-13T09:35:00Z",
                "total_duration_seconds": 15.3,
                "tests": [],
                "tests_passed": 5,
                "tests_failed": 0,
                "tests_skipped": 0,
                "tests_total": 5,
                "overall_status": "passed",
                "summary": "All validation tests passed successfully"
            }
        }


class DeploymentRevision(BaseModel):
    """Helm release revision information"""
    
    revision: int = Field(..., description="Revision number")
    app_version: str = Field(..., description="Free5GC version")
    status: str = Field(..., description="Release status (deployed, superseded, etc)")
    updated: datetime = Field(..., description="When this revision was deployed")
    description: str = Field(..., description="Release description")
    deployment_name: str = Field(..., description="Release name")
    
    class Config:
        schema_extra = {
            "example": {
                "revision": 2,
                "app_version": "3.0.6",
                "status": "deployed",
                "updated": "2026-07-13T09:30:00Z",
                "description": "upgrade complete",
                "deployment_name": "free5gc-helm"
            }
        }


class ScaleRequest(BaseModel):
    """Request to scale a network function"""
    
    network_function: str = Field(
        ...,
        description="NF to scale: amf, smf, upf, ausf, nssf, pcf, udm, udr",
        pattern="^(amf|smf|upf|ausf|nssf|pcf|udm|udr)$"
    )
    replicas: int = Field(..., ge=1, le=10, description="Target number of replicas")
    deployment_name: str = Field(..., description="Deployment name")
    namespace: str = Field(default="free5gc", description="Kubernetes namespace")
    
    class Config:
        schema_extra = {
            "example": {
                "network_function": "upf",
                "replicas": 3,
                "deployment_name": "free5gc-helm",
                "namespace": "free5gc"
            }
        }


class RestartRequest(BaseModel):
    """Request to restart a network function"""
    
    network_function: str = Field(
        ...,
        description="NF to restart: amf, smf, upf, ausf, nssf, pcf, udm, udr, webui",
        pattern="^(amf|smf|upf|ausf|nssf|pcf|udm|udr|webui)$"
    )
    deployment_name: str = Field(..., description="Deployment name")
    namespace: str = Field(default="free5gc", description="Kubernetes namespace")
    
    class Config:
        schema_extra = {
            "example": {
                "network_function": "amf",
                "deployment_name": "free5gc-helm",
                "namespace": "free5gc"
            }
        }


class RollbackRequest(BaseModel):
    """Request to rollback to a previous Helm revision"""
    
    deployment_name: str = Field(..., description="Deployment name")
    namespace: str = Field(default="free5gc", description="Kubernetes namespace")
    revision: Optional[int] = Field(None, description="Target revision (if None, rollback 1 step)")
    
    class Config:
        schema_extra = {
            "example": {
                "deployment_name": "free5gc-helm",
                "namespace": "free5gc",
                "revision": 1
            }
        }
