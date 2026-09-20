from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.auth import (
    DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_USERNAME,
    create_access_token,
    get_current_admin_user,
    hash_password,
    verify_password,
)
from backend.app.core.dependencies import get_db
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=4, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ProfileUpdateRequest(BaseModel):
    current_password: str = Field(..., min_length=4, max_length=128)
    username: str | None = Field(default=None, min_length=3, max_length=100)
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    new_password: str | None = Field(default=None, min_length=4, max_length=128)


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not user.is_active or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администратора",
        )

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "is_admin": user.is_admin,
        },
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_admin_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
    }


@router.post("/logout")
def logout():
    return {"message": "Вы успешно вышли из системы"}


@router.put("/profile")
def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно.")

    if data.username and data.username != current_user.username:
        duplicate = db.query(User).filter(
            User.username == data.username,
            User.id != current_user.id,
        ).first()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Такой логин уже используется.")
        current_user.username = data.username

    if data.full_name:
        current_user.full_name = data.full_name
    if data.new_password:
        current_user.password_hash = hash_password(data.new_password)

    db.commit()
    db.refresh(current_user)
    return {
        "message": "Профиль успешно обновлён.",
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "is_admin": current_user.is_admin,
        },
        "access_token": create_access_token(current_user),
        "token_type": "bearer",
    }
