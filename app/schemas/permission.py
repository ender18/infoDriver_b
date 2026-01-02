from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

# Schema para crear permiso
class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    resource: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None

# Schema para actualizar permiso
class PermissionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    resource: Optional[str] = Field(None, min_length=2, max_length=50)
    action: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = None

# Schema de respuesta
class PermissionBase(BaseModel):
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class PermissionResponse(PermissionBase):
    model_config = ConfigDict(from_attributes=True)