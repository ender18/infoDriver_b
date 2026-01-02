from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# Importar PermissionBase
from app.schemas.permission import PermissionBase

# Schema para crear rol
class RoleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None

# Schema para actualizar rol
class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None

# Schema de respuesta de rol (sin permisos)
class RoleBase(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Schema de respuesta con permisos
class RoleResponse(RoleBase):
    permissions: List['PermissionBase'] = []
    
    model_config = ConfigDict(from_attributes=True)