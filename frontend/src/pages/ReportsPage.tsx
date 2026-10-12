import { useCallback, useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  ListChecks,
  Loader2,
  Printer,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import Modal from "../components/Modal";
import { api, ApiError } from "../lib/api";
import type {
  Page,
  Report,
  ReportRow,
  ReportScope,
  ReportSummary,
  ReportTypeInfo,
} from "../types";
import { formatDate, money } from "../utils/format";

const PAGE_SIZE = 20;

const PERIOD_OPTIONS = [
  { value: "7", label: "Últimos 7 días" },
  { value: "30", label: "Últimos 30 días" },
  { value: "90", label: "Últimos 90 días" },
  { value: "all", label: "Histórico completo" },
];

const STATUS_META: Record<string, { label: string; cls: string }> = {
  draft: { label: "Borrador", cls: "status-pendiente" },
  pending: { label: "Pendiente", cls: "status-pendiente" },
  completed: { label: "Completada", cls: "status-completada" },
  cancelled: { label: "Cancelada", cls: "status-cancelada" },
  refunded: { label: "Reembolsada", cls: "status-cancelada" },
};

const STAT_LABELS: Record<string, string> = {
  count: "Registros",
  mean: "Media",
  median: "Mediana",
  min: "Mínimo",
  max: "Máximo",
  stddev: "Desviación",
};

const round2 = (value: number) => Math.round(value * 100) / 100;

function csvEscape(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",;\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** CSV del reporte: sus filas si las tiene, o pares clave/valor si no. */
function buildCsv(report: Report): string {
  const rows = report.content.rows;
  if (rows && rows.length > 0) {
    const headers = Object.keys(rows[0]);
    return [
      headers.join(","),
      ...rows.map((row) =>
        headers
          .map((header) =>
            csvEscape((row as Record<string, unknown>)[header]),
          )
          .join(","),
      ),
    ].join("\n");
  }

  const source: Record<string, unknown> = {
    ...(report.content.kpis ?? {}),
    ...(report.content.summary ?? {}),
    ...(report.content.statistics ?? {}),
    ...(report.content.totals ?? {}),
  };
  return [
    "campo,valor",
    ...Object.entries(source).map(([key, value]) => `${key},${csvEscape(value)}`),
  ].join("\n");
}

function exportCsv(report: Report) {
  const blob = new Blob(["\uFEFF" + buildCsv(report)], {
    type: "text/csv;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const slug =
    report.title
      .toLowerCase()
      .replace(/[^\wáéíóúñ -]/g, "")
      .trim()
      .replace(/\s+/g, "-") || "reporte";
  link.href = url;
  link.download = `${slug}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span className="evidence-chip">
      {label}: <strong>{value}</strong>
    </span>
  );
}

function ScopeLine({ scope }: { scope: ReportScope }) {
  const parts: string[] = [];
  if (scope.date_from && scope.date_to) {
    parts.push(
      `Del ${formatDate(scope.date_from)} al ${formatDate(scope.date_to)}`,
    );
  } else if (scope.date_from) {
    parts.push(`Desde ${formatDate(scope.date_from)}`);
  } else {
    parts.push("Histórico completo");
  }
  if (scope.seller_id) parts.push(`Vendedor #${scope.seller_id}`);
  if (scope.category_id) parts.push(`Categoría #${scope.category_id}`);
  return <p className="form-field form-field-full">{parts.join(" · ")}</p>;
}

function StatusBadge({ status }: { status?: string }) {
  const meta = status
    ? (STATUS_META[status] ?? { label: status, cls: "status-pendiente" })
    : { label: "—", cls: "status-pendiente" };
  return (
    <span className={`status ${meta.cls}`}>
      <i />
      {meta.label}
    </span>
  );
}

function KpiChips({
  metrics,
}: {
  metrics: {
    sales_count?: number;
    revenue?: number;
    avg_ticket?: number;
    customers_count?: number;
    items_sold?: number;
  };
}) {
  return (
    <div className="evidence-list">
      {metrics.sales_count !== undefined && (
        <Chip label="Ventas" value={String(metrics.sales_count)} />
      )}
      {metrics.revenue !== undefined && (
        <Chip label="Ingresos" value={money(metrics.revenue)} />
      )}
      {metrics.avg_ticket !== undefined && (
        <Chip label="Ticket promedio" value={money(metrics.avg_ticket)} />
      )}
      {metrics.customers_count !== undefined && (
        <Chip label="Clientes" value={String(metrics.customers_count)} />
      )}
      {metrics.items_sold !== undefined && (
        <Chip label="Unidades" value={String(metrics.items_sold)} />
      )}
    </div>
  );
}

function TableShell({
  headers,
  children,
}: {
  headers: string[];
  children: React.ReactNode;
}) {
  return (
    <div className="table-scroll">
      <table className="transactions-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function VentasTable({ rows }: { rows: ReportRow[] }) {
  return (
    <TableShell
      headers={[
        "FECHA",
        "NÚMERO",
        "CLIENTE",
        "VENDEDOR",
        "ESTADO",
        "SUBTOTAL",
        "DESCUENTO",
        "IMPUESTO",
        "TOTAL",
      ]}
    >
      {rows.map((row) => (
        <tr key={row.sale_number}>
          <td className="date-cell">{formatDate(row.sold_at)}</td>
          <td>{row.sale_number}</td>
          <td>{row.customer}</td>
          <td>{row.seller}</td>
          <td>
            <StatusBadge status={row.status} />
          </td>
          <td className="amount-cell">{money(row.subtotal ?? 0)}</td>
          <td className="amount-cell">{money(row.discount_amount ?? 0)}</td>
          <td className="amount-cell">{money(row.tax_amount ?? 0)}</td>
          <td className="amount-cell">{money(row.total_amount ?? 0)}</td>
        </tr>
      ))}
    </TableShell>
  );
}

function RankingTable({
  rows,
  kind,
}: {
  rows: ReportRow[];
  kind: "productos" | "clientes" | "vendedores";
}) {
  if (kind === "productos") {
    return (
      <TableShell
        headers={["PRODUCTO", "INGRESOS", "VENTAS", "UNIDADES", "PARTICIPACIÓN"]}
      >
        {rows.map((row) => (
          <tr key={row.product}>
            <td>{row.product}</td>
            <td className="amount-cell">{money(row.revenue ?? 0)}</td>
            <td>{row.sales_count}</td>
            <td>{row.quantity ?? 0}</td>
            <td className="amount-cell">{row.share_pct ?? 0}%</td>
          </tr>
        ))}
      </TableShell>
    );
  }

  if (kind === "clientes") {
    return (
      <TableShell
        headers={[
          "CLIENTE",
          "VENTAS",
          "INGRESOS",
          "TICKET MEDIO",
          "ÚLTIMA COMPRA",
        ]}
      >
        {rows.map((row) => (
          <tr key={row.customer}>
            <td>{row.customer}</td>
            <td>{row.sales_count}</td>
            <td className="amount-cell">{money(row.revenue ?? 0)}</td>
            <td className="amount-cell">{money(row.avg_ticket ?? 0)}</td>
            <td className="date-cell">{formatDate(row.last_purchase)}</td>
          </tr>
        ))}
      </TableShell>
    );
  }

  return (
    <TableShell
      headers={["VENDEDOR", "VENTAS", "INGRESOS", "TICKET MEDIO", "PARTICIPACIÓN"]}
    >
      {rows.map((row) => (
        <tr key={row.seller}>
          <td>{row.seller}</td>
          <td>{row.sales_count}</td>
          <td className="amount-cell">{money(row.revenue ?? 0)}</td>
          <td className="amount-cell">{money(row.avg_ticket ?? 0)}</td>
          <td className="amount-cell">{row.share_pct ?? 0}%</td>
        </tr>
      ))}
    </TableShell>
  );
}

function ReportBody({ report }: { report: Report }) {
  const content = report.content;
  const rows = content.rows ?? [];

  if (report.report_type === "ventas") {
    return (
      <div className="form-grid">
        <ScopeLine scope={content.scope} />
        {content.summary && (
          <div className="form-field form-field-full">
            <KpiChips metrics={content.summary} />
          </div>
        )}
        <div className="form-field form-field-full">
          {rows.length > 0 ? (
            <VentasTable rows={rows} />
          ) : (
            <p>No hay ventas dentro del ámbito del reporte.</p>
          )}
        </div>
      </div>
    );
  }

  if (report.report_type === "estadistico") {
    const stats = content.statistics ?? {};
    const previous = content.previous_period;
    return (
      <div className="form-grid">
        <ScopeLine scope={content.scope} />
        {content.kpis && (
          <div className="form-field form-field-full">
            <KpiChips metrics={content.kpis} />
          </div>
        )}
        <div className="form-field form-field-full">
          <span>Estadística descriptiva de los importes</span>
          <TableShell headers={["DATO", "VALOR"]}>
            {Object.entries(stats).map(([key, value]) => (
              <tr key={key}>
                <td>{STAT_LABELS[key] ?? key}</td>
                <td className="amount-cell">
                  {value === null || value === undefined
                    ? "—"
                    : key === "count"
                      ? String(value)
                      : money(value)}
                </td>
              </tr>
            ))}
          </TableShell>
        </div>
        {previous && (
          <p className="form-field form-field-full">
            Periodo anterior: {money(previous.revenue)} ·{" "}
            {previous.sales_count} venta{previous.sales_count === 1 ? "" : "s"}
            {previous.revenue_change_pct !== null && (
              <>
                {" "}
                · {previous.revenue_change_pct >= 0 ? "+" : ""}
                {round2(previous.revenue_change_pct)}%
              </>
            )}
            .
          </p>
        )}
        <div className="form-field form-field-full">
          <span>Interpretación</span>
          <ul className="report-interpretation">
            {(content.interpretation ?? []).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  const totals = content.totals ?? {};
  const chips: { label: string; value: string }[] = [];
  if (report.report_type === "productos") {
    chips.push(
      { label: "Ingresos", value: money(totals.revenue ?? 0) },
      { label: "Productos", value: String(totals.products_count ?? 0) },
      { label: "Unidades", value: String(totals.units ?? 0) },
    );
  } else if (report.report_type === "clientes") {
    chips.push(
      { label: "Clientes", value: String(totals.customers_count ?? 0) },
      { label: "Ingresos", value: money(totals.revenue ?? 0) },
      { label: "Ventas", value: String(totals.sales_count ?? 0) },
    );
  } else {
    chips.push(
      { label: "Vendedores", value: String(totals.sellers_count ?? 0) },
      { label: "Ingresos", value: money(totals.revenue ?? 0) },
      { label: "Ventas", value: String(totals.sales_count ?? 0) },
    );
  }

  return (
    <div className="form-grid">
      <ScopeLine scope={content.scope} />
      <div className="form-field form-field-full">
        <div className="evidence-list">
          {chips.map((chip) => (
            <Chip key={chip.label} label={chip.label} value={chip.value} />
          ))}
        </div>
      </div>
      <div className="form-field form-field-full">
        {rows.length > 0 ? (
          <RankingTable
            rows={rows}
            kind={
              report.report_type as "productos" | "clientes" | "vendedores"
            }
          />
        ) : (
          <p>No hay datos dentro del ámbito del reporte.</p>
        )}
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Page<ReportSummary> | null>(null);
  const [types, setTypes] = useState<ReportTypeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [reportType, setReportType] = useState("ventas");
  const [period, setPeriod] = useState("7");
  const [generating, setGenerating] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<Report | null>(null);

  const loadTypes = useCallback(async () => {
    try {
      const result = await api.get<ReportTypeInfo[]>("/reports/types");
      setTypes(result);
    } catch {
      setTypes([]);
    }
  }, []);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<ReportSummary>>("/reports", {
        query: {
          report_type: typeFilter || undefined,
          page,
          page_size: PAGE_SIZE,
        },
      });
      setReports(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar los reportes.",
      );
    } finally {
      setLoading(false);
    }
  }, [typeFilter, page]);

  useEffect(() => {
    // Mismo patrón que AnalyticsPage/InsightsPage: diferir la carga
    // fuera del cuerpo síncrono del efecto (react-hooks/set-state-in-effect).
    const timer = window.setTimeout(() => void loadTypes(), 0);
    return () => window.clearTimeout(timer);
  }, [loadTypes]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadReports(), 0);
    return () => window.clearTimeout(timer);
  }, [loadReports]);

  const handleGenerate = async () => {
    setGenerating(true);
    setActionError(null);
    setNotice(null);

    try {
      const result = await api.post<Report>("/reports/generate", {
        report_type: reportType,
        period,
      });
      setNotice(`Reporte «${result.title}» generado correctamente.`);
      setDetail(result);

      if (page !== 1) {
        setPage(1);
      } else {
        await loadReports();
      }
    } catch (caught) {
      setActionError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo generar el reporte.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const openReport = async (summary: ReportSummary) => {
    setActionError(null);
    try {
      const full = await api.get<Report>(`/reports/${summary.id}`);
      setDetail(full);
    } catch (caught) {
      setActionError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo cargar el reporte.",
      );
    }
  };

  const totalPages = reports
    ? Math.max(1, Math.ceil(reports.total / reports.page_size))
    : 1;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            COMERCIAL Y ESTADÍSTICO · FASE 12
          </div>
          <h1>Reportes</h1>
          <p>
            Cinco reportes comerciales y estadísticos con instantánea
            histórica, exportación a CSV y vista imprimible.
          </p>
        </div>
        <div className="heading-actions">
          <select
            className="form-input"
            value={reportType}
            onChange={(event) => setReportType(event.target.value)}
            aria-label="Tipo de reporte a generar"
          >
            {types.map((type) => (
              <option key={type.code} value={type.code}>
                {type.name}
              </option>
            ))}
            {types.length === 0 && (
              <option value="ventas">Reporte de ventas</option>
            )}
          </select>
          <select
            className="form-input period-select"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            aria-label="Período del reporte"
          >
            {PERIOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            className="button-primary"
            onClick={() => void handleGenerate()}
            disabled={generating}
          >
            {generating ? (
              <Loader2 size={17} className="spin" />
            ) : (
              <Sparkles size={17} />
            )}
            {generating ? "Generando..." : "Generar reporte"}
          </button>
          <button
            className="button-secondary"
            onClick={() => void loadReports()}
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
        </div>
      </section>

      {actionError && (
        <div className="form-alert" role="alert">
          {actionError}
        </div>
      )}

      {notice && (
        <div className="form-alert form-alert-block" role="status">
          {notice}
        </div>
      )}

      <section className="panel data-panel">
        <div className="panel-header data-toolbar">
          <div>
            <h3>Historial de reportes</h3>
            <p>
              {reports
                ? `${reports.total} ${
                    reports.total === 1
                      ? "reporte guardado"
                      : "reportes guardados"
                  }`
                : "Cargando..."}
            </p>
          </div>
          <div className="toolbar-controls">
            <select
              className="form-input"
              value={typeFilter}
              onChange={(event) => {
                setTypeFilter(event.target.value);
                setPage(1);
              }}
              aria-label="Filtrar por tipo de reporte"
            >
              <option value="">Todos los tipos</option>
              {types.map((type) => (
                <option key={type.code} value={type.code}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="table-scroll">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>TIPO</th>
                <th>TÍTULO</th>
                <th>USUARIO</th>
                <th>FECHA</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading && !reports && (
                <tr>
                  <td colSpan={5} className="table-state">
                    <Loader2 size={19} className="spin" /> Cargando
                    reportes...
                  </td>
                </tr>
              )}

              {!loading && error && !reports && (
                <tr>
                  <td colSpan={5} className="table-state table-state-error">
                    {error}
                  </td>
                </tr>
              )}

              {!loading && !error && reports && reports.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="table-state">
                    <ListChecks size={19} /> Aún no hay reportes: genera uno
                    con el botón «Generar reporte».
                  </td>
                </tr>
              )}

              {reports?.items.map((report) => (
                <tr key={report.id}>
                  <td>
                    <span className="insight-link">
                      {report.report_type_label}
                    </span>
                  </td>
                  <td>{report.title}</td>
                  <td>{report.created_by_name ?? "—"}</td>
                  <td className="date-cell">{formatDate(report.created_at)}</td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="text-button"
                        onClick={() => void openReport(report)}
                      >
                        Ver reporte
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table-footer">
          <span />
          <div className="pagination">
            <button
              className="icon-button"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
              aria-label="Página anterior"
            >
              <ChevronLeft size={17} />
            </button>
            <span>
              Página {page} de {totalPages}
            </span>
            <button
              className="icon-button"
              disabled={page >= totalPages}
              onClick={() => setPage((value) => value + 1)}
              aria-label="Página siguiente"
            >
              <ChevronRight size={17} />
            </button>
          </div>
        </div>
      </section>

      {detail && (
        <Modal
          title={detail.title}
          onClose={() => setDetail(null)}
          footer={
            <>
              <button
                className="button-secondary no-print"
                onClick={() => exportCsv(detail)}
              >
                <Download size={16} />
                <span>Exportar CSV</span>
              </button>
              <button
                className="button-secondary no-print"
                onClick={() => window.print()}
              >
                <Printer size={16} />
                <span>Imprimir</span>
              </button>
              <button
                className="button-primary no-print"
                onClick={() => setDetail(null)}
              >
                Cerrar
              </button>
            </>
          }
        >
          <div className="report-meta">
            <span className="insight-link">{detail.report_type_label}</span>
            <span>Generado por {detail.created_by_name ?? "sistema"}</span>
            <span>el {formatDate(detail.created_at)}</span>
          </div>
          <ReportBody report={detail} />
        </Modal>
      )}
    </>
  );
}
