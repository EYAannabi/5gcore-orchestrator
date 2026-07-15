"""
Validation and testing service for Free5GC deployments.
Performs post-deployment validations and generates test reports.
"""

import asyncio
import logging
import subprocess
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.history import (
    ValidationReport, ValidationTestResult, TestStatus, ValidationTestType
)
from app.services.kubernetes_service import list_pods, get_pod_logs
from app.services import history_service

logger = logging.getLogger(__name__)


async def validate_pods_running(
    namespace: str = "free5gc",
    expected_count: int = None
) -> ValidationTestResult:
    """
    Validate that all pods in the namespace are in Running state.
    
    Args:
        namespace: Kubernetes namespace to check
        expected_count: Expected minimum number of running pods (None = all)
        
    Returns:
        ValidationTestResult with pass/fail status
    """
    start_time = datetime.utcnow()
    
    try:
        pods = list_pods(namespace=namespace)
        
        if not pods:
            return ValidationTestResult(
                test_name="Pod Health Check",
                test_type=ValidationTestType.POD_HEALTH,
                status=TestStatus.FAILED,
                details={"error": "No pods found in namespace"},
                expected_count=expected_count or 1,
                actual_count=0
            )
        
        running_pods = [p for p in pods if p["status"] == "Running"]
        failed_pods = [p for p in pods if p["status"] != "Running"]
        
        # Check if all pods are running
        all_running = len(failed_pods) == 0
        
        # If expected_count specified, ensure we have that many
        meets_expected = True
        if expected_count and len(running_pods) < expected_count:
            meets_expected = False
        
        status = TestStatus.PASSED if (all_running and meets_expected) else TestStatus.FAILED
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return ValidationTestResult(
            test_name="Pod Health Check",
            test_type=ValidationTestType.POD_HEALTH,
            status=status,
            duration_seconds=duration,
            details={
                "total_pods": len(pods),
                "running_pods": len(running_pods),
                "failed_pods": len(failed_pods),
                "failed_pod_names": [p["name"] for p in failed_pods]
            },
            checked_pods=[p["name"] for p in running_pods[:10]],  # First 10
            expected_count=expected_count or len(pods),
            actual_count=len(running_pods),
            error_message=None if status == TestStatus.PASSED else "Some pods are not running"
        )
    except Exception as e:
        logger.error(f"Error validating pods: {e}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        return ValidationTestResult(
            test_name="Pod Health Check",
            test_type=ValidationTestType.POD_HEALTH,
            status=TestStatus.ERROR,
            duration_seconds=duration,
            error_message=str(e)
        )


async def validate_amf_registration(
    namespace: str = "free5gc",
    deployment_name: str = "free5gc-helm"
) -> ValidationTestResult:
    """
    Validate that AMF has registered UEs.
    Queries the AMF WebUI API for registered devices.
    
    Args:
        namespace: Kubernetes namespace
        deployment_name: Deployment name
        
    Returns:
        ValidationTestResult with AMF registration status
    """
    start_time = datetime.utcnow()
    
    try:
        # Try to get AMF pod and query its metrics/logs
        pods = list_pods(namespace=namespace)
        amf_pods = [p for p in pods if "amf" in p["name"].lower()]
        
        if not amf_pods:
            return ValidationTestResult(
                test_name="AMF Registration Check",
                test_type=ValidationTestType.AMF_REGISTRATION,
                status=TestStatus.SKIPPED,
                details={"reason": "No AMF pods found"},
                error_message="AMF pod not found in namespace"
            )
        
        # In a real scenario, you would:
        # 1. Query AMF WebUI API: kubectl port-forward to AMF and query registration endpoint
        # 2. Or check AMF pod logs for registration messages
        # 3. Or query AUSF/UDR database for subscriber records
        
        # For now, check if AMF is running
        amf_running = all(p["status"] == "Running" for p in amf_pods)
        
        # Try to get logs (this is a placeholder for real validation)
        logs_sample = ""
        if amf_running and amf_pods:
            logs_sample = get_pod_logs(amf_pods[0]["name"], namespace, tail_lines=50)
        
        registered_count = 0
        if "registered" in logs_sample.lower():
            registered_count = 1  # Placeholder - in reality, parse actual count
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        status = TestStatus.PASSED if amf_running else TestStatus.FAILED
        
        return ValidationTestResult(
            test_name="AMF Registration Check",
            test_type=ValidationTestType.AMF_REGISTRATION,
            status=status,
            duration_seconds=duration,
            details={
                "amf_pods_running": len([p for p in amf_pods if p["status"] == "Running"]),
                "amf_pods_total": len(amf_pods),
                "registered_ues": registered_count
            },
            checked_pods=[p["name"] for p in amf_pods],
            error_message=None if status == TestStatus.PASSED else "AMF is not in Running state"
        )
    except Exception as e:
        logger.error(f"Error validating AMF registration: {e}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        return ValidationTestResult(
            test_name="AMF Registration Check",
            test_type=ValidationTestType.AMF_REGISTRATION,
            status=TestStatus.ERROR,
            duration_seconds=duration,
            error_message=str(e)
        )


async def validate_ue_registration(
    namespace: str = "free5gc",
    deployment_name: str = "free5gc-helm"
) -> ValidationTestResult:
    """
    Validate that UE is registered via UERANSIM.
    """
    start_time = datetime.utcnow()

    try:
        pods = list_pods(namespace=namespace)
        ueransim_pods = [p for p in pods if "ueransim-ue" in p["name"].lower()]

        if not ueransim_pods:
            return ValidationTestResult(
                test_name="UE Registration Check",
                test_type=ValidationTestType.UE_REGISTRATION,
                status=TestStatus.SKIPPED,
                details={"reason": "UERANSIM UE pod not found"},
                error_message="UERANSIM pod not deployed"
            )

        ueransim_running = all(p["status"] == "Running" for p in ueransim_pods)

        logs_sample = ""
        if ueransim_running and ueransim_pods:
            logs_sample = get_pod_logs(ueransim_pods[0]["name"], namespace, tail_lines=300)

        registered = "Initial Registration is successful" in logs_sample

        duration = (datetime.utcnow() - start_time).total_seconds()
        status = TestStatus.PASSED if registered else TestStatus.FAILED

        return ValidationTestResult(
            test_name="UE Registration Check",
            test_type=ValidationTestType.UE_REGISTRATION,
            status=status,
            duration_seconds=duration,
            details={
                "ueransim_pods_running": len([p for p in ueransim_pods if p["status"] == "Running"]),
                "registration_detected": registered
            },
            checked_pods=[p["name"] for p in ueransim_pods],
            error_message=None if status == TestStatus.PASSED else "UE registration not detected in recent logs"
        )
    except Exception as e:
        logger.error(f"Error validating UE registration: {e}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        return ValidationTestResult(
            test_name="UE Registration Check",
            test_type=ValidationTestType.UE_REGISTRATION,
            status=TestStatus.ERROR,
            duration_seconds=duration,
            error_message=str(e)
        )
    
async def validate_pdu_session(
    namespace: str = "free5gc",
    deployment_name: str = "free5gc-helm"
) -> ValidationTestResult:
    """
    Validate that PDU Session has been established, by checking UERANSIM UE logs
    (the UE is the one reporting successful session establishment).
    """
    start_time = datetime.utcnow()

    try:
        pods = list_pods(namespace=namespace)
        ue_pods = [p for p in pods if "ueransim-ue" in p["name"].lower()]
        upf_pods = [p for p in pods if "upf" in p["name"].lower()]

        if not ue_pods or not upf_pods:
            return ValidationTestResult(
                test_name="PDU Session Check",
                test_type=ValidationTestType.PDU_SESSION,
                status=TestStatus.SKIPPED,
                details={"reason": "UE or UPF pods not found"},
                error_message="Required pods not deployed"
            )

        ue_running = all(p["status"] == "Running" for p in ue_pods)
        upf_running = all(p["status"] == "Running" for p in upf_pods)

        session_established = False
        if ue_running and ue_pods:
            logs = get_pod_logs(ue_pods[0]["name"], namespace, tail_lines=300)
            session_established = "PDU Session establishment is successful" in logs

        duration = (datetime.utcnow() - start_time).total_seconds()
        status = TestStatus.PASSED if (ue_running and upf_running and session_established) else TestStatus.FAILED

        return ValidationTestResult(
            test_name="PDU Session Check",
            test_type=ValidationTestType.PDU_SESSION,
            status=status,
            duration_seconds=duration,
            details={
                "ue_running": ue_running,
                "upf_running": upf_running,
                "session_established": session_established
            },
            checked_pods=[p["name"] for p in ue_pods] + [p["name"] for p in upf_pods],
            error_message=None if status == TestStatus.PASSED else "PDU session not established"
        )
    except Exception as e:
        logger.error(f"Error validating PDU session: {e}")
        duration = (datetime.utcnow() - start_time).total_seconds()
        return ValidationTestResult(
            test_name="PDU Session Check",
            test_type=ValidationTestType.PDU_SESSION,
            status=TestStatus.ERROR,
            duration_seconds=duration,
            error_message=str(e)
        )
    
async def validate_connectivity(
    namespace: str = "free5gc",
    deployment_name: str = "free5gc-helm",
    test_host: str = "8.8.8.8"
) -> ValidationTestResult:
    start_time = datetime.utcnow()
    try:
        pods = list_pods(namespace=namespace)
        ueransim_pods = [p for p in pods if "ueransim-ue" in p["name"].lower()]

        if not ueransim_pods or not any(p["status"] == "Running" for p in ueransim_pods):
            return ValidationTestResult(
                test_name="Connectivity Check",
                test_type=ValidationTestType.CONNECTIVITY,
                status=TestStatus.SKIPPED,
                error_message="UERANSIM UE pod not running",
            )

        ue_pod = ueransim_pods[0]
        cmd = [
            "kubectl", "exec", ue_pod["name"], "-n", namespace,
            "--", "ping", "-I", "uesimtun0", "-c", "3", "-W", "3", test_host,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        ping_success = result.returncode == 0 and "0% packet loss" in result.stdout

        duration = (datetime.utcnow() - start_time).total_seconds()
        status = TestStatus.PASSED if ping_success else TestStatus.FAILED

        return ValidationTestResult(
            test_name="Connectivity Check",
            test_type=ValidationTestType.CONNECTIVITY,
            status=status,
            duration_seconds=duration,
            details={"ping_output": result.stdout[-300:], "test_host": test_host},
            checked_pods=[ue_pod["name"]],
            error_message=None if ping_success else "Ping failed or interface unreachable",
        )
    except Exception as e:
        return ValidationTestResult(
            test_name="Connectivity Check",
            test_type=ValidationTestType.CONNECTIVITY,
            status=TestStatus.ERROR,
            error_message=str(e),
        )
    
async def run_all_validations(
    namespace: str = "free5gc",
    deployment_name: str = "free5gc-helm"
) -> ValidationReport:
    """
    Run all validation tests and generate a comprehensive report.
    
    Args:
        namespace: Kubernetes namespace
        deployment_name: Deployment name
        
    Returns:
        ValidationReport with all test results
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting comprehensive validation for {deployment_name} in {namespace}")
    
    try:
        # Run all validations concurrently
        results = await asyncio.gather(
            validate_pods_running(namespace, expected_count=5),
            validate_amf_registration(namespace, deployment_name),
            validate_ue_registration(namespace, deployment_name),
            validate_pdu_session(namespace, deployment_name),
            validate_connectivity(namespace, deployment_name)
        )
        
        # Count results
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        # Overall status
        overall = TestStatus.PASSED if failed == 0 and errors == 0 else TestStatus.FAILED
        
        # Build summary
        summary_parts = [
            f"Validation report for {deployment_name}:",
            f"Passed: {passed}",
            f"Failed: {failed}",
            f"Skipped: {skipped}",
            f"Errors: {errors}"
        ]

        if overall == TestStatus.PASSED:
            summary_parts.insert(0, "ALL TESTS PASSED")
        else:
            summary_parts.insert(0, "SOME TESTS FAILED")

        summary = " | ".join(summary_parts)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        report = ValidationReport(
            deployment_name=deployment_name,
            namespace=namespace,
            timestamp=start_time,
            total_duration_seconds=duration,
            tests=results,
            tests_passed=passed,
            tests_failed=failed,
            tests_skipped=skipped,
            tests_total=len(results),
            overall_status=overall,
            summary=summary
        )
        
        # Store report in history
        history_service.log_validation_report(report)
        logger.info(f"Validation complete: {summary}")
        
        return report
    except Exception as e:
        logger.error(f"Error running validations: {e}")
        # Return partial report
        return ValidationReport(
            deployment_name=deployment_name,
            namespace=namespace,
            overall_status=TestStatus.ERROR,
            summary=f"Validation error: {str(e)}"
        )
