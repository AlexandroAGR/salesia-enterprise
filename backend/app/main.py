
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.api.auth import router as auth_router


app = FastAPI(
    title=settings.app_name,
    description=(
        "API empresarial para gestión de clientes, productos, "
        "ventas, inventario y análisis estadístico."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/", tags=["Sistema"])
def root():
    return {
        "application": settings.app_name,
        "message": "API funcionando correctamente",
        "version": "1.0.0",
        "status": "online",
    }


@app.get("/health", tags=["Sistema"])
def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
        "database": "not_checked",
    }


@app.get("/health/database", tags=["Sistema"])
def database_health_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS database_user,
                    version() AS postgres_version
                """
            )
        ).mappings().one()

        version_text = result["postgres_version"]

        return {
            "status": "connected",
            "database": result["database_name"],
            "database_user": result["database_user"],
            "postgres_version": version_text,
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No se pudo conectar con PostgreSQL. "
                "Revisa la configuración del backend."
            ),
        ) from None
        
        
