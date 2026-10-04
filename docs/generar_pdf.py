# -*- coding: utf-8 -*-
"""Convierte la documentación Markdown a PDF con diseño corporativo.

Uso:
    python3 -m venv /tmp/pdfenv
    /tmp/pdfenv/bin/pip install weasyprint markdown
    /tmp/pdfenv/bin/python docs/generar_pdf.py
"""
import re
import sys
from pathlib import Path

import markdown
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "docs" / "Documentacion_Avance_Fases_01-07.md"
PDF_PATH = ROOT / "docs" / "SalesIA_Documentacion_Avance_Fases_01-07.pdf"

NAVY = "#142d52"
BLUE = "#2563eb"
CYAN = "#06b6d4"

CSS = """
@page {
  size: A4;
  margin: 20mm 16mm 22mm 16mm;
  @top-left {
    content: "SalesIA Enterprise · Plan de Desarrollo";
    font-size: 7.5pt;
    color: #8390a5;
    font-family: "DejaVu Sans", sans-serif;
  }
  @top-right {
    content: "Fases 01–07";
    font-size: 7.5pt;
    color: #8390a5;
    font-family: "DejaVu Sans", sans-serif;
  }
  @bottom-left {
    content: "Documentación de Avance · Versión 1.0";
    font-size: 7.5pt;
    color: #8390a5;
    font-family: "DejaVu Sans", sans-serif;
  }
  @bottom-right {
    content: "Página " counter(page) " de " counter(pages);
    font-size: 7.5pt;
    color: #8390a5;
    font-family: "DejaVu Sans", sans-serif;
  }
}

@page :first {
  @top-left { content: none; }
  @top-right { content: none; }
  @bottom-left { content: none; }
  @bottom-right { content: none; }
  margin: 0;
}

* { box-sizing: border-box; }

body {
  font-family: "DejaVu Sans", "Liberation Sans", sans-serif;
  font-size: 9.5pt;
  line-height: 1.55;
  color: #17243b;
}

/* ---------- PORTADA ---------- */
.portada {
  height: 297mm;
  padding: 0;
  background: linear-gradient(150deg, #142d52 0%, #1d3f75 55%, #0e7490 100%);
  color: #ffffff;
  page-break-after: always;
  position: relative;
}

.portada-inner {
  padding: 34mm 22mm 0 22mm;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 26mm;
}

.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.35);
  text-align: center;
  line-height: 34px;
  font-size: 15px;
  font-weight: bold;
}

.brand-name {
  font-size: 14pt;
  font-weight: bold;
  letter-spacing: 3px;
}

.brand-edition {
  display: block;
  font-size: 7.5pt;
  letter-spacing: 4px;
  color: #7de3f7;
}

.portada .kicker {
  font-size: 9pt;
  letter-spacing: 5px;
  color: #7de3f7;
  margin-bottom: 8mm;
}

.portada h1 {
  font-size: 30pt;
  line-height: 1.15;
  margin: 0 0 6mm 0;
  color: #ffffff;
  border: 0;
  padding: 0;
}

.portada .subtitle {
  font-size: 14pt;
  color: rgba(255,255,255,0.85);
  margin: 0 0 4mm 0;
  font-weight: normal;
}

.portada .lead {
  font-size: 10pt;
  color: rgba(255,255,255,0.72);
  max-width: 130mm;
  line-height: 1.7;
  margin-bottom: 16mm;
}

.meta-box {
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 10px;
  padding: 7mm 8mm;
  width: 118mm;
}

.meta-box table {
  width: 100%;
  border: 0;
}

.meta-box td {
  border: 0;
  padding: 1.6mm 0;
  font-size: 9.5pt;
  color: #ffffff;
  background: transparent;
}

.meta-box td:first-child {
  color: #7de3f7;
  font-weight: bold;
  width: 38mm;
}

.meta-box tbody tr:nth-child(even) td {
  background: rgba(255, 255, 255, 0.06);
}

.cover-footer {
  position: absolute;
  bottom: 16mm;
  left: 22mm;
  right: 22mm;
  font-size: 8pt;
  color: rgba(255,255,255,0.6);
  border-top: 1px solid rgba(255,255,255,0.25);
  padding-top: 4mm;
}

/* ---------- ÍNDICE ---------- */
.toc-page { page-break-after: always; }

.toc-page > h2 {
  font-size: 17pt;
  color: NAVY_COLOR;
  border-bottom: 2.5px solid BLUE_COLOR;
  padding-bottom: 3mm;
  margin-bottom: 6mm;
}

ul.toc, .toc ul { list-style: none; padding-left: 0; margin: 0; }

.toc ul ul { list-style: none; padding-left: 7mm; margin: 1mm 0; }

.toc li { margin: 1.4mm 0; }

.toc a {
  text-decoration: none;
  color: #17243b;
}

.toc > ul > li > a { font-weight: bold; color: NAVY_COLOR; }

.toc a::after {
  content: leader('.') " " target-counter(attr(href url), page);
  color: #8390a5;
  font-weight: normal;
}

/* ---------- CONTENIDO ---------- */
h1 {
  font-size: 19pt;
  color: NAVY_COLOR;
  border-bottom: 3px solid BLUE_COLOR;
  padding-bottom: 2.5mm;
  margin: 0 0 5mm 0;
  page-break-after: avoid;
}

h2 {
  font-size: 14.5pt;
  color: NAVY_COLOR;
  margin: 8mm 0 3.5mm 0;
  padding-bottom: 1.6mm;
  border-bottom: 1px solid #e9edf4;
  page-break-after: avoid;
}

h3 {
  font-size: 11.5pt;
  color: #1d3f75;
  margin: 6mm 0 2.5mm 0;
  page-break-after: avoid;
}

h4 { font-size: 10pt; color: #253751; margin: 5mm 0 2mm 0; }

p { margin: 0 0 3mm 0; }

strong { color: #142d52; }

a { color: #2563eb; text-decoration: none; }

ul, ol { margin: 0 0 3mm 0; padding-left: 6mm; }
li { margin-bottom: 1.4mm; }

/* ---------- TABLAS ---------- */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 5mm 0;
  font-size: 8.4pt;
  page-break-inside: auto;
}

thead { display: table-header-group; }

tr { page-break-inside: avoid; }

th {
  background: NAVY_COLOR;
  color: #ffffff;
  font-weight: bold;
  text-align: left;
  padding: 2.2mm 2.6mm;
  border: 1px solid #2a4470;
}

td {
  border: 1px solid #dde4ee;
  padding: 2mm 2.6mm;
  vertical-align: top;
  background: #ffffff;
}

tbody tr:nth-child(even) td { background: #f6f9ff; }

/* ---------- CÓDIGO ---------- */
code {
  font-family: "DejaVu Sans Mono", monospace;
  font-size: 8.2pt;
  background: #eef2f8;
  border: 1px solid #dde4ee;
  border-radius: 3px;
  padding: 0.3mm 1.2mm;
  color: #b91c1c;
}

pre {
  background: #0f1c32;
  color: #e6edf7;
  border-radius: 6px;
  padding: 4mm;
  font-size: 7.9pt;
  line-height: 1.45;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  page-break-inside: avoid;
}

pre code {
  background: transparent;
  border: 0;
  color: #e6edf7;
  padding: 0;
  font-size: 7.9pt;
}

blockquote {
  margin: 3mm 0 4mm 0;
  padding: 3mm 4mm;
  background: #fff8e6;
  border-left: 3px solid #f59e0b;
  border-radius: 0 6px 6px 0;
  font-size: 9pt;
}

blockquote p { margin: 0; }

hr {
  border: 0;
  border-top: 1px solid #e9edf4;
  margin: 6mm 0;
}
"""

TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>SalesIA Enterprise — Documentación de Avance Fases 01-07</title>
<style>
{css}
</style>
</head>
<body>

<section class="portada">
  <div class="portada-inner">
    <div class="brand-row">
      <div class="brand-mark">S</div>
      <div>
        <span class="brand-name">SALESIA</span>
        <span class="brand-edition">ENTERPRISE</span>
      </div>
    </div>

    <p class="kicker">DOCUMENTACIÓN TÉCNICA DE AVANCE</p>
    <h1>Sistema Web Empresarial de Gestión de Ventas y Analítica Estadística</h1>
    <p class="subtitle">Fases 01 – 07 del Plan Integral de Desarrollo</p>
    <p class="lead">
      Documento detallado del trabajo ejecutado: estado del plan de 16 fases,
      decisiones de arquitectura, referencia completa de la API, guía de
      arranque, pruebas realizadas, hallazgos corregidos y roadmap pendiente.
    </p>

    <div class="meta-box">
      <table>
        <tr><td>Documento</td><td>Documentación de Avance por Fases</td></tr>
        <tr><td>Versión</td><td>1.0</td></tr>
        <tr><td>Fecha</td><td>04 de octubre de 2026</td></tr>
        <tr><td>Estado</td><td>Fases 01–07 completadas · Fase 08 en curso</td></tr>
        <tr><td>Stack</td><td>React + TypeScript · Python/FastAPI · PostgreSQL</td></tr>
        <tr><td>Commits</td><td>c8162f0 · 6cc70d6 · 1a3f263 · 0d4286d</td></tr>
      </table>
    </div>
  </div>

  <div class="cover-footer">
    SalesIA Enterprise · Plan Integral de Desarrollo · Versión 1.0
  </div>
</section>

<section class="toc-page">
  <h2>Índice</h2>
  {toc}
</section>

{content}

</body>
</html>
"""


def main() -> int:
    text = MD_PATH.read_text(encoding="utf-8")

    # La primera línea es el título H1 del documento: ya va en la portada.
    text = re.sub(r"^# .*\n", "", text, count=1)

    converter = markdown.Markdown(
        extensions=["tables", "toc", "fenced_code", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
    )
    content_html = converter.convert(text)

    css = CSS.replace("NAVY_COLOR", NAVY).replace("BLUE_COLOR", BLUE)
    html = TEMPLATE.format(css=css, toc=converter.toc, content=content_html)

    HTML(string=html, base_url=str(ROOT)).write_pdf(PDF_PATH)
    print(f"PDF generado: {PDF_PATH} ({PDF_PATH.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
