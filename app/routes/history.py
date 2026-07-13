"""
Operation and deployment history routes.
Tracks all deployment lifecycle operations and provides historical data.
"""

import logging
from fastapi import APIRouter, HTTPException
from app.services import history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History & Audit Trail"])


@router.get("/deployments", tags=["History & Audit Trail"])
async def get_all_deployments(limit: int = 50):
    """
    Get list of all deployments with operation history.
    
    Query Parameters:
        limit: Maximum number of records to return
        
    Returns dictionary of deployments with their latest status.
    """
    try:
        operations = history_service.get_all_operations(limit)
        
        # Group by deployment
        deployments = {}
        for op in operations:
            key = f"{op.deployment_name}:{op.namespace}"
            if key not in deployments:
                deployments[key] = {
                    "deployment_name": op.deployment_name,
                    "namespace": op.namespace,
                    "first_deployment": op.timestamp.isoformat(),
                    "last_operation": op.timestamp.isoformat(),
                    "last_operation_type": op.operation_type.value,
                    "last_operation_status": op.status.value,
                    "total_operations": 0
                }
            deployments[key]["total_operations"] += 1
        
        return {
            "total_deployments": len(deployments),
            "deployments": list(deployments.values())
        }
    except Exception as e:
        logger.error(f"Error retrieving deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deployment/{deployment_name}", tags=["History & Audit Trail"])
async def get_deployment_history(
    deployment_name: str,
    namespace: str = "free5gc",
    limit: int = 50
):
    """
    Get complete operation history for a specific deployment.
    Shows all operations performed on the deployment.
    
    Path Parameters:
        deployment_name: Name of the deployment
        
    Query Parameters:
        namespace: Kubernetes namespace
        limit: Maximum number of operations to return
        
    Returns chronological list of operations.
    """
    try:
        operations = history_service.get_deployment_history(deployment_name, namespace, limit)
        
        if not operations:
            return {
                "deployment_name": deployment_name,
                "namespace": namespace,
                "operations": [],
                "total": 0,
                "message": "No operations found for this deployment"
            }
        
        return {
            "deployment_name": deployment_name,
            "namespace": namespace,
            "total": len(operations),
            "operations": [
                {
                    "id": op.id,
                    "operation_type": op.operation_type.value,
                    "timestamp": op.timestamp.isoformat(),
                    "status": op.status.value,
                    "parameters": op.parameters,
                    "result": op.result,
                    "error_message": op.error_message,
                    "duration_seconds": op.duration_seconds,
                    "helm_revision": op.helm_revision
                }
                for op in operations
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving deployment history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operations", tags=["History & Audit Trail"])
async def get_all_operations(limit: int = 100):
    """
    Get all operations across all deployments.
    Useful for audit trail and overall platform activity.
    
    Query Parameters:
        limit: Maximum number of operations to return
        
    Returns chronological list of all operations.
    """
    try:
        operations = history_service.get_all_operations(limit)
        
        return {
            "total_operations": len(operations),
            "operations": [
                {
                    "id": op.id,
                    "operation_type": op.operation_type.value,
                    "deployment_name": op.deployment_name,
                    "namespace": op.namespace,
                    "timestamp": op.timestamp.isoformat(),
                    "status": op.status.value,
                    "duration_seconds": op.duration_seconds,
                    "helm_revision": op.helm_revision
                }
                for op in operations
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving operations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/operation/{operation_id}", tags=["History & Audit Trail"])
async def get_operation_details(operation_id: int):
    """
    Get detailed information about a specific operation.
    
    Path Parameters:
        operation_id: ID of the operation to retrieve
        
    Returns detailed operation information including parameters and results.
    """
    try:
        operations = history_service.get_all_operations(limit=1000)
        
        operation = None
        for op in operations:
            if op.id == operation_id:
                operation = op
                break
        
        if not operation:
            raise HTTPException(status_code=404, detail=f"Operation {operation_id} not found")
        
        return {
            "id": operation.id,
            "operation_type": operation.operation_type.value,
            "deployment_name": operation.deployment_name,
            "namespace": operation.namespace,
            "timestamp": operation.timestamp.isoformat(),
            "status": operation.status.value,
            "parameters": operation.parameters,
            "result": operation.result,
            "error_message": operation.error_message,
            "duration_seconds": operation.duration_seconds,
            "helm_revision": operation.helm_revision,
            "previous_revision": operation.previous_revision
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", tags=["History & Audit Trail"])
async def get_operation_statistics(namespace: str = "free5gc"):
    """
    Get platform-wide operation statistics.
    Shows counts of different operation types and success rates.
    
    Query Parameters:
        namespace: Filter by specific namespace (optional)
        
    Returns statistics about operations.
    """
    try:
        operations = history_service.get_all_operations(limit=5000)
        
        # Filter by namespace if specified
        if namespace:
            operations = [op for op in operations if op.namespace == namespace]
        
        # Calculate statistics
        stats = {
            "total_operations": len(operations),
            "by_type": {},
            "by_status": {},
            "success_rate": 0.0,
            "average_duration_seconds": 0.0
        }
        
        success_count = 0
        total_duration = 0
        duration_count = 0
        
        for op in operations:
            # By type
            op_type = op.operation_type.value
            if op_type not in stats["by_type"]:
                stats["by_type"][op_type] = 0
            stats["by_type"][op_type] += 1
            
            # By status
            status = op.status.value
            if status not in stats["by_status"]:
                stats["by_status"][status] = 0
            stats["by_status"][status] += 1
            
            # Success rate
            if op.status.value == "success":
                success_count += 1
            
            # Average duration
            if op.duration_seconds:
                total_duration += op.duration_seconds
                duration_count += 1
        
        if len(operations) > 0:
            stats["success_rate"] = round(success_count / len(operations) * 100, 2)
        
        if duration_count > 0:
            stats["average_duration_seconds"] = round(total_duration / duration_count, 2)
        
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
