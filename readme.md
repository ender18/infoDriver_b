# Instalar dependencias
pip install -r requirements.txt

# Levantar BD (dentro de carpeta db)
podman compose up -d

# Crear migración inicial
alembic revision --autogenerate -m "initial tables"

# Aplicar migraciones
alembic upgrade head

# Correr app
uvicorn app.main:app --reload

# Ver en: http://localhost:8000/docs
```

---

## `.gitignore`
```
__pycache__/
*.pyc
.env
venv/
.vscode/