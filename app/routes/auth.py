from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

router = APIRouter(prefix="/api", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    # Charger les utilisateurs depuis le JSON
    users_path = "app/data/users.json"
    if not os.path.exists(users_path):
        raise HTTPException(status_code=500, detail="Fichier utilisateurs introuvable")

    with open(users_path, "r") as f:
        data = json.load(f)
    
    # Vérifier les identifiants
    for user in data["users"]:
        if user["username"] == request.username and user["password"] == request.password:
            return {
                "status": "success",
                "role": user["role"],
                "namespace": user["namespace"],
                "username": user["username"]
            }
    
    raise HTTPException(status_code=401, detail="Identifiants invalides")