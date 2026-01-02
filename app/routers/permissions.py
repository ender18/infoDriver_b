from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import List

from app.database import get_db
from app.models import Permission
from app.schemas import PermissionCreate, PermissionUpdate, PermissionResponse
from app.utils.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/permissions", tags=["permissions"])

# ==================== CRUD DE PERMISOS ====================

@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear un nuevo permiso (requiere autenticación)
    """
    # Verificar si el permiso ya existe
    existing = db.query(Permission).filter(Permission.name == permission.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission name already exists"
        )
    
    # Crear permiso
    new_permission = Permission(
        name=permission.name,
        resource=permission.resource,
        action=permission.action,
        description=permission.description
    )
    
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)
    
    return new_permission

@router.get("/", response_model=List[PermissionResponse])
def list_permissions(
    skip: int = 0,
    limit: int = 100,
    resource: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Listar todos los permisos con paginación y filtro opcional por recurso
    """
    query = db.query(Permission)
    
    # Filtrar por recurso si se proporciona
    if resource:
        query = query.filter(Permission.resource == resource)
    
    permissions = query.offset(skip).limit(limit).all()
    return permissions

@router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener un permiso por ID
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    return permission

@router.patch("/{permission_id}", response_model=PermissionResponse)
def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar un permiso
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Verificar nombre duplicado si se está cambiando
    if permission_update.name and permission_update.name != permission.name:
        existing = db.query(Permission).filter(Permission.name == permission_update.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission name already exists"
            )
    
    # Actualizar campos
    update_data = permission_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)
    
    permission.updated_at = func.now()
    db.commit()
    db.refresh(permission)
    
    return permission

@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar un permiso permanentemente
    """
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Hard delete (los permisos se pueden eliminar permanentemente)
    db.delete(permission)
    db.commit()
    
    return None