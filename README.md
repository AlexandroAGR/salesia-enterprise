# SalesIA Enterprise

Sistema web empresarial de gestión de ventas y analítica estadística.

Frontend **React + TypeScript (Vite)** · Backend **Python / FastAPI** · Base de datos **PostgreSQL**.

> 📄 **Documentación de avance por fases:** [`docs/Documentacion_Avance_Fases_01-07.md`](docs/Documentacion_Avance_Fases_01-07.md)
> (estado del plan de 16 fases, decisiones de arquitectura, referencia de API, guía de arranque y roadmap)

## Estado actual

**Las 16 fases del plan están completadas.** El sistema está desplegado y
verificado en producción (Vercel + Render + Supabase).

| Bloque | Fases | Estado |
|---|---|---|
| Análisis, arquitectura y diseño | 01–03 | ✅ |
| Base de datos PostgreSQL | 04 | ✅ |
| Backend/API y frontend React | 05–06 | ✅ |
| Módulos comerciales (clientes, productos, ventas, pagos, inventario) | 07–08 | ✅ |
| Analítica (estadística, dashboard, insights, reportes) | 09–12 | ✅ |
| Seguridad, auditoría y pruebas | 13–14 | ✅ 115 + 37 pruebas automatizadas |
| Despliegue y documentación | 15–16 | ✅ |

## Documentación

Guías completas del sistema en [`docs/`](docs/), disponibles también en PDF en
[`docs/pdf/`](docs/pdf/):

| Documento | Contenido |
|---|---|
| [Manual de usuario](docs/manual-usuario.md) | Uso de los módulos según cada rol |
| [Manual técnico](docs/manual-tecnico.md) | Arquitectura, configuración y solución de problemas |
| [Documentación API](docs/api.md) | 42 rutas, convenciones y matriz de acceso por rol |
| [Diagrama final](docs/diagrama-final.md) | Arquitectura, modelo entidad-relación y flujo de venta |
| [Diccionario de datos](docs/diccionario-datos.md) | 23 tablas · 191 columnas |
| [Evidencias de pruebas](docs/evidencias-pruebas.md) | Resultados de las suites y verificación |
| [Plan de mantenimiento](docs/plan-mantenimiento.md) | Operación, copias de seguridad y evolución |

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

## Despliegue en Vercel

Dos proyectos en Vercel apuntando a este mismo repositorio:

| Proyecto | Root Directory | Runtime | Variables de entorno |
|---|---|---|---|
| `salesia-api` | `backend/` | Python (FastAPI, detectado automáticamente) | `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS` |
| `salesia-web` | `frontend/` | Vite (estático) | `VITE_API_BASE_URL` (build time) = URL de `salesia-api` |

`CORS_ORIGINS` debe incluir la URL de `salesia-web`; el frontend llama a la API
con la URL absoluta (en desarrollo sigue usando el proxy de Vite).

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
docs/       documentación (Markdown + PDF en docs/pdf/ · diagramas en docs/img/)
scripts/    utilidades (generador de PDF de la documentación)
```

## Comandos de documentación

```bash
python3 -m venv .venv-docs
.venv-docs/bin/pip install -r scripts/requirements-docs.txt
.venv-docs/bin/python scripts/generar_pdf.py docs/   # regenera docs/pdf/*.pdf
```
