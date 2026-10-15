# Documentación — SalesIA Enterprise

Documentación oficial del proyecto, correspondiente a la **Fase 16** del Plan
Integral de Desarrollo. Cada documento existe en Markdown (fuente) y en PDF
(generado con `scripts/generar_pdf.py`).

## Documentos

| Documento | Descripción | PDF |
|---|---|---|
| [Manual de usuario](manual-usuario.md) | Guía práctica de uso de los módulos para los 5 roles | [PDF](pdf/manual-usuario.pdf) |
| [Manual técnico](manual-tecnico.md) | Arquitectura, configuración, BD, pruebas y solución de problemas | [PDF](pdf/manual-tecnico.pdf) |
| [Documentación API](api.md) | 42 rutas · 57 operaciones, convenciones y matriz de acceso | [PDF](pdf/api.pdf) |
| [Diagrama final](diagrama-final.md) | Arquitectura, modelo entidad-relación y flujo de venta | [PDF](pdf/diagrama-final.pdf) |
| [Diccionario de datos](diccionario-datos.md) | 23 tablas · 191 columnas, con tipos y relaciones | [PDF](pdf/diccionario-datos.pdf) |
| [Evidencias de pruebas](evidencias-pruebas.md) | Resultados de las suites y de la verificación end-to-end | [PDF](pdf/evidencias-pruebas.pdf) |
| [Plan de mantenimiento](plan-mantenimiento.md) | Operación, cambios, copias de seguridad y evolución | [PDF](pdf/plan-mantenimiento.pdf) |

## Diagramas

Los diagramas viven en [`img/`](img/) en formato **SVG**, generados con
[Graphviz](https://graphviz.org/) a partir de los ficheros `.dot` fuente:

| Archivo | Contenido |
|---|---|
| `img/arquitectura.svg` | Flor de capas: usuario → frontend → backend → cálculo → datos → despliegue |
| `img/er_nucleo.svg` | Modelo entidad-relación del núcleo, comercial y operación |
| `img/er_analitica.svg` | Modelo entidad-relación de la analítica y la inteligencia |
| `img/venta.svg` | Flujo completo de una venta, de punta a punta |

Para regenerarlos (requiere `graphviz`):

```bash
cd /tmp && cp <ruta-al-proyecto>/scripts/dots/*.dot .   # o trabajar directamente en el repo
dot -Tsvg er_nucleo.dot -o docs/img/er_nucleo.svg
```

## Regenerar los PDF

```bash
python3 -m venv .venv-docs
.venv-docs/bin/pip install -r scripts/requirements-docs.txt
.venv-docs/bin/python scripts/generar_pdf.py docs/      # todos los documentos
```

> WeasyPrint necesita las librerías del sistema `pango` y `cairo`
> (Debian/Ubuntu: `sudo apt install libpango-1.0-0 libpangocairo-1.0-0`).

## Mantenimiento de la documentación

La documentación se mantiene **junto al código**:

- Un cambio de API obliga a revisar [`api.md`](api.md).
- Un cambio de esquema obliga a regenerar [`diccionario-datos.md`](diccionario-datos.md)
  (se genera desde `database/migrations/001_initial_schema.sql`).
- Un módulo nuevo obliga a actualizar [manual-usuario.md](manual-usuario.md) y
  [diagrama-final.md](diagrama-final.md).
- Tras cada despliegue se actualizan las cifras de
  [evidencias-pruebas.md](evidencias-pruebas.md).

El detalle de la rutina está en el [plan de mantenimiento](plan-mantenimiento.md).
