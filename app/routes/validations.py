"""
Validation and testing routes.
Exposes validation workflows and generates test reports.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.services import validation_service, history_service
from app.models.history import TestStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tests", tags=["Validation & Testing"])


@router.post("/validate-pods", tags=["Validation & Testing"])
async def run_pod_validation(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
):
    """
    Validate that all Kubernetes pods in the namespace are in Running state.
    
    Returns test result with pass/fail status and detailed information.
    """
    try:
        logger.info(f"Running pod validation for {deployment_name}")
        result = await validation_service.validate_pods_running(namespace)
        return {
            "test": "Pod Health Check",
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "details": result.details,
            "error": result.error_message
        }
    except Exception as e:
        logger.error(f"Error running pod validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-amf", tags=["Validation & Testing"])
async def run_amf_validation(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
):
    """
    Validate AMF registration status.
    Checks that AMF has registered devices and is responding correctly.
    
    Returns test result with registration status.
    """
    try:
        logger.info(f"Running AMF validation for {deployment_name}")
        result = await validation_service.validate_amf_registration(namespace, deployment_name)
        return {
            "test": "AMF Registration Check",
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "details": result.details,
            "error": result.error_message
        }
    except Exception as e:
        logger.error(f"Error running AMF validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-ue", tags=["Validation & Testing"])
async def run_ue_validation(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
):
    """
    Validate UE registration via UERANSIM.
    Checks that UERANSIM UE has registered with the network.
    
    Returns test result with UE registration status.
    """
    try:
        logger.info(f"Running UE validation for {deployment_name}")
        result = await validation_service.validate_ue_registration(namespace, deployment_name)
        return {
            "test": "UE Registration Check",
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "details": result.details,
            "error": result.error_message
        }
    except Exception as e:
        logger.error(f"Error running UE validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-pdu", tags=["Validation & Testing"])
async def run_pdu_validation(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
):
    """
    Validate PDU Session establishment.
    Checks that PDU sessions have been successfully created between UE and network.
    
    Returns test result with PDU session status.
    """
    try:
        logger.info(f"Running PDU session validation for {deployment_name}")
        result = await validation_service.validate_pdu_session(namespace, deployment_name)
        return {
            "test": "PDU Session Check",
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "details": result.details,
            "error": result.error_message
        }
    except Exception as e:
        logger.error(f"Error running PDU validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-connectivity", tags=["Validation & Testing"])
async def run_connectivity_validation(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc",
    test_host: str = "8.8.8.8"
):
    """
    Validate internet connectivity through UERANSIM tunnel.
    Checks that uesimtun0 interface is accessible and connectivity works.
    
    Query Parameters:
        test_host: IP address to ping for connectivity test (default: 8.8.8.8)
        
    Returns test result with connectivity status.
    """
    try:
        logger.info(f"Running connectivity validation for {deployment_name}")
        result = await validation_service.validate_connectivity(namespace, deployment_name, test_host)
        return {
            "test": "Connectivity Check",
            "status": result.status.value,
            "duration_seconds": result.duration_seconds,
            "details": result.details,
            "error": result.error_message
        }
    except Exception as e:
        logger.error(f"Error running connectivity validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-all", tags=["Validation & Testing"])
async def run_all_validations(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc"
):
    """
    Run complete validation suite (all 5 tests) for a deployment.
    
    Runs in parallel:
    1. Pod Health Check
    2. AMF Registration Check
    3. UE Registration Check
    4. PDU Session Check
    5. Connectivity Check
    
    Returns comprehensive validation report with all results.
    """
    try:
        logger.info(f"Running complete validation suite for {deployment_name}")
        report = await validation_service.run_all_validations(namespace, deployment_name)
        
        return {
            "deployment_name": report.deployment_name,
            "namespace": report.namespace,
            "timestamp": report.timestamp.isoformat(),
            "total_duration_seconds": report.total_duration_seconds,
            "tests_passed": report.tests_passed,
            "tests_failed": report.tests_failed,
            "tests_skipped": report.tests_skipped,
            "tests_total": report.tests_total,
            "overall_status": report.overall_status.value,
            "summary": report.summary,
            "tests": [
                {
                    "test_name": t.test_name,
                    "test_type": t.test_type.value,
                    "status": t.status.value,
                    "duration_seconds": t.duration_seconds,
                    "details": t.details,
                    "error": t.error_message
                }
                for t in report.tests
            ]
        }
    except Exception as e:
        logger.error(f"Error running validation suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{deployment_name}", tags=["Validation & Testing"])
async def get_latest_validation_report(
    deployment_name: str,
    namespace: str = "free5gc"
):
    """
    Get the most recent validation report for a deployment.
    
    Path Parameters:
        deployment_name: Name of the deployment
        
    Query Parameters:
        namespace: Kubernetes namespace
        
    Returns latest validation report if available.
    """
    try:
        report = history_service.get_latest_validation_report(deployment_name, namespace)
        
        if not report:
            raise HTTPException(status_code=404, detail="No validation report found for this deployment")
        
        return {
            "deployment_name": report.deployment_name,
            "namespace": report.namespace,
            "timestamp": report.timestamp.isoformat(),
            "total_duration_seconds": report.total_duration_seconds,
            "tests_passed": report.tests_passed,
            "tests_failed": report.tests_failed,
            "tests_skipped": report.tests_skipped,
            "tests_total": report.tests_total,
            "overall_status": report.overall_status.value,
            "summary": report.summary,
            "tests": [
                {
                    "test_name": t.test_name,
                    "test_type": t.test_type.value,
                    "status": t.status.value,
                    "duration_seconds": t.duration_seconds,
                    "details": t.details,
                    "error": t.error_message
                }
                for t in report.tests
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving validation report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{deployment_name}", tags=["Validation & Testing"])
async def get_validation_history(
    deployment_name: str,
    namespace: str = "free5gc",
    limit: int = 20
):
    """
    Get validation history (all reports) for a deployment.
    
    Path Parameters:
        deployment_name: Name of the deployment
        
    Query Parameters:
        namespace: Kubernetes namespace
        limit: Maximum number of reports to return
        
    Returns list of validation reports.
    """
    try:
        reports = history_service.get_validation_history(deployment_name, namespace, limit)
        
        return {
            "deployment_name": deployment_name,
            "namespace": namespace,
            "total_reports": len(reports),
            "reports": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "overall_status": r.overall_status.value,
                    "tests_passed": r.tests_passed,
                    "tests_failed": r.tests_failed,
                    "tests_skipped": r.tests_skipped,
                    "summary": r.summary
                }
                for r in reports
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving validation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))
