# Evidencias de pruebas — SalesIA Enterprise

> Registro de las verificaciones ejecutadas sobre el proyecto. Todas las cifras
> provienen de ejecuciones reales; el entorno se indica en cada bloque.

## 1. Suites automatizadas (Fase 14)

### Backend — pytest (115 pruebas · ✅ 115 pasan)

```
$ cd backend && .venv/bin/python -m pytest tests -q
115 passed, 1 warning in 62.89s
```

| Archivo | Pruebas | Cubre |
|---|---:|---|
| `tests/test_unitario_motor.py` | 33 | Motor estadístico: media, mediana, variables aleatorias, probabilidad, Bayes |
| `tests/test_endpoints.py` | 25 | API: contratos de respuesta, códigos de estado, validaciones |
| `tests/test_calculos.py` | 22 | Cálculos de totales, impuestos, descuentos y KPIs |
| `tests/test_datos.py` | 18 | Aislamiento multiempresa y reglas de negocio sobre datos |
| `tests/test_integracion.py` | 14 | Flujos venta → pago → inventario → auditoría |
| `tests/test_aceptacion.py` | 3 | Criterios de aceptación de alto nivel |

Estrategia (plan §17): unitarias, integración, API, datos y aceptación. La BD de
pruebas es un SQLite temporal con *shims* de tipos (`tests/conftest.py`), creada
y vaciada por sesión; nunca toca la BD de desarrollo ni la de producción.

### Frontend — Vitest (6 archivos · 37 pruebas · ✅ 37 pasan)

| Archivo | Contenido |
|---|---|
| `src/App.test.tsx` | Enrutado, protección de rutas y render de layout |
| `src/pages/DashboardPage.test.tsx` | KPIs y estado de carga |
| `src/pages/CustomersPage.test.tsx` | CRUD, búsqueda y filtros con debounce |
| `src/pages/AnalyticsPage.test.tsx` | Gráficos, filtros y series temporales |
| `src/pages/InsightsPage.test.tsx` | Listado y generación de insights |
| `src/pages/ReportsPage.test.tsx` | Generación y exportación de reportes |

### Lint y build

```
$ npm run lint     → sin errores
$ npm run build    → ✓ built (aviso benigno de chunk >500 kB)
```

## 2. Cadena de verificación end-to-end (6 fases)

Ejecutada sobre **PostgreSQL 17.11 (Supabase)** con la BD reseedada a cero
(`backend/seed_demo.py`), backend FastAPI en ejecución. Orden recomendado:
`12 → 11 → 10 → 9 → 8 → 13`.

| Fase | Script | Resultado | Detalle |
|---|---|---|---|
| 12 · Reportes | `verify_fase12.py` | **71 ✅ / 0 ❌** | Generación, tipos, filtros, exportación e histórico |
| 11 · Insights | `verify_fase11.py` | **75 ✅ / 0 ❌** | 7 reglas estadísticas disparen en BD fresca; evidencia numérica |
| 10 · Analytics | `verify_fase10.py` | **76 ✅ / 0 incorrectas** | KPIs con valores exactos (1060.82 · 1490.34 · 902.70 · 587.64) |
| 09 · Estadística | `verify_fase09.py` | **65 ✅ / 0 incorrectas** | Media, mediana, variables aleatorias, Bayes reproducible |
| 08 · Ventas | `verify_fase08.py` | **52 ✅ / 0 fallos** | Venta completa, pagos, inventario y stock |
| 13 · Seguridad | `verify_fase13.py` | **134 ✅ / 0 ❌** | Sesiones, matriz de 5 roles, auditoría, validación, secretos |

> **Nota sobre el check «PostgreSQL conectado» (Fase 8)**: esta es la primera
> ejecución en la que sale en verde, al estar el backend conectado a Supabase
> en lugar de al SQLite temporal.

### Detalle de Fase 13 (seguridad) — 5 bloques

1. **Control de sesiones**: token ausente, corrupto, expirado y firmado con otra
   clave → todos rechazados; JWT con exp ≤ 60 min; logout registrado.
2. **Matriz de roles**: 5 usuarios (Administrador, Gerente, Vendedor, Analista,
   Almacén) × endpoints protegidos → 403 esperados y accesos permitidos.
3. **Auditoría**: toda operación crítica queda registrada en `audit_logs`
   (RF-22), con aislamiento entre empresas.
4. **Validación de entrada**: payloads inválidos → `422`.
5. **Secretos**: `.env` fuera de git, sin valores por defecto.

## 3. Despliegue (Fase 15)

Entorno productivo verificado el 2026-10-15:

| Comprobación | Resultado |
|---|---|
| API en Render — `GET /health` | ✅ `{"status":"healthy"}` |
| API en Render — `GET /health/database` | ✅ `PostgreSQL 17.11` (Supabase) |
| `POST /api/auth/login` contra Render | ✅ 200 |
| Preflight CORS desde el origen de Vercel | ✅ 200 con `access-control-allow-origin` |
| Frontend en Vercel | ✅ sirve la app y las rutas de React Router |

Direcciones: API `https://salesia-enterprise-brqr.onrender.com` ·
Web `https://salesia-enterprise-nine.vercel.app`.

## 4. Criterios de aceptación (plan §20)

| Criterio | Estado | Verificado por |
|---|:--:|---|
| Sesión iniciada y acceso limitado a los módulos del rol | ✅ | Fase 13 · matriz de roles |
| Una venta registra sus detalles y actualiza inventario | ✅ | Fase 08 · `test_integracion.py` |
| Los datos de ventas se consultan desde Analytics | ✅ | Fase 10 |
| El sistema calcula correctamente media y mediana | ✅ | Fase 09 · `test_unitario_motor.py` |
| Permite identificar variables estadísticas | ✅ | Fase 09 |
| Analiza variables aleatorias definidas | ✅ | Fase 09 |
| El módulo de Bayes devuelve resultado reproducible | ✅ | Fase 09 |
| Los resultados aparecen en gráficos y KPIs | ✅ | Fase 10 |
| Los insights muestran el dato que los origina | ✅ | Fase 11 |
| Los análisis quedan almacenados y consultables | ✅ | Fase 09 · `statistical_analyses` |
| Las operaciones críticas quedan en auditoría | ✅ | Fase 13 |
| El sistema supera las pruebas previas al despliegue | ✅ | 115 + 37 automatizadas, 6 fases verificadas |
