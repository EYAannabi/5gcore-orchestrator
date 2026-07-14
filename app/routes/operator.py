"""
Operator-facing routes — high-level actions only.
These are the ONLY routes the operator UI should call.
Technical routes (core/scale, core/upgrade, tests/*) stay internal,
used by the orchestrator, not exposed directly to the operator.
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from app.services import deployment_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operator", tags=["Operator Actions"])


class ReconfigureRequest(BaseModel):
    network_function: str
    replicas: int
    deployment_name: str = "free5gc-helm"
    namespace: str = "free5gc"


@router.post("/deploy")
async def operator_deploy(deployment_name: str = "free5gc-helm", namespace: str = "free5gc"):
    """Deploy the network and validate it in one action."""
    return await deployment_orchestrator.deploy_and_validate(deployment_name, namespace)


@router.post("/reconfigure")
async def operator_reconfigure(request: ReconfigureRequest):
    """Change a network function's scale, with automatic validation + rollback on failure."""
    return await deployment_orchestrator.reconfigure_with_safety(
        network_function=request.network_function,
        replicas=request.replicas,
        deployment_name=request.deployment_name,
        namespace=request.namespace,
    )


@router.post("/test")
async def operator_test(deployment_name: str = "free5gc-helm", namespace: str = "free5gc"):
    """Run a full network health check and return a single verdict."""
    return await deployment_orchestrator.test_network(deployment_name, namespace)
