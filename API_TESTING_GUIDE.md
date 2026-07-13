# Quick Reference: NetDevOps Platform API Testing Guide

## 📋 API Endpoints Reference

### Deployment Lifecycle Management

#### 1. Upgrade Deployment
**Endpoint**: `POST /api/core/upgrade`
**Description**: Upgrade Helm release with new parameter values
```bash
curl -X POST http://localhost:8000/api/core/upgrade \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_name": "free5gc-helm",
    "namespace": "free5gc",
    "values": {
      "global.mcc": "310",
      "global.mnc": "410"
    }
  }'
```

#### 2. Scale Network Function
**Endpoint**: `POST /api/core/scale`
**Description**: Scale a specific network function (AMF, SMF, UPF, etc)
**Supported NFs**: amf, smf, upf, ausf, nssf, pcf, udm, udr
```bash
curl -X POST http://localhost:8000/api/core/scale \
  -H "Content-Type: application/json" \
  -d '{
    "network_function": "upf",
    "replicas": 3,
    "deployment_name": "free5gc-helm",
    "namespace": "free5gc"
  }'
```

#### 3. Restart Network Function
**Endpoint**: `POST /api/core/restart`
**Description**: Gracefully restart all pods of a network function
```bash
curl -X POST http://localhost:8000/api/core/restart \
  -H "Content-Type: application/json" \
  -d '{
    "network_function": "amf",
    "deployment_name": "free5gc-helm",
    "namespace": "free5gc"
  }'
```

#### 4. Rollback Deployment
**Endpoint**: `POST /api/core/rollback`
**Description**: Rollback to a previous Helm revision (or 1 step back if no revision specified)
```bash
# Rollback one step
curl -X POST http://localhost:8000/api/core/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_name": "free5gc-helm",
    "namespace": "free5gc"
  }'

# Rollback to specific revision
curl -X POST http://localhost:8000/api/core/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "deployment_name": "free5gc-helm",
    "namespace": "free5gc",
    "revision": 1
  }'
```

#### 5. Get Helm Revisions
**Endpoint**: `GET /api/core/revisions`
**Description**: Get complete Helm release history with revision info
```bash
curl "http://localhost:8000/api/core/revisions?deployment_name=free5gc-helm&namespace=free5gc"
```

#### 6. Get Deployment Parameters
**Endpoint**: `GET /api/core/parameters`
**Description**: Get current Helm values for a deployment
```bash
curl "http://localhost:8000/api/core/parameters?deployment_name=free5gc-helm&namespace=free5gc"
```

---

### Validation & Testing

#### 1. Validate Pod Health
**Endpoint**: `POST /api/tests/validate-pods`
```bash
curl -X POST "http://localhost:8000/api/tests/validate-pods?namespace=free5gc"
```

#### 2. Validate AMF Registration
**Endpoint**: `POST /api/tests/validate-amf`
```bash
curl -X POST "http://localhost:8000/api/tests/validate-amf?deployment_name=free5gc-helm&namespace=free5gc"
```

#### 3. Validate UE Registration
**Endpoint**: `POST /api/tests/validate-ue`
```bash
curl -X POST "http://localhost:8000/api/tests/validate-ue?deployment_name=free5gc-helm&namespace=free5gc"
```

#### 4. Validate PDU Session
**Endpoint**: `POST /api/tests/validate-pdu`
```bash
curl -X POST "http://localhost:8000/api/tests/validate-pdu?deployment_name=free5gc-helm&namespace=free5gc"
```

#### 5. Validate Connectivity
**Endpoint**: `POST /api/tests/validate-connectivity`
```bash
curl -X POST "http://localhost:8000/api/tests/validate-connectivity?deployment_name=free5gc-helm&namespace=free5gc&test_host=8.8.8.8"
```

#### 6. Run All Validations (Concurrent)
**Endpoint**: `POST /api/tests/validate-all`
**Description**: Run all 5 validation tests concurrently, takes ~5-15 seconds
```bash
curl -X POST "http://localhost:8000/api/tests/validate-all?deployment_name=free5gc-helm&namespace=free5gc"
```

#### 7. Get Latest Validation Report
**Endpoint**: `GET /api/tests/report/{deployment_name}`
```bash
curl "http://localhost:8000/api/tests/report/free5gc-helm?namespace=free5gc"
```

#### 8. Get Validation History
**Endpoint**: `GET /api/tests/history/{deployment_name}`
```bash
curl "http://localhost:8000/api/tests/history/free5gc-helm?namespace=free5gc&limit=20"
```

---

### History & Audit Trail

#### 1. List All Deployments
**Endpoint**: `GET /api/history/deployments`
```bash
curl "http://localhost:8000/api/history/deployments?limit=50"
```

#### 2. Get Deployment Operation History
**Endpoint**: `GET /api/history/deployment/{deployment_name}`
```bash
curl "http://localhost:8000/api/history/deployment/free5gc-helm?namespace=free5gc&limit=50"
```

#### 3. Get All Operations (Audit Log)
**Endpoint**: `GET /api/history/operations`
```bash
curl "http://localhost:8000/api/history/operations?limit=100"
```

#### 4. Get Specific Operation Details
**Endpoint**: `GET /api/history/operation/{operation_id}`
```bash
curl "http://localhost:8000/api/history/operation/1"
```

#### 5. Get Platform Statistics
**Endpoint**: `GET /api/history/stats`
**Description**: Get aggregated statistics about all operations
```bash
curl "http://localhost:8000/api/history/stats?namespace=free5gc"
```

---

## 🧪 Complete Test Workflow Example

```bash
#!/bin/bash

API="http://localhost:8000/api"

echo "=== 1. Check current deployment parameters ==="
curl "$API/core/parameters?deployment_name=free5gc-helm" | jq .

echo -e "\n=== 2. Get Helm revision history ==="
curl "$API/core/revisions?deployment_name=free5gc-helm" | jq .

echo -e "\n=== 3. Scale UPF to 3 replicas ==="
curl -X POST "$API/core/scale" \
  -H "Content-Type: application/json" \
  -d '{
    "network_function": "upf",
    "replicas": 3,
    "deployment_name": "free5gc-helm",
    "namespace": "free5gc"
  }' | jq .

echo -e "\n=== 4. Wait a few seconds for scaling... ==="
sleep 10

echo -e "\n=== 5. Run validation suite ==="
curl -X POST "$API/tests/validate-all?deployment_name=free5gc-helm" | jq .

echo -e "\n=== 6. Check operation history ==="
curl "$API/history/deployment/free5gc-helm" | jq .

echo -e "\n=== 7. Get platform statistics ==="
curl "$API/history/stats" | jq .
```

---

## 📊 Expected Response Examples

### Successful Scale Operation
```json
{
  "status": "success",
  "message": "Scaled deployment 'free5gc-helm-upf' to 3 replicas",
  "deployment_name": "free5gc-helm",
  "namespace": "free5gc"
}
```

### Validation Report (All Passed)
```json
{
  "deployment_name": "free5gc-helm",
  "namespace": "free5gc",
  "timestamp": "2026-07-13T10:30:00Z",
  "total_duration_seconds": 12.5,
  "tests_passed": 5,
  "tests_failed": 0,
  "tests_skipped": 0,
  "tests_total": 5,
  "overall_status": "passed",
  "summary": "✓ ALL TESTS PASSED | ✓ Passed: 5 | ✗ Failed: 0 | ⊘ Skipped: 0 | ⚠ Errors: 0",
  "tests": [
    {
      "test_name": "Pod Health Check",
      "test_type": "pod_health",
      "status": "passed",
      "duration_seconds": 2.1,
      "details": {
        "total_pods": 5,
        "running_pods": 5,
        "failed_pods": 0
      }
    },
    ...
  ]
}
```

### Operation History
```json
{
  "deployment_name": "free5gc-helm",
  "namespace": "free5gc",
  "total": 3,
  "operations": [
    {
      "id": 3,
      "operation_type": "scale",
      "timestamp": "2026-07-13T10:25:00Z",
      "status": "success",
      "parameters": {
        "network_function": "upf",
        "target_replicas": 3
      },
      "duration_seconds": 15.2,
      "helm_revision": null
    },
    {
      "id": 2,
      "operation_type": "deploy",
      "timestamp": "2026-07-13T09:30:00Z",
      "status": "success",
      "duration_seconds": 45.5,
      "helm_revision": 1
    },
    ...
  ]
}
```

---

## 🔍 Testing Tips

1. **Use `jq` for pretty-printing JSON**:
   ```bash
   curl -s "http://localhost:8000/api/history/stats" | jq .
   ```

2. **Check all validation tests quickly**:
   ```bash
   time curl -X POST "http://localhost:8000/api/tests/validate-all"
   ```

3. **Monitor operation history in real-time**:
   ```bash
   watch -n 5 'curl -s "http://localhost:8000/api/history/operations" | jq ".operations | length"'
   ```

4. **Get API documentation**:
   - Open browser to: `http://localhost:8000/api/docs`
   - Interactive Swagger UI with "Try it out" buttons

5. **Check database directly** (optional):
   ```bash
   sqlite3 app/data/orchestrator.db "SELECT * FROM operation_history;"
   ```

---

## 📚 Data Retention

- **Operation history**: Retained indefinitely
- **Validation reports**: Retained indefinitely
- **Helm revisions cache**: Updated on each upgrade/rollback
- **Database size**: Grows ~1KB per operation, ~50KB per validation report

---

## 🚀 Next Steps

1. **Test all endpoints** using examples above
2. **Review responses** to understand data structure
3. **Monitor database growth** with validation reports
4. **Plan frontend UI** to expose these operations to operators
5. **Integrate with monitoring** system for metrics

