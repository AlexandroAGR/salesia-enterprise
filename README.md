# SalesIA Enterprise

Sistema web empresarial de gestión de ventas y analítica estadística.

Frontend **React + TypeScript (Vite)** · Backend **Python / FastAPI** · Base de datos **PostgreSQL**.

> 📄 **Documentación de avance por fases:** [`docs/Documentacion_Avance_Fases_01-07.md`](docs/Documentacion_Avance_Fases_01-07.md)
> (estado del plan de 16 fases, decisiones de arquitectura, referencia de API, guía de arranque y roadmap)

## Estado actual

| Fase | Estado |
|---|---|
| 01–04 · Análisis, arquitectura, UX/UI y modelo de datos | ✅ Completadas |
| 05 · Backend/API | 🟡 Auth + CRUD de clientes/productos/categorías |
| 06 · Frontend React | 🟡 Router, login, cliente API, páginas CRUD |
| 07 · Clientes y productos | ✅ Completada |
| 08 · Ventas, pagos e inventario | 🔴 En curso |
| 09–16 · Estadística, Analytics, Insights, Reportes, RBAC, pruebas, despliegue, manuales | 🔴 Pendientes |

## Arranque rápido

**Backend** (terminal 1):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Frontend** (terminal 2):

```bash
cd frontend
nvm use 22          # Vite 8 requiere Node ≥ 20
npm install
npm run dev          # http://localhost:5173  (proxy /api → :8000)
```

**Credenciales de desarrollo:** `admin@salesia.com` / `Admin123*`

Documentación interactiva de la API: <http://localhost:8000/docs>

## Base de datos

La fuente de verdad del esquema es SQL plano:

```bash
psql -U postgres -f database/migrations/001_initial_schema.sql   # 24 tablas
psql -U postgres -f database/seeds/001_reference_data.sql        # roles, empresa, categorías, métodos de pago
psql -U postgres -f database/seeds/002_admin_user.sql            # usuario administrador
```

Configuración en `backend/.env` (plantilla en `backend/.env.example`).

## Comandos de calidad

```bash
cd frontend
npm run lint     # ESLint
npm run build    # typecheck (tsc -b) + build de producción
npm test         # pruebas de frontend (Vitest + Testing Library)
```

## Estructura

```
frontend/   frontend React (router, contextos, páginas, cliente API, pruebas)
backend/    API FastAPI (api/ routers · services/ negocio · models/ SQLAlchemy)
database/   migraciones y seeds SQL
docs/       documentación técnica por fases
```
