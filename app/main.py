from fastapi import FastAPI
from app.routers import users, auth, permissions, roles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # URL de tu frontend Vue
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)

# Incluir routers
app.include_router(users.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(permissions.router, prefix="/api")
app.include_router(roles.router, prefix="/api")


@app.get("/")
def root():
    return {"message": "API running"}


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend OK"}