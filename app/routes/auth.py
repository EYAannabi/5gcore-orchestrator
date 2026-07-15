from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

router = APIRouter(tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    # Chemin vers ton fichier JSON
    users_path = "app/data/users.json"
    
    if not os.path.exists(users_path):
        # Créer un fichier par défaut si inexistant pour éviter l'erreur 500
        os.makedirs(os.path.dirname(users_path), exist_ok=True)
        default_users = {"users": [
            {"username": "orange", "password": "orange123", "role": "operator", "namespace": "orange-5g"},
            {"username": "ooredoo", "password": "ooredoo123", "role": "operator", "namespace": "ooredoo-5g"},
            {"username": "huawei", "password": "admin123", "role": "admin", "namespace": "all"}
        ]}
        with open(users_path, "w") as f:
            json.dump(default_users, f)

    with open(users_path, "r") as f:
        data = json.load(f)
    
    # Vérification
    for user in data["users"]:
        if user["username"] == request.username and user["password"] == request.password:
            return {
                "status": "success",
                "role": user["role"],
                "namespace": user["namespace"],
                "username": user["username"]
            }
    
    raise HTTPException(status_code=401, detail="Identifiants incorrects")