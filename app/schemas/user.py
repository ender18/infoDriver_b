from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# Importar para las relaciones
from app.schemas.role import RoleBase

# Para crear/registrar usuario
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    telephone: Optional[str] = Field(None, max_length=20)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)

# Para actualizar usuario (propio perfil)
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone: Optional[str] = None
    profile_picture: Optional[str] = None

# Para actualizar usuario como admin (incluye is_active)
class UserAdminUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: Optional[bool] = None

# Respuesta de usuario
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telephone: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

# Respuesta de usuario CON roles
class UserWithRolesResponse(UserResponse):
    roles: List[RoleBase] = []
    permissions: List[str] = []
    
    model_config = ConfigDict(from_attributes=True)

# Schema para asignar rol a usuario
class UserRoleAssign(BaseModel):
    role_id: int