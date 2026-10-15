# Documentación API — SalesIA Enterprise

> Generada desde el esquema OpenAPI del backend en ejecución (`/openapi.json`).
> **42 rutas · 57 operaciones.** Documentación interactiva en `/docs` (Swagger) y
> `/redoc`.

## Convenciones

| Aspecto | Detalle |
|---|---|
| **Prefijo** | `/api` (salvo las comprobaciones de salud en `/health`) |
| **Autenticación** | `Authorization: Bearer <JWT>` — se obtiene en `POST /api/auth/login` |
| **Formato** | JSON. Importes y cantidades como **cadenas decimales** (`"10.50"`), fechas ISO-8601 UTC |
| **Multiempresa** | Todas las respuestas están limitadas a la empresa del usuario autenticado |
| **Paginación** | Endpoints de lista devuelven `{ items, total, page, page_size }` |
| **Errores** | `400` validación · `401` sin/expirado token · `403` rol no autorizado · `404` recurso o ámbito inexistente · `409` conflicto de unicidad · `500` error interno |

### Códigos de estado habituales

```
200 OK            201 Creado        204 Sin contenido
400 Bad Request   401 Unauthorized  403 Forbidden   404 Not Found
409 Conflict      500 Server Error
```

## Matriz de acceso por rol

El backend vuelve a validar cada petición en `app/core/permissions.py`; el frontend
sólo oculta elementos que terminarían en `403`.

| Módulo | Administrador | Gerente | Vendedor | Analista | Almacén |
|---|:--:|:--:|:--:|:--:|:--:|
| Auditoría | ✔ | ✖ | ✖ | ✖ | ✖ |
| Clientes (lectura/escritura) | ✔/✔ | ✔/✖ | ✔/✔ | ✖/✖ | ✖/✖ |
| Productos (lectura/escritura) | ✔/✔ | ✔/✖ | ✔/✖ | ✖/✖ | ✔/✔ |
| Categorías (lectura) | ✔ | ✔ | ✔ | ✖ | ✔ |
| Inventario (lectura/movimientos) | ✔/✔ | ✔/✖ | ✔/✖ | ✖/✖ | ✔/✔ |
| Métodos de pago | ✔ | ✔ | ✔ | ✖ | ✖ |
| Ventas (lectura/escritura) | ✔/✔ | ✔/✖ | ✔/✔ | ✔/✖ | ✔/✖ |
| Analytics | ✔ | ✔ | ✔ | ✔ | ✔ |
| Insights / Reportes / Datasets / Análisis | ✔ | ✔ | ✖ | ✔ | ✖ |

## Endpoints por módulo

### Autenticación

| Método | Ruta | Acceso |
|---|---|---|
| `POST` | `/api/auth/login` | Cualquier usuario activo |
| `POST` | `/api/auth/logout` | Cualquier usuario activo |
| `GET` | `/api/auth/me` | Cualquier usuario activo |

### Clientes

| Método | Ruta | Acceso |
|---|---|---|
| `GET · POST` | `/api/customers` | Administrador · Gerente · Vendedor |
| `GET · PATCH · DELETE` | `/api/customers/{customer_id}` | Administrador · Gerente · Vendedor |

### Categorías

| Método | Ruta | Acceso |
|---|---|---|
| `GET · POST` | `/api/categories` | Administrador · Gerente · Vendedor · Almacén (lectura) — Administrador (escritura) |
| `GET · PATCH · DELETE` | `/api/categories/{category_id}` | Administrador · Gerente · Vendedor · Almacén (lectura) — Administrador (escritura) |

### Productos

| Método | Ruta | Acceso |
|---|---|---|
| `GET · POST` | `/api/products` | Administrador · Gerente · Vendedor · Almacén (lectura) — Administrador · Almacén (escritura) |
| `GET · PATCH · DELETE` | `/api/products/{product_id}` | Administrador · Gerente · Vendedor · Almacén (lectura) — Administrador · Almacén (escritura) |

### Ventas

| Método | Ruta | Acceso |
|---|---|---|
| `GET · POST` | `/api/sales` | Lectura: todos · Escritura: Administrador · Vendedor |
| `GET` | `/api/sales/{sale_id}` | Lectura: todos · Escritura: Administrador · Vendedor |

### Pagos

| Método | Ruta | Acceso |
|---|---|---|
| `GET · POST` | `/api/payments` | Todos los roles |

### Métodos de pago

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/payment-methods` | Administrador · Gerente · Vendedor |

### Inventario

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/inventory` | Administrador · Gerente · Vendedor · Almacén (lectura) — Administrador · Almacén (movimientos) |
| `GET · POST` | `/api/inventory/movements` | Administrador · Gerente · Vendedor · Almacén (lectura) — Administrador · Almacén (movimientos) |

### Datasets

| Método | Ruta | Acceso |
|---|---|---|
| `GET · POST` | `/api/datasets` | Administrador · Gerente · Analista |
| `GET · DELETE` | `/api/datasets/{dataset_id}` | Administrador · Gerente · Analista |
| `POST · GET` | `/api/datasets/{dataset_id}/observations` | Administrador · Gerente · Analista |
| `POST` | `/api/datasets/{dataset_id}/variables` | Administrador · Gerente · Analista |
| `PATCH` | `/api/datasets/{dataset_id}/variables/{variable_id}` | Administrador · Gerente · Analista |

### Análisis estadísticos

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/analyses` | Administrador · Gerente · Analista |
| `POST` | `/api/analyses/bayes` | Administrador · Gerente · Analista |
| `POST` | `/api/analyses/mean-median` | Administrador · Gerente · Analista |
| `POST` | `/api/analyses/probability` | Administrador · Gerente · Analista |
| `POST` | `/api/analyses/random-variable` | Administrador · Gerente · Analista |
| `GET` | `/api/analyses/{analysis_id}` | Administrador · Gerente · Analista |

### Analytics

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/analytics/breakdown` | Todos los roles |
| `GET` | `/api/analytics/filters` | Todos los roles |
| `GET` | `/api/analytics/frequencies` | Todos los roles |
| `GET` | `/api/analytics/series` | Todos los roles |
| `GET` | `/api/analytics/summary` | Todos los roles |

### Insights

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/insights` | Administrador · Gerente · Analista |
| `POST` | `/api/insights/generate` | Administrador · Gerente · Analista |
| `GET` | `/api/insights/rules` | Administrador · Gerente · Analista |

### Reportes

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/reports` | Administrador · Gerente · Analista |
| `POST` | `/api/reports/generate` | Administrador · Gerente · Analista |
| `GET` | `/api/reports/types` | Administrador · Gerente · Analista |
| `GET` | `/api/reports/{report_id}` | Administrador · Gerente · Analista |

### Auditoría

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/api/audit` | Administrador |

### Sistema

| Método | Ruta | Acceso |
|---|---|---|
| `GET` | `/` | Público (health check) |
| `GET` | `/health` | Público (health check) |
| `GET` | `/health/database` | Público (health check) |
