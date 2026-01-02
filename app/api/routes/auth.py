from fastapi import APIRouter

from app.api.dependencies import require_db
from app.models.schemas import UserLogin, UserOut, UserRegister
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister):
    require_db()
    return auth.register_user(payload)


@router.post("/login", response_model=UserOut)
def login(payload: UserLogin):
    require_db()
    return auth.login_user(payload)
