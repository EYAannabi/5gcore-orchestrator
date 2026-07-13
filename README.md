# 5G Core Orchestrator

Plateforme d'automatisation et d'orchestration d'un cœur de réseau 5G Cloud-Native (Free5GC) déployé sur Kubernetes (K3s), pilotée via une API FastAPI.

## Stack
- Kubernetes (K3s)
- Helm
- Free5GC
- UERANSIM
- FastAPI / Python

## Lancer le projet
\`\`\`bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
\`\`\`
