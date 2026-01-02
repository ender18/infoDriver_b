from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Role, Permission
from app.utils.security import get_password_hash

def create_initial_data():
    db = SessionLocal()
    
    try:
        # Verificar si ya existe superadmin
        existing_admin = db.query(User).filter(User.email == "admin@infodriver.com").first()
        if existing_admin:
            print("Superadmin already exists. Aborting initialization.")
            return
        
        # Crear permisos
        permissions_data = [
            # Users
            {"name": "users:read", "resource": "users", "action": "read", "description": "View users"},
            {"name": "users:create", "resource": "users", "action": "create", "description": "Create users"},
            {"name": "users:update", "resource": "users", "action": "update", "description": "Update users"},
            {"name": "users:delete", "resource": "users", "action": "delete", "description": "Delete users"},
            
            # Roles
            {"name": "roles:read", "resource": "roles", "action": "read", "description": "View roles"},
            {"name": "roles:create", "resource": "roles", "action": "create", "description": "Create roles"},
            {"name": "roles:update", "resource": "roles", "action": "update", "description": "Update roles"},
            {"name": "roles:delete", "resource": "roles", "action": "delete", "description": "Delete roles"},
            {"name": "roles:assign", "resource": "roles", "action": "assign", "description": "Assign roles"},
            
            # Permissions
            {"name": "permissions:read", "resource": "permissions", "action": "read", "description": "View permissions"},
            {"name": "permissions:create", "resource": "permissions", "action": "create", "description": "Create permissions"},
            {"name": "permissions:update", "resource": "permissions", "action": "update", "description": "Update permissions"},
            {"name": "permissions:delete", "resource": "permissions", "action": "delete", "description": "Delete permissions"},
            {"name": "permissions:assign", "resource": "permissions", "action": "assign", "description": "Assign permissions"},
            
            # System
            {"name": "system:settings", "resource": "system", "action": "settings", "description": "System settings"},
            {"name": "system:logs", "resource": "system", "action": "logs", "description": "View logs"},
            {"name": "system:backup", "resource": "system", "action": "backup", "description": "System backup"},
        ]
        
        permissions = []
        for perm_data in permissions_data:
            perm = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
            if not perm:
                perm = Permission(**perm_data)
                db.add(perm)
                db.flush()
            permissions.append(perm)
        
        print(f"Created {len(permissions)} permissions")
        
        # Crear roles
        superadmin_role = db.query(Role).filter(Role.name == "superadmin").first()
        if not superadmin_role:
            superadmin_role = Role(
                name="superadmin",
                description="Full system access"
            )
            db.add(superadmin_role)
            db.flush()
            superadmin_role.permissions = permissions
        
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(
                name="admin",
                description="Administrative access"
            )
            db.add(admin_role)
            db.flush()
            admin_role.permissions = [p for p in permissions if p.name != "system:backup"]
        
        moderator_role = db.query(Role).filter(Role.name == "moderator").first()
        if not moderator_role:
            moderator_role = Role(
                name="moderator",
                description="Content management"
            )
            db.add(moderator_role)
            db.flush()
            moderator_role.permissions = [
                p for p in permissions if p.name in [
                    "users:read", "users:update",
                    "roles:read"
                ]
            ]
        
        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(
                name="user",
                description="Standard user"
            )
            db.add(user_role)
            db.flush()
            user_role.permissions = [p for p in permissions if p.action == "read"]
        
        print("Created 4 roles")
        
        # Crear superadmin
        superadmin_user = User(
            email="admin@infodriver.com",
            username="superadmin",
            password=get_password_hash("SuperAdmin**/"),
            first_name="Super",
            last_name="Admin",
            is_active=True,
            is_verified=True
        )
        db.add(superadmin_user)
        db.flush()
        superadmin_user.roles.append(superadmin_role)
        
        db.commit()
        
        print("\nInitialization completed")
        print("Email: admin@infodriver.com")
        print("Password: SuperAdmin**/")
        print("Change password after first login\n")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_data()