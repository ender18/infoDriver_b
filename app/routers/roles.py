from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List

from app.database import get_db
from app.models import Role, Permission, role_permissions
from app.schemas import RoleCreate, RoleUpdate, RoleResponse
from app.utils.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/roles", tags=["roles"])

# ==================== CRUD DE ROLES ====================

@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear un nuevo rol (requiere autenticación)
    """
    # Verificar si el rol ya existe
    existing = db.query(Role).filter(Role.name == role.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    # Crear rol
    new_role = Role(
        name=role.name,
        description=role.description
    )
    
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return new_role

@router.get("/", response_model=List[RoleResponse])
def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Listar todos los roles con paginación
    """
    roles = db.query(Role).offset(skip).limit(limit).all()
    return roles

@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener un rol por ID
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role

@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar un rol
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Verificar nombre duplicado si se está cambiando
    if role_update.name and role_update.name != role.name:
        existing = db.query(Role).filter(Role.name == role_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists"
            )
    
    # Actualizar campos
    update_data = role_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    
    role.updated_at = func.now()
    db.commit()
    db.refresh(role)
    
    return role

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar un rol (soft delete)
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Soft delete
    role.is_active = False
    role.updated_at = func.now()
    db.commit()
    
    return None

# ==================== GESTIÓN DE PERMISOS DEL ROL ====================

@router.post("/{role_id}/permissions/{permission_id}", status_code=status.HTTP_200_OK)
def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Asignar un permiso a un rol
    """
    # Verificar que existan
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Verificar si ya está asignado
    if permission in role.permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already assigned to this role"
        )
    
    # Asignar
    role.permissions.append(permission)
    db.commit()
    
    return {"message": f"Permission '{permission.name}' assigned to role '{role.name}'"}

@router.delete("/{role_id}/permissions/{permission_id}", status_code=status.HTTP_200_OK)
def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Quitar un permiso de un rol
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Verificar que esté asignado
    if permission not in role.permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission not assigned to this role"
        )
    
    # Remover
    role.permissions.remove(permission)
    db.commit()
    
    return {"message": f"Permission '{permission.name}' removed from role '{role.name}'"}

@router.get("/{role_id}/permissions", response_model=List)
def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener todos los permisos de un rol
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return role.permissions