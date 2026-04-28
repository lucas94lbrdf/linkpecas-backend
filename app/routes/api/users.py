# ==========================================================
# app/routes/api/users.py
# ==========================================================

from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
def me():
    return {
        "id": "uuid",
        "name": "User Name",
        "email": "user@email.com"
    }


@router.get("/dashboard")
def dashboard():
    return {
        "ads": 12,
        "clicks": 340,
        "plan": "pro"
    }