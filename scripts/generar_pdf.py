#!/usr/bin/env python3
"""Convierte los documentos Markdown de docs/ en PDF con WeasyPrint.

Genera portada, índice automático numerado, cabecera con el título y pie con
número de página. Los diagramas SVG de docs/img/ se incrustan automáticamente.

Uso:
    python -m venv .venv-docs && .venv-docs/bin/pip install -r scripts/requirements-docs.txt
    .venv-docs/bin/python scripts/generar_pdf.py docs/              # todos
    .venv-docs/bin/python scripts/generar_pdf.py docs/api.md        # uno solo

Los PDF se escriben en docs/pdf/.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import markdown
import weasyprint

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
SALIDA = DOCS / "pdf"

EXTS = ["tables", "fenced_code", "toc", "sane_lists", "attr_list"]

CSS = """
@page {
    size: A4;
    margin: 22mm 17mm 20mm 17mm;
    @top-center {
        content: string(titulo-doc);
        font-family: "DejaVu Sans", sans-serif;
        font-size: 8pt; color: #64748b;
        border-bottom: .4pt solid #e2e8f0; padding-bottom: 3mm; width: 100%;
    }
    @bottom-right {
        content: "Página " counter(page) " de " counter(pages);
        font-family: "DejaVu Sans", sans-serif; font-size: 8pt; color: #64748b;
    }
    @bottom-left {
        content: "SalesIA Enterprise · v1.0";
        font-family: "DejaVu Sans", sans-serif; font-size: 8pt; color: #94a3b8;
    }
}
@page portada { @top-center { content: none } @bottom-right { content: none }
                @bottom-left { content: none } margin: 0 }

html { font-family: "DejaVu Sans", "Noto Sans", sans-serif; font-size: 10pt;
       line-height: 1.55; color: #1e293b; }

/* ---------- portada ---------- */
.portada { page: portada; height: 297mm; padding: 0; position: relative;
           page-break-after: always; }
.portada .cinta { background: linear-gradient(135deg, #0f172a, #1d4ed8);
                  height: 105mm; color: #fff; padding: 28mm 20mm 0 20mm; }
.portada .eyebrow { font-size: 9pt; letter-spacing: 3pt; text-transform: uppercase;
                    color: #93c5fd; margin-bottom: 6mm; }
.portada h1 { font-size: 30pt; margin: 0 0 4mm 0; line-height: 1.1;
              color: #ffffff; border-bottom: none; padding-bottom: 0;
              page-break-before: avoid; string-set: none; }
.portada .sub { font-size: 12pt; color: #cbd5e1; }
.portada .meta { padding: 14mm 20mm; }
.portada .meta table { width: 100%; font-size: 9.5pt; }
.portada .meta td { border: none; padding: 2.6mm 0; border-bottom: .4pt solid #e2e8f0;
                    background: none !important; }
.portada .meta td:first-child { color: #64748b; width: 42mm;
                                text-transform: uppercase; letter-spacing: .6pt;
                                font-size: 8pt; padding-top: 3.2mm; }
.portada .sello { position: absolute; bottom: 20mm; left: 20mm; right: 20mm;
                  font-size: 8.5pt; color: #94a3b8;
                  border-top: .4pt solid #e2e8f0; padding-top: 4mm; }

/* ---------- titulares ---------- */
h1 { font-size: 19pt; color: #0f172a; margin: 0 0 6mm 0;
     string-set: titulo-doc content(); padding-bottom: 3mm;
     border-bottom: 2pt solid #1d4ed8; page-break-before: always;
     page-break-after: avoid; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 13.5pt; color: #1d4ed8; margin: 8mm 0 3mm 0;
     page-break-after: avoid; }
h3 { font-size: 11pt; color: #0f172a; margin: 6mm 0 2mm 0; page-break-after: avoid; }
h4 { font-size: 10pt; color: #334155; margin: 4mm 0 1.5mm 0; page-break-after: avoid; }

p { margin: 0 0 3mm 0; text-align: justify; }
ul, ol { margin: 0 0 3mm 0; padding-left: 6mm; }
li { margin-bottom: 1.4mm; }

/* ---------- tablas ---------- */
table { width: 100%; border-collapse: collapse; margin: 3mm 0 5mm 0;
        font-size: 8.4pt; page-break-inside: auto; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th { background: #1d4ed8; color: #fff; text-align: left; padding: 2mm 2.4mm;
     font-weight: 600; border: .4pt solid #1d4ed8; }
td { padding: 1.9mm 2.4mm; border: .4pt solid #cbd5e1; vertical-align: top; }
tbody tr:nth-child(even) td { background: #f8fafc; }

/* ---------- código ---------- */
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.3pt;
       background: #f1f5f9; padding: .3mm 1.1mm; border-radius: 1mm;
       color: #0f172a; word-break: break-all; }
pre { background: #0f172a; color: #e2e8f0; padding: 3.5mm 4mm; border-radius: 2mm;
      font-family: "DejaVu Sans Mono", monospace; font-size: 7.4pt; line-height: 1.4;
      white-space: pre-wrap; word-break: break-word; margin: 3mm 0 4mm 0;
      page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; font-size: 7.4pt;
           word-break: break-word; }

blockquote { margin: 3mm 0 4mm 0; padding: 3mm 4mm; background: #eff6ff;
             border-left: 2.5pt solid #1d4ed8; border-radius: 0 1.5mm 1.5mm 0; }
blockquote p { margin: 0 0 1.5mm 0; }
blockquote p:last-child { margin: 0; }

hr { border: none; border-top: .4pt solid #e2e8f0; margin: 5mm 0; }
img { display: block; width: 100%; max-width: 100%; height: auto;
      margin: 4mm auto 5mm auto; }
a { color: #1d4ed8; text-decoration: none; word-break: break-all; }
strong { color: #0f172a; }

/* ---------- índice ---------- */
.indice { page-break-after: always; }
.indice h1 { page-break-before: avoid; }
.indice ul { list-style: none; padding-left: 0; }
.indice li { margin-bottom: 1.6mm; font-size: 9.5pt; }
.indice li li { padding-left: 7mm; font-size: 9pt; color: #475569; }
.indice a { color: #1e293b; }
.indice a::after { content: leader('.') target-counter(attr(href), page);
                   color: #94a3b8; }
"""

PORTADA = """
<div class="portada">
  <div class="cinta">
    <div class="eyebrow">SalesIA Enterprise · Fase 16</div>
    <h1>{titulo}</h1>
    <div class="sub">{subtitulo}</div>
  </div>
  <div class="meta">
    <table>
      <tr><td>Documento</td><td>{doc}</td></tr>
      <tr><td>Versión</td><td>1.0</td></tr>
      <tr><td>Fecha</td><td>14 de octubre de 2026</td></tr>
      <tr><td>Plataforma</td><td>React 19 + TypeScript · FastAPI · PostgreSQL 17</td></tr>
      <tr><td>Despliegue</td><td>Render (API) · Vercel (web) · Supabase (BD)</td></tr>
      <tr><td>Estado</td><td>Sistema desplegado y verificado</td></tr>
    </table>
  </div>
  <div class="sello">Plan Integral de Desarrollo · SalesIA Enterprise · Versión 1.0</div>
</div>
"""

META = {
    "manual-tecnico.md": ("Manual técnico", "Arquitectura, configuración, base de datos y operación"),
    "manual-usuario.md": ("Manual de usuario", "Guía de uso de los módulos del sistema"),
    "api.md": ("Documentación API", "Referencia de endpoints, roles y convenciones"),
    "diagrama-final.md": ("Diagrama final", "Arquitectura, modelo entidad-relación y flujos"),
    "diccionario-datos.md": ("Diccionario de datos", "Esquema completo de PostgreSQL: 23 tablas"),
    "evidencias-pruebas.md": ("Evidencias de pruebas", "Resultados de verificación y criterios de aceptación"),
    "plan-mantenimiento.md": ("Plan de mantenimiento", "Operación, cambios, copias de seguridad y evolución"),
}


def md_a_html(texto: str) -> str:
    # python-markdown sólo inserta el índice donde está el marcador [[TOC]].
    if "[[TOC]]" not in texto:
        texto = "[[TOC]]\n\n" + texto
    return markdown.markdown(texto, extensions=EXTS, extension_configs={
        "toc": {
            "toc_depth": "2-3",
            "permalink": False,
            "separator": "-",
            "marker": "[[TOC]]",
        },
    })


def construir_indice(html: str) -> str:
    """Envuelve el toc generado por python-markdown en una sección con estilo."""
    m = re.search(r'<div class="toc">\s*<ul>.*?</ul>\s*</div>', html, re.S)
    if not m:
        m = re.search(r"<ul>\s*<li><a href=\"#.*?</ul>", html, re.S)
    if not m:
        return ""
    return f'<div class="indice"><h1>Índice</h1>{m.group(0)}</div>'


def convertir(archivo: Path) -> Path:
    nombre = archivo.name
    titulo, subtitulo = META.get(nombre, (archivo.stem, "Documentación SalesIA"))
    cuerpo = md_a_html(archivo.read_text(encoding="utf-8"))
    indice = construir_indice(cuerpo)
    html = (
        '<html><head><meta charset="utf-8">'
        f"<style>{CSS}</style>"
        "</head><body>"
        + PORTADA.format(titulo=titulo, subtitulo=subtitulo, doc=nombre)
        + indice
        + cuerpo
        + "</body></html>"
    )
    SALIDA.mkdir(exist_ok=True)
    destino = SALIDA / (archivo.stem + ".pdf")
    # base_url = docs/ para resolver las rutas relativas de las imágenes (img/*.svg)
    weasyprint.HTML(string=html, base_url=str(DOCS)).write_pdf(str(destino))
    return destino


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    entrada = Path(sys.argv[1])
    archivos = sorted(entrada.glob("*.md")) if entrada.is_dir() else [entrada]
    for f in archivos:
        if f.name not in META:
            print(f"  (omitido {f.name}: sin plantilla)")
            continue
        d = convertir(f)
        print(f"  ✓ {d.relative_to(RAIZ)}  ({d.stat().st_size // 1024} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
