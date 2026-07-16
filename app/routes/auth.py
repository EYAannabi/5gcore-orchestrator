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
    users_path = "app/data/users.json"
    
    if not os.path.exists(users_path):
        raise HTTPException(status_code=500, detail="Base de données utilisateurs introuvable")

    with open(users_path, "r") as f:
        data = json.load(f)
    
    for user in data["users"]:
        # Vérification stricte des identifiants
        if user["username"] == request.username and user["password"] == request.password:
            return {
                "status": "success",
                "role": user["role"],
                "namespace": user["namespace"],
                "username": user["username"],
                "logo": user.get("logo") # On renvoie le nom du fichier image
            }
    
    raise HTTPException(status_code=401, detail="Identifiants incorrects")