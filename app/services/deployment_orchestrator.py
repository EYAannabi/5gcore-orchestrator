"""
Deployment orchestrator — couche métier de haut niveau.

Combine helm_service, kubernetes_service, validation_service et history_service
pour exposer des scénarios complets (déployer, reconfigurer, tester) plutôt que
des actions techniques isolées. C'est cette couche que les routes "opérateur"
doivent appeler — jamais les services bas niveau directement.
"""

import asyncio
import logging
import time
from datetime import datetime

from app.services import helm_service, kubernetes_service, history_service, validation_service
from app.models.history import TestStatus

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 5


async def _wait_until_pods_ready(namespace: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> bool:
    """Attend que tous les pods du namespace soient Running (ou timeout)."""
    elapsed = 0
    while elapsed < timeout:
        pods = kubernetes_service.list_pods(namespace=namespace)
        if pods and all(p["status"] == "Running" for p in pods):
            return True
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
    return False


async def deploy_and_validate(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc",
) -> dict:
    """
    Scénario complet : déployer -> attendre les pods -> valider -> rapport unique.
    C'est la SEULE action que l'opérateur déclenche pour "Deploy Network".
    """
    start = time.time()
    logger.info(f"[orchestrator] Deploy+validate started for {deployment_name}")

    success, stdout, stderr = helm_service.deploy_free5gc()
    if not success:
        return {
            "step": "deploy",
            "status": "failed",
            "message": "Le déploiement Helm a échoué",
            "error": stderr,
        }

    pods_ready = await _wait_until_pods_ready(namespace)
    if not pods_ready:
        return {
            "step": "wait_pods",
            "status": "failed",
            "message": "Les pods n'ont pas atteint l'état Running dans le délai imparti",
        }

    report = await validation_service.run_all_validations(namespace, deployment_name)

    duration = time.time() - start
    result = {
        "step": "complete",
        "status": "ready" if report.overall_status == TestStatus.PASSED else "degraded",
        "message": "Réseau prêt et validé" if report.overall_status == TestStatus.PASSED
                    else "Réseau déployé mais certaines validations ont échoué",
        "duration_seconds": round(duration, 1),
        "validation_summary": report.summary,
        "tests_passed": report.tests_passed,
        "tests_failed": report.tests_failed,
        "tests_total": report.tests_total,
    }
    logger.info(f"[orchestrator] Deploy+validate finished: {result['status']}")
    return result


async def reconfigure_with_safety(
    network_function: str,
    replicas: int,
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc",
) -> dict:
    """
    Scénario complet : scale une NF -> valider -> si échec, rollback automatique.
    C'est la SEULE action que l'opérateur déclenche pour "Modifier la configuration".
    """
    start = time.time()
    nf_deployment_name = f"{deployment_name}-{network_function}"
    logger.info(f"[orchestrator] Reconfigure {network_function} -> {replicas} replicas")

    # Revision avant changement, pour pouvoir y revenir si besoin
    history, _ = helm_service.get_release_history(deployment_name, namespace)
    previous_revision = history[0].get("revision") if history else None

    success, message = kubernetes_service.scale_deployment(
        deployment_name=nf_deployment_name,
        replicas=replicas,
        namespace=namespace,
    )
    if not success:
        return {
            "step": "scale",
            "status": "failed",
            "message": "La modification a échoué avant même d'être appliquée",
            "error": message,
        }

    pods_ready = await _wait_until_pods_ready(namespace)
    report = await validation_service.run_all_validations(namespace, deployment_name)

    if not pods_ready or report.overall_status != TestStatus.PASSED:
        logger.warning("[orchestrator] Validation failed post-reconfigure, rolling back")
        rb_success, rb_out, rb_err = helm_service.rollback_release(
            deployment_name=deployment_name,
            namespace=namespace,
            revision=previous_revision,
        )
        duration = time.time() - start
        return {
            "step": "rollback",
            "status": "reverted",
            "message": "La modification a échoué la validation — configuration précédente restaurée automatiquement",
            "rollback_success": rb_success,
            "duration_seconds": round(duration, 1),
            "validation_summary": report.summary,
        }

    duration = time.time() - start
    return {
        "step": "complete",
        "status": "applied",
        "message": f"{network_function.upper()} mis à jour à {replicas} replicas, validation réussie",
        "duration_seconds": round(duration, 1),
        "validation_summary": report.summary,
    }


async def test_network(
    deployment_name: str = "free5gc-helm",
    namespace: str = "free5gc",
) -> dict:
    """
    Scénario complet : lance les 5 vérifications internes et renvoie UN seul
    verdict clair. C'est la SEULE action que l'opérateur déclenche pour
    "Tester mon réseau" — il ne voit jamais la liste des 5 tests séparés
    sauf s'il clique sur "Détails".
    """
    report = await validation_service.run_all_validations(namespace, deployment_name)

    return {
        "status": "functional" if report.overall_status == TestStatus.PASSED else "issues_detected",
        "message": "Le réseau fonctionne correctement (enregistrement + connectivité OK)"
                    if report.overall_status == TestStatus.PASSED
                    else "Certaines fonctionnalités du réseau ne répondent pas",
        "summary": report.summary,
        "details": [
            {
                "name": t.test_name,
                "passed": t.status == TestStatus.PASSED,
                "error": t.error_message,
                "data": t.details,
            }
            for t in report.tests
        ],
    }