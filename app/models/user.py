from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    
    # Información personal
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    telephone = Column(String(20), nullable=True)
    profile_picture = Column(String(500), nullable=True)
    
    # Estado
    is_active = Column(Boolean, default=True, server_default='true', nullable=False)
    is_verified = Column(Boolean, default=False, server_default='false', nullable=False)
    
    # Tokens
    verification_token = Column(String(255), nullable=True)
    reset_password_token = Column(String(255), nullable=True)
    reset_password_expires = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    
    def __repr__(self):
        return f"<User {self.username} ({self.email})>"