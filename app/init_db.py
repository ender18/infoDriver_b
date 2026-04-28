from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Role, Permission
from app.utils.security import get_password_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_permission(db: Session, data: dict) -> Permission:
    perm = db.query(Permission).filter(Permission.name == data["name"]).first()
    if not perm:
        perm = Permission(**data)
        db.add(perm)
        db.flush()
        print(f"  [+] Permission: {data['name']}")
    return perm


def _get_or_create_role(db: Session, name: str, description: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        role = Role(name=name, description=description)
        db.add(role)
        db.flush()
        print(f"  [+] Role: {name}")
    return role


def _assign_permissions_to_role(role: Role, perms: list[Permission]):
    """Agrega permisos al rol solo si no los tiene ya."""
    existing_names = {p.name for p in role.permissions}
    added = 0
    for perm in perms:
        if perm.name not in existing_names:
            role.permissions.append(perm)
            added += 1
    if added:
        print(f"  [~] Role '{role.name}': +{added} new permissions")


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

PERMISSIONS_DATA = [
    # Users
    {"name": "users:read",   "resource": "users",   "action": "read",   "description": "View users"},
    {"name": "users:create", "resource": "users",   "action": "create", "description": "Create users"},
    {"name": "users:update", "resource": "users",   "action": "update", "description": "Update users"},
    {"name": "users:delete", "resource": "users",   "action": "delete", "description": "Delete users"},

    # Roles
    {"name": "roles:read",   "resource": "roles",   "action": "read",   "description": "View roles"},
    {"name": "roles:create", "resource": "roles",   "action": "create", "description": "Create roles"},
    {"name": "roles:update", "resource": "roles",   "action": "update", "description": "Update roles"},
    {"name": "roles:delete", "resource": "roles",   "action": "delete", "description": "Delete roles"},
    {"name": "roles:assign", "resource": "roles",   "action": "assign", "description": "Assign roles"},

    # Permissions
    {"name": "permissions:read",   "resource": "permissions", "action": "read",   "description": "View permissions"},
    {"name": "permissions:create", "resource": "permissions", "action": "create", "description": "Create permissions"},
    {"name": "permissions:update", "resource": "permissions", "action": "update", "description": "Update permissions"},
    {"name": "permissions:delete", "resource": "permissions", "action": "delete", "description": "Delete permissions"},
    {"name": "permissions:assign", "resource": "permissions", "action": "assign", "description": "Assign permissions"},

    # Companies
    {"name": "companies:read",   "resource": "companies", "action": "read",   "description": "View companies"},
    {"name": "companies:create", "resource": "companies", "action": "create", "description": "Create companies"},
    {"name": "companies:update", "resource": "companies", "action": "update", "description": "Update companies"},
    {"name": "companies:delete", "resource": "companies", "action": "delete", "description": "Delete companies"},

    # Companies
    {"name": "companies:read",   "resource": "companies", "action": "read",   "description": "View companies"},
    {"name": "companies:create", "resource": "companies", "action": "create", "description": "Create companies"},
    {"name": "companies:update", "resource": "companies", "action": "update", "description": "Update companies"},
    {"name": "companies:delete", "resource": "companies", "action": "delete", "description": "Delete companies"},

    # Tools
    {"name": "tools:run", "resource": "tools", "action": "run", "description": "Run validation tools"},

    # System
    {"name": "system:settings", "resource": "system", "action": "settings", "description": "System settings"},
    {"name": "system:logs",     "resource": "system", "action": "logs",     "description": "View logs"},
    {"name": "system:backup",   "resource": "system", "action": "backup",   "description": "System backup"},
]


def create_initial_data():
    db = SessionLocal()

    try:
        print("\n=== InfoDriver — DB Seed (idempotente) ===\n")

        # ---- Permisos -------------------------------------------------------
        print("[1/4] Permisos")
        all_perms = [_get_or_create_permission(db, d) for d in PERMISSIONS_DATA]
        perm_by_name = {p.name: p for p in all_perms}

        # ---- Roles ----------------------------------------------------------
        print("\n[2/4] Roles")

        superadmin_role = _get_or_create_role(db, "superadmin", "Full system access")
        _assign_permissions_to_role(superadmin_role, all_perms)

        admin_role = _get_or_create_role(db, "admin", "Administrative access")
        admin_perms = [p for p in all_perms if p.name != "system:backup"]
        _assign_permissions_to_role(admin_role, admin_perms)

        moderator_role = _get_or_create_role(db, "moderator", "Content management")
        moderator_perms = [perm_by_name[n] for n in [
            "users:read", "users:update",
            "roles:read",
            "companies:read",
            "tools:run",
        ] if n in perm_by_name]
        _assign_permissions_to_role(moderator_role, moderator_perms)

        user_role = _get_or_create_role(db, "user", "Standard user")
        user_perms = [p for p in all_perms if p.action == "read"]
        _assign_permissions_to_role(user_role, user_perms)

        # ---- Superadmin user ------------------------------------------------
        print("\n[3/4] Usuario superadmin")
        superadmin_user = db.query(User).filter(User.email == "admin@infodriver.com").first()
        if not superadmin_user:
            superadmin_user = User(
                email="admin@infodriver.com",
                username="superadmin",
                password=get_password_hash("SuperAdmin**/"),
                first_name="Super",
                last_name="Admin",
                is_active=True,
                is_verified=True,
            )
            db.add(superadmin_user)
            db.flush()
            superadmin_user.roles.append(superadmin_role)
            print("  [+] User: admin@infodriver.com")
        else:
            print("  [=] User admin@infodriver.com ya existe, sin cambios")

        # ---- Commit ---------------------------------------------------------
        print("\n[4/4] Guardando cambios...")
        db.commit()

        print("\n=== Seed completado ===")
        print("Email:    admin@infodriver.com")
        print("Password: SuperAdmin**/")
        print("Cambia la contraseña después del primer login.\n")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_initial_data()
