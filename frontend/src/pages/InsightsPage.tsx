import { useCallback, useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  ListChecks,
  Loader2,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import Modal from "../components/Modal";
import { api, ApiError } from "../lib/api";
import type {
  GenerateInsightsResult,
  Insight,
  InsightRule,
  InsightSeverity,
  Page,
} from "../types";
import { formatDate, money } from "../utils/format";

const PAGE_SIZE = 20;

const SEVERITY_META: Record<
  InsightSeverity,
  { label: string; cls: string }
> = {
  info: { label: "Informativo", cls: "status-pendiente" },
  positive: { label: "Positivo", cls: "status-completada" },
  warning: { label: "Advertencia", cls: "status-cancelada" },
};

const PERIOD_OPTIONS = [
  { value: "7", label: "Últimos 7 días" },
  { value: "30", label: "Últimos 30 días" },
  { value: "90", label: "Últimos 90 días" },
  { value: "all", label: "Histórico completo" },
];

const ANALYSIS_LABELS: Record<string, string> = {
  mean_median: "Media y mediana",
  random_variable: "Variable aleatoria",
  probability: "Probabilidades",
  bayes: "Teorema de Bayes",
};

const EVIDENCE_LABELS: Record<string, string> = {
  date_from: "Desde",
  date_to: "Hasta",
  seller_id: "Vendedor",
  category_id: "Categoría (filtro)",
  revenue: "Ingresos",
  previous_revenue: "Ingresos previos",
  change_pct: "Variación",
  category: "Categoría",
  product: "Producto",
  seller: "Vendedor",
  total_revenue: "Total del periodo",
  share_pct: "Participación",
  groups_count: "Grupos",
  count: "Registros",
  mean: "Media",
  median: "Mediana",
  ratio: "Ratio",
  stddev: "Desviación",
  cv: "Coef. de variación",
  total_amount: "Monto",
  total: "Ventas totales",
  cancelled: "Canceladas",
  refunded: "Reembolsadas",
  rate_pct: "Tasa",
  variable: "Variable",
  relation: "Relación",
  distribution: "Distribución",
  expected_value: "Valor esperado",
  variance: "Varianza",
  std_dev: "Desviación estándar",
  empirical_mean: "Media observada",
  p_a: "P(A)",
  p_b: "P(B)",
  p_a_given_b: "P(A|B)",
  p_b_given_a: "P(B|A)",
  independent: "Independientes",
  difference: "Diferencia",
  probability_a: "P(A)",
  probability_b_given_a: "P(B|A)",
  probability_b: "P(B)",
  posterior_probability: "P(A|B)",
};

const RELATION_LABELS: Record<string, string> = {
  media_mayor_mediana: "Media > Mediana",
  media_menor_mediana: "Media < Mediana",
  media_igual_mediana: "Media = Mediana",
};

const MONEY_KEYS = new Set([
  "revenue",
  "previous_revenue",
  "total_revenue",
  "total_amount",
]);

function evidenceEntries(evidence: Record<string, unknown>) {
  return Object.entries(evidence).filter(
    ([, value]) => value !== null && value !== undefined,
  );
}

function evidenceLabel(key: string): string {
  return EVIDENCE_LABELS[key] ?? key.replace(/_/g, " ");
}

function evidenceValue(key: string, value: unknown): string {
  if (key === "relation") {
    return RELATION_LABELS[String(value)] ?? String(value);
  }
  if (typeof value === "boolean") {
    return value ? "Sí" : "No";
  }
  if (typeof value === "number") {
    if (MONEY_KEYS.has(key)) return money(value);
    if (key.endsWith("_pct")) return `${Math.round(value * 100) / 100}%`;
    if (Number.isInteger(value)) return String(value);
    return String(Math.round(value * 1e6) / 1e6);
  }
  return String(value);
}

function EvidenceChips({
  evidence,
  limit,
}: {
  evidence: Record<string, unknown>;
  limit?: number;
}) {
  const entries = evidenceEntries(evidence);
  const visible = limit ? entries.slice(0, limit) : entries;
  const rest = entries.length - visible.length;

  return (
    <div className="evidence-list">
      {visible.map(([key, value]) => (
        <span className="evidence-chip" key={key}>
          {evidenceLabel(key)}: <strong>{evidenceValue(key, value)}</strong>
        </span>
      ))}
      {rest > 0 && <span className="evidence-chip">+{rest} más</span>}
    </div>
  );
}

function SeverityBadge({ severity }: { severity: InsightSeverity }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.info;
  return (
    <span className={`status ${meta.cls}`}>
      <i />
      {meta.label}
    </span>
  );
}

export default function InsightsPage() {
  const [insights, setInsights] = useState<Page<Insight> | null>(null);
  const [rules, setRules] = useState<InsightRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const [period, setPeriod] = useState("7");
  const [generating, setGenerating] = useState(false);
  const [ruleFilter, setRuleFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<Insight | null>(null);

  const loadRules = useCallback(async () => {
    try {
      const result = await api.get<InsightRule[]>("/insights/rules");
      setRules(result);
    } catch {
      setRules([]);
    }
  }, []);

  const loadInsights = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<Insight>>("/insights", {
        query: {
          rule_code: ruleFilter || undefined,
          severity: severityFilter || undefined,
          page,
          page_size: PAGE_SIZE,
        },
      });
      setInsights(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar las observaciones.",
      );
    } finally {
      setLoading(false);
    }
  }, [ruleFilter, severityFilter, page]);

  useEffect(() => {
    // Mismo patrón que AnalyticsPage: diferir la carga fuera del cuerpo
    // síncrono del efecto (regla react-hooks/set-state-in-effect).
    const timer = window.setTimeout(() => void loadRules(), 0);
    return () => window.clearTimeout(timer);
  }, [loadRules]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadInsights(), 0);
    return () => window.clearTimeout(timer);
  }, [loadInsights]);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenerateError(null);
    setNotice(null);

    try {
      const result = await api.post<GenerateInsightsResult>(
        "/insights/generate",
        { period },
      );
      const created = result.created.length;

      setNotice(
        created > 0
          ? `Se crearon ${
              created === 1
                ? "1 observación nueva"
                : `${created} observaciones nuevas`
            } y se omitieron ${result.skipped} duplicada${
              result.skipped === 1 ? "" : "s"
            }.`
          : `Sin observaciones nuevas: ${result.skipped} resultado${
              result.skipped === 1 ? "" : "s"
            } ya registrado${result.skipped === 1 ? "" : "s"}.`,
      );

      if (page !== 1) {
        setPage(1);
      } else {
        await loadInsights();
      }
    } catch (caught) {
      setGenerateError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron generar los insights.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const totalPages = insights
    ? Math.max(1, Math.ceil(insights.total / insights.page_size))
    : 1;

  const ruleOf = (code: string) =>
    rules.find((rule) => rule.code === code) ?? null;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            REGLAS DETERMINISTAS · FASE 11
          </div>
          <h1>Insights</h1>
          <p>
            Observaciones explicables sobre ventas y análisis: cada una
            muestra la evidencia numérica que la origina.
          </p>
        </div>
        <div className="heading-actions">
          <select
            className="form-input period-select"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            aria-label="Período de análisis"
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
            {generating ? "Generando..." : "Generar insights"}
          </button>
          <button
            className="button-secondary"
            onClick={() => void loadInsights()}
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
        </div>
      </section>

      {generateError && (
        <div className="form-alert" role="alert">
          {generateError}
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
            <h3>Observaciones</h3>
            <p>
              {insights
                ? `${insights.total} ${
                    insights.total === 1
                      ? "observación registrada"
                      : "observaciones registradas"
                  }`
                : "Cargando..."}
            </p>
          </div>
          <div className="toolbar-controls">
            <select
              className="form-input"
              value={ruleFilter}
              onChange={(event) => {
                setRuleFilter(event.target.value);
                setPage(1);
              }}
              aria-label="Filtrar por regla"
            >
              <option value="">Todas las reglas</option>
              {rules.map((rule) => (
                <option key={rule.code} value={rule.code}>
                  {rule.name}
                </option>
              ))}
            </select>
            <select
              className="form-input"
              value={severityFilter}
              onChange={(event) => {
                setSeverityFilter(event.target.value);
                setPage(1);
              }}
              aria-label="Filtrar por severidad"
            >
              <option value="">Todas las severidades</option>
              <option value="info">Informativo</option>
              <option value="positive">Positivo</option>
              <option value="warning">Advertencia</option>
            </select>
          </div>
        </div>

        <div className="table-scroll">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>SEVERIDAD</th>
                <th>REGLA</th>
                <th>OBSERVACIÓN</th>
                <th>EVIDENCIA</th>
                <th>VÍNCULO</th>
                <th>FECHA</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {loading && !insights && (
                <tr>
                  <td colSpan={7} className="table-state">
                    <Loader2 size={19} className="spin" /> Cargando
                    observaciones...
                  </td>
                </tr>
              )}

              {!loading && error && !insights && (
                <tr>
                  <td colSpan={7} className="table-state table-state-error">
                    {error}
                  </td>
                </tr>
              )}

              {!loading && !error && insights && insights.items.length === 0 && (
                <tr>
                  <td colSpan={7} className="table-state">
                    <ListChecks size={19} /> Aún no hay observaciones:
                    genera insights con el botón «Generar insights».
                  </td>
                </tr>
              )}

              {insights?.items.map((insight) => (
                <tr key={insight.id}>
                  <td>
                    <SeverityBadge severity={insight.severity} />
                  </td>
                  <td>{insight.rule_name}</td>
                  <td>{insight.title}</td>
                  <td>
                    <EvidenceChips evidence={insight.evidence} limit={3} />
                  </td>
                  <td>
                    {insight.analysis_id !== null ? (
                      <span className="insight-link">
                        Análisis #{insight.analysis_id}
                      </span>
                    ) : (
                      <span className="insight-link">Ventas</span>
                    )}
                    {insight.dataset_name && (
                      <span className="insight-link">
                        {insight.dataset_name}
                      </span>
                    )}
                  </td>
                  <td className="date-cell">
                    {formatDate(insight.created_at)}
                  </td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="text-button"
                        onClick={() => setDetail(insight)}
                      >
                        Ver detalle
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
          title={`Observación #${detail.id}`}
          onClose={() => setDetail(null)}
          footer={
            <button
              className="button-secondary"
              onClick={() => setDetail(null)}
            >
              Cerrar
            </button>
          }
        >
          <div className="form-grid">
            <p className="form-field form-field-full">
              <SeverityBadge severity={detail.severity} />{" "}
              <span className="insight-link">{detail.rule_name}</span>
            </p>

            <p className="form-field form-field-full">
              <strong>{detail.title}</strong>
            </p>

            <p className="form-field form-field-full">{detail.description}</p>

            <div className="form-field form-field-full">
              <span>Evidencia numérica</span>
              <div className="table-scroll">
                <table className="transactions-table">
                  <thead>
                    <tr>
                      <th>DATO</th>
                      <th>VALOR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evidenceEntries(detail.evidence).map(([key, value]) => (
                      <tr key={key}>
                        <td>{evidenceLabel(key)}</td>
                        <td className="amount-cell">
                          {evidenceValue(key, value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <p className="form-field form-field-full">
              {ruleOf(detail.rule_code)?.description ??
                "Regla del motor de insights."}
            </p>

            {detail.analysis_id !== null && (
              <p className="form-field form-field-full">
                Generado por el análisis #{detail.analysis_id}
                {detail.analysis_type
                  ? ` (${ANALYSIS_LABELS[detail.analysis_type] ?? detail.analysis_type})`
                  : ""}
                {detail.dataset_name ? ` · Dataset: ${detail.dataset_name}` : ""}
                .
              </p>
            )}

            <p className="form-field form-field-full">
              Registrado el {formatDate(detail.created_at)}.
            </p>
          </div>
        </Modal>
      )}
    </>
  );
}
