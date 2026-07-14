"""
History service for tracking deployment operations and validation results.
Manages SQLite database for persistent operation and test record storage.
"""

import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.history import (
    OperationHistory, OperationStatus, OperationType,
    ValidationReport, ValidationTestResult, DeploymentRevision
)

logger = logging.getLogger(__name__)

# Database path
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "orchestrator.db"


def init_database():
    """Initialize SQLite database with required tables"""
    conn = None
    DB_DIR.mkdir(exist_ok=True)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Operation history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                deployment_name TEXT NOT NULL,
                namespace TEXT NOT NULL DEFAULT 'free5gc',
                timestamp DATETIME NOT NULL,
                status TEXT NOT NULL,
                parameters TEXT NOT NULL,
                result TEXT,
                error_message TEXT,
                duration_seconds REAL,
                helm_revision INTEGER,
                previous_revision INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Validation reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_name TEXT NOT NULL,
                namespace TEXT NOT NULL DEFAULT 'free5gc',
                timestamp DATETIME NOT NULL,
                total_duration_seconds REAL,
                tests_passed INTEGER DEFAULT 0,
                tests_failed INTEGER DEFAULT 0,
                tests_skipped INTEGER DEFAULT 0,
                tests_total INTEGER DEFAULT 0,
                overall_status TEXT NOT NULL,
                summary TEXT,
                tests_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Validation test results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                test_name TEXT NOT NULL,
                test_type TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                duration_seconds REAL,
                details_json TEXT,
                error_message TEXT,
                checked_pods_json TEXT,
                expected_count INTEGER,
                actual_count INTEGER,
                FOREIGN KEY(report_id) REFERENCES validation_reports(id)
            )
        """)
        
        # Helm revisions cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS helm_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_name TEXT NOT NULL,
                namespace TEXT NOT NULL DEFAULT 'free5gc',
                revision INTEGER NOT NULL,
                app_version TEXT,
                status TEXT,
                updated DATETIME,
                description TEXT,
                cached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(deployment_name, namespace, revision)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_deployment ON operation_history(deployment_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operations_timestamp ON operation_history(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_deployment ON validation_reports(deployment_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON validation_reports(timestamp DESC)")
        
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False
    finally:
        if conn:
            conn.close()


def _ensure_database() -> bool:
    """Create the SQLite database lazily before the first history operation."""
    if DB_PATH.exists():
        return True
    return init_database()


def log_operation(operation: OperationHistory) -> Optional[int]:
    """
    Record a deployment operation in the database.
    
    Args:
        operation: OperationHistory object to record
        
    Returns:
        Database ID of inserted record, or None on error
    """
    if not _ensure_database():
        return None

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO operation_history 
            (operation_type, deployment_name, namespace, timestamp, status, 
             parameters, result, error_message, duration_seconds, 
             helm_revision, previous_revision)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            operation.operation_type.value,
            operation.deployment_name,
            operation.namespace,
            operation.timestamp.isoformat(),
            operation.status.value,
            json.dumps(operation.parameters),
            operation.result,
            operation.error_message,
            operation.duration_seconds,
            operation.helm_revision,
            operation.previous_revision
        ))
        
        operation_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Logged {operation.operation_type.value} operation (ID: {operation_id})")
        return operation_id
    except Exception as e:
        logger.error(f"Error logging operation: {e}")
        return None
    finally:
        if conn:
            conn.close()


def log_validation_report(report: ValidationReport) -> Optional[int]:
    """
    Record a validation report in the database.
    
    Args:
        report: ValidationReport object to record
        
    Returns:
        Database ID of inserted report, or None on error
    """
    if not _ensure_database():
        return None

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert report
        cursor.execute("""
            INSERT INTO validation_reports 
            (deployment_name, namespace, timestamp, total_duration_seconds, 
             tests_passed, tests_failed, tests_skipped, tests_total, 
             overall_status, summary, tests_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report.deployment_name,
            report.namespace,
            report.timestamp.isoformat(),
            report.total_duration_seconds,
            report.tests_passed,
            report.tests_failed,
            report.tests_skipped,
            report.tests_total,
            report.overall_status.value,
            report.summary,
            json.dumps([t.model_dump(mode="json") for t in report.tests])
        ))
        
        report_id = cursor.lastrowid
        conn.commit()
        logger.info(f"Logged validation report (ID: {report_id})")
        return report_id
    except Exception as e:
        logger.error(f"Error logging validation report: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_deployment_history(deployment_name: str, namespace: str = "free5gc", limit: int = 50) -> List[OperationHistory]:
    """
    Get all operations for a specific deployment.
    
    Args:
        deployment_name: Name of deployment to query
        namespace: Kubernetes namespace
        limit: Maximum number of records to return
        
    Returns:
        List of OperationHistory objects
    """
    if not _ensure_database():
        return []

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM operation_history 
            WHERE deployment_name = ? AND namespace = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (deployment_name, namespace, limit))
        
        rows = cursor.fetchall()
        operations = []
        
        for row in rows:
            op = OperationHistory(
                id=row['id'],
                operation_type=OperationType(row['operation_type']),
                deployment_name=row['deployment_name'],
                namespace=row['namespace'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                status=OperationStatus(row['status']),
                parameters=json.loads(row['parameters']),
                result=row['result'],
                error_message=row['error_message'],
                duration_seconds=row['duration_seconds'],
                helm_revision=row['helm_revision'],
                previous_revision=row['previous_revision']
            )
            operations.append(op)
        
        return operations
    except Exception as e:
        logger.error(f"Error retrieving deployment history: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_all_operations(limit: int = 100) -> List[OperationHistory]:
    """Get all recorded operations across all deployments."""
    if not _ensure_database():
        return []

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM operation_history 
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        operations = []
        
        for row in rows:
            op = OperationHistory(
                id=row['id'],
                operation_type=OperationType(row['operation_type']),
                deployment_name=row['deployment_name'],
                namespace=row['namespace'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                status=OperationStatus(row['status']),
                parameters=json.loads(row['parameters']),
                result=row['result'],
                error_message=row['error_message'],
                duration_seconds=row['duration_seconds'],
                helm_revision=row['helm_revision'],
                previous_revision=row['previous_revision']
            )
            operations.append(op)
        
        return operations
    except Exception as e:
        logger.error(f"Error retrieving operations: {e}")
        return []
    finally:
        if conn:
            conn.close()


def get_latest_validation_report(deployment_name: str, namespace: str = "free5gc") -> Optional[ValidationReport]:
    """Get the most recent validation report for a deployment."""
    if not _ensure_database():
        return None

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM validation_reports 
            WHERE deployment_name = ? AND namespace = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (deployment_name, namespace))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        tests = json.loads(row['tests_json'])
        test_results = [ValidationTestResult(**test) for test in tests]
        
        report = ValidationReport(
            id=row['id'],
            deployment_name=row['deployment_name'],
            namespace=row['namespace'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            total_duration_seconds=row['total_duration_seconds'],
            tests=test_results,
            tests_passed=row['tests_passed'],
            tests_failed=row['tests_failed'],
            tests_skipped=row['tests_skipped'],
            tests_total=row['tests_total'],
            overall_status=row['overall_status'],
            summary=row['summary']
        )
        return report
    except Exception as e:
        logger.error(f"Error retrieving validation report: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_validation_history(deployment_name: str, namespace: str = "free5gc", limit: int = 20) -> List[ValidationReport]:
    """Get validation history for a deployment."""
    if not _ensure_database():
        return []

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM validation_reports 
            WHERE deployment_name = ? AND namespace = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (deployment_name, namespace, limit))
        
        rows = cursor.fetchall()
        reports = []
        
        for row in rows:
            tests = json.loads(row['tests_json'])
            test_results = [ValidationTestResult(**test) for test in tests]
            
            report = ValidationReport(
                id=row['id'],
                deployment_name=row['deployment_name'],
                namespace=row['namespace'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                total_duration_seconds=row['total_duration_seconds'],
                tests=test_results,
                tests_passed=row['tests_passed'],
                tests_failed=row['tests_failed'],
                tests_skipped=row['tests_skipped'],
                tests_total=row['tests_total'],
                overall_status=row['overall_status'],
                summary=row['summary']
            )
            reports.append(report)
        
        return reports
    except Exception as e:
        logger.error(f"Error retrieving validation history: {e}")
        return []
    finally:
        if conn:
            conn.close()


