from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, UserWithRolesResponse
from app.schemas.auth import PasswordChange
from app.utils.dependencies import get_current_active_user
from app.utils.security import get_password_hash, verify_password

router = APIRouter(prefix="/users", tags=["users"])

# ==================== ENDPOINTS DEL USUARIO ACTUAL ====================

@router.get("/me", response_model=UserWithRolesResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Obtener información del usuario actual (requiere token)
    """
    permissions = set()
    for role in current_user.roles:
        for permission in role.permissions:
            permissions.add(permission.name)
    
    # Convertir a dict y agregar permisos
    user_data = UserWithRolesResponse.model_validate(current_user)
    user_data.permissions = list(permissions)
    
    return user_data

@router.patch("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar información del usuario actual.
    Solo envía los campos que quieres modificar.
    """
    # Convertir a dict solo con campos enviados
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Actualizar cada campo
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    # Actualizar timestamp
    current_user.updated_at = func.now()
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/me/change-password", status_code=status.HTTP_200_OK)
def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cambiar contraseña del usuario actual
    """
    # Verificar contraseña actual
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Actualizar a nueva contraseña
    current_user.password = get_password_hash(password_data.new_password)
    current_user.updated_at = func.now()
    
    db.commit()
    
    return {"message": "Password updated successfully"}

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar cuenta del usuario actual (soft delete)
    """
    # Soft delete (desactivar cuenta)
    current_user.is_active = False
    current_user.updated_at = func.now()
    db.commit()
    
    return None

# ==================== ENDPOINTS ADMINISTRATIVOS ====================

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener información de un usuario por ID
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Listar todos los usuarios con paginación
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar un usuario (solo admin debería poder)
    """
    # No permitir que se elimine a sí mismo
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account from this endpoint. Use /users/me instead"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete
    user.is_active = False
    user.updated_at = func.now()
    db.commit()
    
    return None

# Agregar al final del archivo users.py

# ==================== GESTIÓN DE ROLES DEL USUARIO ====================

@router.post("/{user_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
def assign_role_to_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Asignar un rol a un usuario
    """
    from app.models import Role
    
    # Verificar que existan
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Verificar si ya tiene el rol
    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has this role"
        )
    
    # Asignar
    user.roles.append(role)
    db.commit()
    
    return {"message": f"Role '{role.name}' assigned to user '{user.username}'"}

@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Quitar un rol de un usuario
    """
    from app.models import Role
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Verificar que tenga el rol
    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User doesn't have this role"
        )
    
    # Remover
    user.roles.remove(role)
    db.commit()
    
    return {"message": f"Role '{role.name}' removed from user '{user.username}'"}

@router.get("/{user_id}/roles")
def get_user_roles(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener todos los roles de un usuario
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user.roles
