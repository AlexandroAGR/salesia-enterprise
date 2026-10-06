import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  ArrowLeft,
  Calculator,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  Database,
  Dices,
  GitCompare,
  ListChecks,
  Loader2,
  Percent,
  Plus,
  RefreshCw,
  Scale,
  Search,
  Sigma,
  Trash,
} from "lucide-react";
import Modal from "../components/Modal";
import { useSearch } from "../context/search-context";
import { api, ApiError } from "../lib/api";
import type {
  AnalysisType,
  Dataset,
  DatasetDetail,
  Page,
  StatisticalAnalysis,
} from "../types";
import { formatDate } from "../utils/format";

const PAGE_SIZE = 10;

type Tab = "datasets" | "analisis" | "historial";
type AnalysisTab = "mean_median" | "random_variable" | "probability" | "bayes";

const ANALYSIS_LABELS: Record<AnalysisType, string> = {
  mean_median: "Media y mediana",
  random_variable: "Variable aleatoria",
  probability: "Probabilidades",
  bayes: "Teorema de Bayes",
};

const VARIABLE_TYPE_LABELS: Record<string, string> = {
  cualitativa: "Cualitativa",
  discreta: "Discreta",
  continua: "Continua",
};

const DISTRIBUTION_FIELDS: Record<string, string[]> = {
  uniforme: ["a", "b"],
  bernoulli: ["p"],
  binomial: ["n", "p"],
  normal: ["mu", "sigma"],
};

const PARAM_LABELS: Record<string, string> = {
  a: "Límite a",
  b: "Límite b",
  p: "Probabilidad p",
  n: "Ens. n",
  mu: "Media μ",
  sigma: "Desviación σ",
};

const COMPARISON_LABELS: Record<string, string> = {
  media_mayor_mediana: "Media > Mediana",
  media_menor_mediana: "Media < Mediana",
  media_igual_mediana: "Media = Mediana",
};

const emptyDatasetForm = {
  name: "",
  source_type: "manual",
  description: "",
};

const emptyVariableForm = {
  name: "",
  data_type: "numeric",
  variable_type: "discreta",
  description: "",
};

const emptyObservationsForm = {
  variable_id: "",
  values: "",
};

function stat(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return String(Math.round(value * 1e6) / 1e6);
}

function getMetric(analysis: StatisticalAnalysis | null, name: string) {
  return analysis?.results.find((item) => item.metric_name === name) ?? null;
}

function metricText(analysis: StatisticalAnalysis | null, name: string): string {
  return stat(getMetric(analysis, name)?.numeric_result ?? null);
}

function payloadOf(analysis: StatisticalAnalysis | null, name: string) {
  return (getMetric(analysis, name)?.result_payload ?? {}) as Record<
    string,
    unknown
  >;
}

function historySummary(analysis: StatisticalAnalysis): string {
  switch (analysis.analysis_type) {
    case "mean_median":
      return `Media ${metricText(analysis, "mean")} · Mediana ${metricText(
        analysis,
        "median",
      )}`;
    case "random_variable":
      return `E(X) ${metricText(analysis, "expected_value")} · Var ${metricText(
        analysis,
        "variance",
      )}`;
    case "probability":
      return `P(A|B) ${metricText(analysis, "p_a_given_b")} · P(B|A) ${metricText(
        analysis,
        "p_b_given_a",
      )}`;
    case "bayes":
      return `P(A|B) = ${metricText(analysis, "posterior_probability")}`;
    default:
      return "—";
  }
}

type StatCardProps = {
  title: string;
  value: string;
  description: string;
  icon: React.ReactNode;
  color: "blue" | "cyan" | "violet" | "orange";
};

function StatCard({ title, value, description, icon, color }: StatCardProps) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className={`metric-icon metric-${color}`}>{icon}</span>
      </div>
      <p className="metric-title">{title}</p>
      <div className="metric-value-row">
        <strong>{value}</strong>
      </div>
      <div className="metric-bottom">
        <span className="metric-description">{description}</span>
      </div>
    </article>
  );
}

export default function AnalyticsPage() {
  const { search, setSearch } = useSearch();

  const [tab, setTab] = useState<Tab>("datasets");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // -----------------------------------------------------------
  // Datasets
  // -----------------------------------------------------------
  const [datasets, setDatasets] = useState<Page<Dataset> | null>(null);
  const [datasetsLoading, setDatasetsLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<DatasetDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Modales de datasets
  const [datasetModal, setDatasetModal] = useState(false);
  const [datasetForm, setDatasetForm] = useState(emptyDatasetForm);
  const [variableModal, setVariableModal] = useState(false);
  const [variableForm, setVariableForm] = useState(emptyVariableForm);
  const [observationsModal, setObservationsModal] = useState(false);
  const [observationsForm, setObservationsForm] = useState(
    emptyObservationsForm,
  );
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // -----------------------------------------------------------
  // Motor de análisis
  // -----------------------------------------------------------
  const [analysisTab, setAnalysisTab] = useState<AnalysisTab>("mean_median");
  const [analysisDatasetId, setAnalysisDatasetId] = useState("");
  const [analysisDetail, setAnalysisDetail] =
    useState<DatasetDetail | null>(null);
  const [selectedVariable, setSelectedVariable] = useState("");
  const [distribution, setDistribution] = useState("normal");
  const [distParams, setDistParams] = useState<Record<string, string>>({
    mu: "",
    sigma: "",
  });
  const [probForm, setProbForm] = useState({ p_a: "", p_b: "", p_a_and_b: "" });
  const [bayesForm, setBayesForm] = useState({
    probability_a: "",
    probability_b_given_a: "",
    probability_b: "",
    probability_b_given_not_a: "",
  });
  const [running, setRunning] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] =
    useState<StatisticalAnalysis | null>(null);

  // -----------------------------------------------------------
  // Historial
  // -----------------------------------------------------------
  const [history, setHistory] = useState<Page<StatisticalAnalysis> | null>(
    null,
  );
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyPage, setHistoryPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState("");
  const [historyDetail, setHistoryDetail] =
    useState<StatisticalAnalysis | null>(null);

  // -----------------------------------------------------------
  // Cargas de datos
  // -----------------------------------------------------------
  const loadDatasets = useCallback(async () => {
    setDatasetsLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<Dataset>>("/datasets", {
        query: {
          search: search.trim() || undefined,
          page: 1,
          page_size: 100,
        },
      });
      setDatasets(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar los datasets.",
      );
    } finally {
      setDatasetsLoading(false);
    }
  }, [search]);

  const loadDetail = useCallback(async (datasetId: number) => {
    setDetailLoading(true);
    setError(null);

    try {
      const result = await api.get<DatasetDetail>(`/datasets/${datasetId}`);
      setDetail(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo cargar el dataset.",
      );
      setSelectedId(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);

    try {
      const result = await api.get<Page<StatisticalAnalysis>>("/analyses", {
        query: {
          analysis_type: typeFilter || undefined,
          page: historyPage,
          page_size: PAGE_SIZE,
        },
      });
      setHistory(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo cargar el historial.",
      );
    } finally {
      setHistoryLoading(false);
    }
  }, [typeFilter, historyPage]);

  const loadAnalysisDetail = useCallback(async (datasetId: string) => {
    if (!datasetId) {
      setAnalysisDetail(null);
      return;
    }

    try {
      const result = await api.get<DatasetDetail>(`/datasets/${datasetId}`);
      setAnalysisDetail(result);
    } catch {
      setAnalysisDetail(null);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadDatasets(), 0);
    return () => window.clearTimeout(timer);
  }, [loadDatasets]);

  useEffect(() => {
    if (selectedId === null) return;
    const timer = window.setTimeout(() => void loadDetail(selectedId), 0);
    return () => window.clearTimeout(timer);
  }, [selectedId, loadDetail]);

  useEffect(() => {
    if (tab !== "historial") return;
    const timer = window.setTimeout(() => void loadHistory(), 0);
    return () => window.clearTimeout(timer);
  }, [tab, loadHistory]);

  useEffect(() => {
    const timer = window.setTimeout(
      () => void loadAnalysisDetail(analysisDatasetId),
      0,
    );
    return () => window.clearTimeout(timer);
  }, [analysisDatasetId, loadAnalysisDetail]);

  // -----------------------------------------------------------
  // Datasets: acciones
  // -----------------------------------------------------------
  const handleDatasetSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);

    try {
      const created = await api.post<DatasetDetail>("/datasets", {
        name: datasetForm.name.trim(),
        source_type: datasetForm.source_type,
        description: datasetForm.description.trim() || null,
      });
      setDatasetModal(false);
      setDatasetForm(emptyDatasetForm);
      setNotice(`Dataset "${created.name}" creado.`);
      await loadDatasets();
      setSelectedId(created.id);
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo crear el dataset.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleVariableSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (selectedId === null) return;

    setSubmitting(true);
    setFormError(null);

    try {
      await api.post(`/datasets/${selectedId}/variables`, {
        name: variableForm.name.trim(),
        data_type: variableForm.data_type,
        variable_type: variableForm.variable_type,
        description: variableForm.description.trim() || null,
      });
      setVariableModal(false);
      setVariableForm(emptyVariableForm);
      setNotice(`Variable "${variableForm.name.trim()}" registrada.`);
      await loadDetail(selectedId);
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo crear la variable.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleObservationsSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (selectedId === null) return;

    setSubmitting(true);
    setFormError(null);

    try {
      const variable = detail?.variables.find(
        (item) => item.id === Number(observationsForm.variable_id),
      );

      if (!variable) {
        setFormError("Selecciona una variable.");
        return;
      }

      const lines = observationsForm.values
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

      if (lines.length === 0) {
        setFormError("Escribe al menos un valor (uno por línea).");
        return;
      }

      const items =
        variable.data_type === "numeric"
          ? lines.map((line, index) => {
              const value = Number(line);
              if (!Number.isFinite(value)) {
                throw new Error(
                  `La línea ${index + 1} no es un número: "${line}"`,
                );
              }
              return { variable_id: variable.id, numeric_value: value };
            })
          : lines.map((line) => ({
              variable_id: variable.id,
              text_value: line,
            }));

      const result = await api.post<{ created: number }>(
        `/datasets/${selectedId}/observations`,
        { items },
      );

      setObservationsModal(false);
      setObservationsForm(emptyObservationsForm);
      setNotice(
        `${result.created} observación${result.created === 1 ? "" : "es"} ` +
          `registradas en "${variable.name}".`,
      );
      await loadDetail(selectedId);
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : caught instanceof Error
            ? caught.message
            : "No se pudieron registrar las observaciones.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteDataset = async () => {
    if (selectedId === null || !detail) return;

    const confirmed = window.confirm(
      `¿Eliminar el dataset "${detail.name}" y sus observaciones? ` +
        "Los análisis registrados se conservarán.",
    );
    if (!confirmed) return;

    try {
      await api.del(`/datasets/${selectedId}`);
      setNotice(`Dataset "${detail.name}" eliminado.`);
      setSelectedId(null);
      await loadDatasets();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo eliminar el dataset.",
      );
    }
  };

  // -----------------------------------------------------------
  // Motor: ejecución de análisis
  // -----------------------------------------------------------
  const runAnalysis = async (path: string, body: unknown) => {
    setRunning(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    try {
      const result = await api.post<StatisticalAnalysis>(path, body);
      setAnalysisResult(result);
      void loadHistory();
      return result;
    } catch (caught) {
      setAnalysisError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo ejecutar el análisis.",
      );
      return null;
    } finally {
      setRunning(false);
    }
  };

  const requireVariable = (): number | null => {
    if (!selectedVariable) {
      setAnalysisError("Selecciona una variable numérica del dataset.");
      return null;
    }
    return Number(selectedVariable);
  };

  const handleMeanMedian = async () => {
    const variableId = requireVariable();
    if (variableId === null) return;
    await runAnalysis("/analyses/mean-median", { variable_id: variableId });
  };

  const handleRandomVariable = async () => {
    const variableId = requireVariable();
    if (variableId === null) return;

    const parameters: Record<string, number> = {};
    for (const field of DISTRIBUTION_FIELDS[distribution]) {
      const raw = distParams[field] ?? "";
      const value = Number(raw);
      if (raw.trim() === "" || !Number.isFinite(value)) {
        setAnalysisError(`Completa el parámetro "${PARAM_LABELS[field]}".`);
        return;
      }
      parameters[field] = value;
    }

    await runAnalysis("/analyses/random-variable", {
      variable_id: variableId,
      distribution,
      parameters,
    });
  };

  const handleProbability = async () => {
    const values = {
      p_a: Number(probForm.p_a),
      p_b: Number(probForm.p_b),
      p_a_and_b: Number(probForm.p_a_and_b),
    };

    if (
      probForm.p_a.trim() === "" ||
      probForm.p_b.trim() === "" ||
      probForm.p_a_and_b.trim() === ""
    ) {
      setAnalysisError("Completa P(A), P(B) y P(A ∩ B).");
      return;
    }

    await runAnalysis("/analyses/probability", values);
  };

  const handleBayes = async () => {
    if (
      bayesForm.probability_a.trim() === "" ||
      bayesForm.probability_b_given_a.trim() === ""
    ) {
      setAnalysisError("Completa P(A) y P(B|A).");
      return;
    }

    if (
      bayesForm.probability_b.trim() === "" &&
      bayesForm.probability_b_given_not_a.trim() === ""
    ) {
      setAnalysisError("Indica P(B) o P(B|¬A) para el denominador.");
      return;
    }

    const body: Record<string, number> = {
      probability_a: Number(bayesForm.probability_a),
      probability_b_given_a: Number(bayesForm.probability_b_given_a),
    };

    if (bayesForm.probability_b.trim() !== "") {
      body.probability_b = Number(bayesForm.probability_b);
    }
    if (bayesForm.probability_b_given_not_a.trim() !== "") {
      body.probability_b_given_not_a = Number(
        bayesForm.probability_b_given_not_a,
      );
    }

    await runAnalysis("/analyses/bayes", body);
  };

  const numericVariables =
    analysisDetail?.variables.filter(
      (variable) => variable.data_type === "numeric",
    ) ?? [];

  const totalPages = history
    ? Math.max(1, Math.ceil(history.total / history.page_size))
    : 1;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            MOTOR ESTADÍSTICO · SEMANA 07
          </div>
          <h1>Analytics</h1>
          <p>
            Variables, media, mediana, variables aleatorias, probabilidades y
            Teorema de Bayes.
          </p>
        </div>
        <div className="heading-actions">
          <button
            className="button-secondary"
            onClick={() => {
              void loadDatasets();
              if (tab === "historial") void loadHistory();
              if (selectedId !== null) void loadDetail(selectedId);
            }}
          >
            <RefreshCw size={16} className={datasetsLoading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
          {tab === "datasets" && selectedId === null && (
            <button
              className="button-primary"
              onClick={() => {
                setFormError(null);
                setDatasetModal(true);
              }}
            >
              <Plus size={17} />
              Nuevo dataset
            </button>
          )}
        </div>
      </section>

      <div className="tabs">
        <button
          className={`tab ${tab === "datasets" ? "tab-active" : ""}`}
          onClick={() => setTab("datasets")}
        >
          <Database size={16} /> Datasets
        </button>
        <button
          className={`tab ${tab === "analisis" ? "tab-active" : ""}`}
          onClick={() => setTab("analisis")}
        >
          <Calculator size={16} /> Análisis
        </button>
        <button
          className={`tab ${tab === "historial" ? "tab-active" : ""}`}
          onClick={() => setTab("historial")}
        >
          <ClipboardList size={16} /> Historial
        </button>
      </div>

      {notice && (
        <div className="form-alert form-alert-block" role="status">
          {notice}
        </div>
      )}

      {/* ---------------------------------------------------------
          Pestaña 1: Datasets y clasificación de variables
          --------------------------------------------------------- */}
      {tab === "datasets" && (
        <section className="panel data-panel">
          {selectedId === null ? (
            <>
              <div className="panel-header data-toolbar">
                <div>
                  <h3>Datasets</h3>
                  <p>
                    {datasets
                      ? `${datasets.total} dataset${datasets.total === 1 ? "" : "s"}`
                      : "Cargando..."}
                  </p>
                </div>
                <div className="toolbar-controls">
                  <label className="search-box">
                    <Search size={17} />
                    <input
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Buscar dataset..."
                      aria-label="Buscar dataset"
                    />
                  </label>
                </div>
              </div>

              <div className="table-scroll">
                <table className="transactions-table">
                  <thead>
                    <tr>
                      <th>NOMBRE</th>
                      <th>ORIGEN</th>
                      <th>VARIABLES</th>
                      <th>CREADO</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {datasetsLoading && !datasets && (
                      <tr>
                        <td colSpan={5} className="table-state">
                          <Loader2 size={19} className="spin" /> Cargando
                          datasets...
                        </td>
                      </tr>
                    )}

                    {!datasetsLoading && error && (
                      <tr>
                        <td
                          colSpan={5}
                          className="table-state table-state-error"
                        >
                          {error}
                        </td>
                      </tr>
                    )}

                    {!datasetsLoading && !error && datasets &&
                      datasets.items.length === 0 && (
                        <tr>
                          <td colSpan={5} className="table-state">
                            <Database size={19} /> Sin datasets. Crea el
                            primero para comenzar.
                          </td>
                        </tr>
                      )}

                    {datasets?.items.map((dataset) => (
                      <tr key={dataset.id}>
                        <td>
                          <div className="customer-cell">
                            <div className="customer-avatar avatar-cyan">
                              <Database size={15} />
                            </div>
                            <div className="customer-copy">
                              <strong>{dataset.name}</strong>
                              <span>{dataset.description ?? "Sin descripción"}</span>
                            </div>
                          </div>
                        </td>
                        <td>{dataset.source_type}</td>
                        <td className="amount-cell">
                          {dataset.variables_count}
                        </td>
                        <td className="date-cell">
                          {formatDate(dataset.created_at)}
                        </td>
                        <td>
                          <div className="row-actions">
                            <button
                              className="text-button"
                              onClick={() => {
                                setNotice(null);
                                setSelectedId(dataset.id);
                              }}
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
            </>
          ) : (
            <>
              <div className="panel-header data-toolbar">
                <div>
                  <button
                    className="text-button"
                    onClick={() => {
                      setNotice(null);
                      setDetail(null);
                      setSelectedId(null);
                    }}
                  >
                    <ArrowLeft size={15} /> Volver a datasets
                  </button>
                  <h3>{detail?.name ?? "Dataset"}</h3>
                  <p>
                    {detail
                      ? `${detail.source_type} · ${detail.variables.length} variable${detail.variables.length === 1 ? "" : "s"} · creado ${formatDate(detail.created_at)}`
                      : "Cargando..."}
                  </p>
                </div>
                <div className="toolbar-controls">
                  <button
                    className="button-secondary"
                    onClick={() => void handleDeleteDataset()}
                  >
                    <Trash size={16} /> Eliminar
                  </button>
                  <button
                    className="button-primary"
                    onClick={() => {
                      setFormError(null);
                      setVariableModal(true);
                    }}
                  >
                    <Plus size={17} /> Nueva variable
                  </button>
                </div>
              </div>

              <div className="table-scroll">
                <table className="transactions-table">
                  <thead>
                    <tr>
                      <th>VARIABLE</th>
                      <th>TIPO DE DATO</th>
                      <th>CLASIFICACIÓN</th>
                      <th>OBSERVACIONES</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {detailLoading && !detail && (
                      <tr>
                        <td colSpan={5} className="table-state">
                          <Loader2 size={19} className="spin" /> Cargando
                          variables...
                        </td>
                      </tr>
                    )}

                    {!detailLoading && detail &&
                      detail.variables.length === 0 && (
                        <tr>
                          <td colSpan={5} className="table-state">
                            <Sigma size={19} /> Sin variables. Crea una variable
                            para clasificar tus datos.
                          </td>
                        </tr>
                      )}

                    {detail?.variables.map((variable) => (
                      <tr key={variable.id}>
                        <td>
                          <div className="customer-copy">
                            <strong>{variable.name}</strong>
                            <span>{variable.description ?? "—"}</span>
                          </div>
                        </td>
                        <td>
                          {variable.data_type === "numeric"
                            ? "Numérico"
                            : "Texto"}
                        </td>
                        <td>
                          <span
                            className={`status ${
                              variable.variable_type === "cualitativa"
                                ? "status-pendiente"
                                : "status-completada"
                            }`}
                          >
                            <i />
                            {VARIABLE_TYPE_LABELS[variable.variable_type] ??
                              variable.variable_type}
                          </span>
                        </td>
                        <td className="amount-cell">
                          {variable.observations_count}
                        </td>
                        <td>
                          <div className="row-actions">
                            <button
                              className="text-button"
                              onClick={() => {
                                setFormError(null);
                                setObservationsForm({
                                  variable_id: String(variable.id),
                                  values: "",
                                });
                                setObservationsModal(true);
                              }}
                            >
                              Agregar datos
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}

      {/* ---------------------------------------------------------
          Pestaña 2: Motor de análisis
          --------------------------------------------------------- */}
      {tab === "analisis" && (
        <>
          <div className="tabs">
            <button
              className={`tab ${analysisTab === "mean_median" ? "tab-active" : ""}`}
              onClick={() => {
                setAnalysisTab("mean_median");
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            >
              <Sigma size={16} /> Media y mediana
            </button>
            <button
              className={`tab ${analysisTab === "random_variable" ? "tab-active" : ""}`}
              onClick={() => {
                setAnalysisTab("random_variable");
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            >
              <Dices size={16} /> Variable aleatoria
            </button>
            <button
              className={`tab ${analysisTab === "probability" ? "tab-active" : ""}`}
              onClick={() => {
                setAnalysisTab("probability");
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            >
              <Percent size={16} /> Probabilidades
            </button>
            <button
              className={`tab ${analysisTab === "bayes" ? "tab-active" : ""}`}
              onClick={() => {
                setAnalysisTab("bayes");
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            >
              <Scale size={16} /> Bayes
            </button>
          </div>

          <section className="panel data-panel">
            <div className="panel-header data-toolbar">
              <div>
                <h3>{ANALYSIS_LABELS[analysisTab]}</h3>
                <p>
                  {analysisTab === "mean_median" &&
                    "Media aritmética y mediana de una variable numérica, con comparación."}
                  {analysisTab === "random_variable" &&
                    "Esperanza, varianza y desviación estándar de una distribución."}
                  {analysisTab === "probability" &&
                    "Probabilidades condicionales e independencia de eventos."}
                  {analysisTab === "bayes" &&
                    "P(A|B) = P(A) · P(B|A) / P(B), con resultado reproducible."}
                </p>
              </div>
            </div>

            <div className="form-grid">
              {(analysisTab === "mean_median" ||
                analysisTab === "random_variable") && (
                <>
                  <label className="form-field">
                    <span>Dataset *</span>
                    <select
                      className="form-input"
                      value={analysisDatasetId}
                      onChange={(event) => {
                        setAnalysisDatasetId(event.target.value);
                        setSelectedVariable("");
                      }}
                      aria-label="Seleccionar dataset"
                    >
                      <option value="">Selecciona un dataset...</option>
                      {datasets?.items.map((dataset) => (
                        <option key={dataset.id} value={dataset.id}>
                          {dataset.name}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="form-field">
                    <span>Variable numérica *</span>
                    <select
                      className="form-input"
                      value={selectedVariable}
                      onChange={(event) =>
                        setSelectedVariable(event.target.value)
                      }
                      disabled={!analysisDatasetId}
                      aria-label="Seleccionar variable"
                    >
                      <option value="">
                        {!analysisDatasetId
                          ? "Elige primero un dataset..."
                          : numericVariables.length === 0
                            ? "Sin variables numéricas..."
                            : "Selecciona una variable..."}
                      </option>
                      {numericVariables.map((variable) => (
                        <option key={variable.id} value={variable.id}>
                          {variable.name} ·{" "}
                          {VARIABLE_TYPE_LABELS[variable.variable_type]}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              )}

              {analysisTab === "random_variable" && (
                <label className="form-field">
                  <span>Distribución *</span>
                  <select
                    className="form-input"
                    value={distribution}
                    onChange={(event) => {
                      const next = event.target.value;
                      setDistribution(next);
                      setDistParams(
                        Object.fromEntries(
                          DISTRIBUTION_FIELDS[next].map((field) => [field, ""]),
                        ),
                      );
                    }}
                    aria-label="Distribución"
                  >
                    <option value="uniforme">Uniforme U(a, b)</option>
                    <option value="bernoulli">Bernoulli(p)</option>
                    <option value="binomial">Binomial(n, p)</option>
                    <option value="normal">Normal(μ, σ)</option>
                  </select>
                </label>
              )}

              {analysisTab === "random_variable" &&
                DISTRIBUTION_FIELDS[distribution].map((field) => (
                  <label className="form-field" key={field}>
                    <span>{PARAM_LABELS[field]} *</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      value={distParams[field] ?? ""}
                      onChange={(event) =>
                        setDistParams({
                          ...distParams,
                          [field]: event.target.value,
                        })
                      }
                      placeholder={field === "n" ? "ej. 10" : "ej. 0.5"}
                    />
                  </label>
                ))}

              {analysisTab === "probability" && (
                <>
                  <label className="form-field">
                    <span>P(A) *</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={probForm.p_a}
                      onChange={(event) =>
                        setProbForm({ ...probForm, p_a: event.target.value })
                      }
                      placeholder="ej. 0.6"
                    />
                  </label>
                  <label className="form-field">
                    <span>P(B) *</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={probForm.p_b}
                      onChange={(event) =>
                        setProbForm({ ...probForm, p_b: event.target.value })
                      }
                      placeholder="ej. 0.5"
                    />
                  </label>
                  <label className="form-field">
                    <span>P(A ∩ B) *</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={probForm.p_a_and_b}
                      onChange={(event) =>
                        setProbForm({
                          ...probForm,
                          p_a_and_b: event.target.value,
                        })
                      }
                      placeholder="ej. 0.3"
                    />
                  </label>
                </>
              )}

              {analysisTab === "bayes" && (
                <>
                  <label className="form-field">
                    <span>P(A) · prior *</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={bayesForm.probability_a}
                      onChange={(event) =>
                        setBayesForm({
                          ...bayesForm,
                          probability_a: event.target.value,
                        })
                      }
                      placeholder="ej. 0.01"
                    />
                  </label>
                  <label className="form-field">
                    <span>P(B|A) · verosimilitud *</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={bayesForm.probability_b_given_a}
                      onChange={(event) =>
                        setBayesForm({
                          ...bayesForm,
                          probability_b_given_a: event.target.value,
                        })
                      }
                      placeholder="ej. 0.9"
                    />
                  </label>
                  <label className="form-field">
                    <span>P(B) · marginal</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={bayesForm.probability_b}
                      onChange={(event) =>
                        setBayesForm({
                          ...bayesForm,
                          probability_b: event.target.value,
                        })
                      }
                      placeholder="ej. 0.42"
                    />
                  </label>
                  <label className="form-field">
                    <span>P(B|¬A) · alternativa</span>
                    <input
                      className="form-input"
                      type="number"
                      step="any"
                      min="0"
                      max="1"
                      value={bayesForm.probability_b_given_not_a}
                      onChange={(event) =>
                        setBayesForm({
                          ...bayesForm,
                          probability_b_given_not_a: event.target.value,
                        })
                      }
                      placeholder="si no conoces P(B)"
                    />
                  </label>
                </>
              )}

              <div className="form-field form-field-full">
                <button
                  className="button-primary"
                  onClick={() => {
                    if (analysisTab === "mean_median") void handleMeanMedian();
                    if (analysisTab === "random_variable")
                      void handleRandomVariable();
                    if (analysisTab === "probability") void handleProbability();
                    if (analysisTab === "bayes") void handleBayes();
                  }}
                  disabled={running}
                >
                  {running ? (
                    <>
                      <Loader2 size={17} className="spin" /> Calculando...
                    </>
                  ) : (
                    <>
                      <Calculator size={17} /> Calcular
                    </>
                  )}
                </button>
              </div>
            </div>

            {analysisError && (
              <div className="form-alert" role="alert">
                {analysisError}
              </div>
            )}

            {analysisResult && analysisTab === "mean_median" && (
              <>
                <section className="metrics-grid">
                  <StatCard
                    title="Media aritmética"
                    value={metricText(analysisResult, "mean")}
                    description="Suma de valores / cantidad"
                    icon={<Sigma size={19} />}
                    color="blue"
                  />
                  <StatCard
                    title="Mediana"
                    value={metricText(analysisResult, "median")}
                    description="Valor central de los datos ordenados"
                    icon={<Sigma size={19} />}
                    color="cyan"
                  />
                  <StatCard
                    title="Comparación"
                    value={
                      COMPARISON_LABELS[
                        String(payloadOf(analysisResult, "comparison").relation)
                      ] ?? "—"
                    }
                    description={String(
                      payloadOf(analysisResult, "comparison").interpretation ??
                        "",
                    )}
                    icon={<GitCompare size={19} />}
                    color="orange"
                  />
                  <StatCard
                    title="Observaciones"
                    value={metricText(analysisResult, "count")}
                    description={
                      String(
                        analysisResult.parameters.variable_name ?? "",
                      ) || "Variable analizada"
                    }
                    icon={<ClipboardList size={19} />}
                    color="violet"
                  />
                </section>
              </>
            )}

            {analysisResult && analysisTab === "random_variable" && (
              <section className="metrics-grid">
                <StatCard
                  title="Esperanza E(X)"
                  value={metricText(analysisResult, "expected_value")}
                  description={String(
                    payloadOf(analysisResult, "expected_value").formula ?? "",
                  )}
                  icon={<Sigma size={19} />}
                  color="violet"
                />
                <StatCard
                  title="Varianza"
                  value={metricText(analysisResult, "variance")}
                  description={String(
                    payloadOf(analysisResult, "variance").formula ?? "",
                  )}
                  icon={<Sigma size={19} />}
                  color="blue"
                />
                <StatCard
                  title="Desviación estándar"
                  value={metricText(analysisResult, "std_dev")}
                  description="σ = √Var(X)"
                  icon={<Sigma size={19} />}
                  color="cyan"
                />
                {getMetric(analysisResult, "empirical_mean") && (
                  <StatCard
                    title="Media empírica"
                    value={metricText(analysisResult, "empirical_mean")}
                    description={`Diferencia con E(X): ${stat(
                      Number(
                        payloadOf(analysisResult, "empirical_mean")
                          .difference,
                      ),
                    )}`}
                    icon={<ClipboardList size={19} />}
                    color="orange"
                  />
                )}
              </section>
            )}

            {analysisResult && analysisTab === "probability" && (
              <section className="metrics-grid">
                <StatCard
                  title="P(A|B)"
                  value={metricText(analysisResult, "p_a_given_b")}
                  description="P(A ∩ B) / P(B)"
                  icon={<Percent size={19} />}
                  color="blue"
                />
                <StatCard
                  title="P(B|A)"
                  value={metricText(analysisResult, "p_b_given_a")}
                  description="P(A ∩ B) / P(A)"
                  icon={<Percent size={19} />}
                  color="cyan"
                />
                <StatCard
                  title="Independencia"
                  value={
                    payloadOf(analysisResult, "independence").independent
                      ? "Independientes"
                      : "Dependientes"
                  }
                  description={`P(A)·P(B) = ${stat(
                    Number(
                      payloadOf(analysisResult, "independence").p_a_times_p_b,
                    ),
                  )}`}
                  icon={<Scale size={19} />}
                  color={
                    payloadOf(analysisResult, "independence").independent
                      ? "violet"
                      : "orange"
                  }
                />
              </section>
            )}

            {analysisResult && analysisTab === "bayes" && (
              <>
                <section className="metrics-grid">
                  <StatCard
                    title="Posterior P(A|B)"
                    value={metricText(analysisResult, "posterior_probability")}
                    description="P(A) · P(B|A) / P(B)"
                    icon={<Scale size={19} />}
                    color="orange"
                  />
                  <StatCard
                    title="Marginal P(B)"
                    value={metricText(analysisResult, "marginal_probability")}
                    description={
                      payloadOf(analysisResult, "marginal_probability")
                        .computed_from_complement
                        ? "Calculada con P(B|¬A)"
                        : "Indicada por el usuario"
                    }
                    icon={<Percent size={19} />}
                    color="blue"
                  />
                </section>
                {analysisResult.bayes?.explanation && (
                  <div className="info-panel">
                    <strong>Explicación reproducible</strong>
                    <p>{analysisResult.bayes.explanation}</p>
                  </div>
                )}
              </>
            )}
          </section>
        </>
      )}

      {/* ---------------------------------------------------------
          Pestaña 3: Historial de análisis
          --------------------------------------------------------- */}
      {tab === "historial" && (
        <section className="panel data-panel">
          <div className="panel-header data-toolbar">
            <div>
              <h3>Historial de análisis</h3>
              <p>
                {history
                  ? `${history.total} análisis registrados`
                  : "Cargando..."}
              </p>
            </div>
            <div className="toolbar-controls">
              <select
                className="form-input"
                value={typeFilter}
                onChange={(event) => {
                  setTypeFilter(event.target.value);
                  setHistoryPage(1);
                }}
                aria-label="Filtrar por tipo"
              >
                <option value="">Todos los tipos</option>
                <option value="mean_median">Media y mediana</option>
                <option value="random_variable">Variable aleatoria</option>
                <option value="probability">Probabilidades</option>
                <option value="bayes">Teorema de Bayes</option>
              </select>
            </div>
          </div>

          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>FECHA</th>
                  <th>TIPO</th>
                  <th>DATASET</th>
                  <th>RESULTADO</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {historyLoading && !history && (
                  <tr>
                    <td colSpan={5} className="table-state">
                      <Loader2 size={19} className="spin" /> Cargando
                      historial...
                    </td>
                  </tr>
                )}

                {!historyLoading && history && history.items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="table-state">
                      <ListChecks size={19} /> Aún no hay análisis registrados.
                    </td>
                  </tr>
                )}

                {history?.items.map((analysis) => (
                  <tr key={analysis.id}>
                    <td className="date-cell">
                      {formatDate(analysis.created_at)}
                    </td>
                    <td>
                      <span className="status status-completada">
                        <i />
                        {ANALYSIS_LABELS[analysis.analysis_type]}
                      </span>
                    </td>
                    <td>{analysis.dataset_name ?? "General"}</td>
                    <td className="amount-cell">
                      {historySummary(analysis)}
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="text-button"
                          onClick={() => setHistoryDetail(analysis)}
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
                disabled={historyPage <= 1}
                onClick={() => setHistoryPage((value) => value - 1)}
                aria-label="Página anterior"
              >
                <ChevronLeft size={17} />
              </button>
              <span>
                Página {historyPage} de {totalPages}
              </span>
              <button
                className="icon-button"
                disabled={historyPage >= totalPages}
                onClick={() => setHistoryPage((value) => value + 1)}
                aria-label="Página siguiente"
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ---------------------------------------------------------
          Modal: nuevo dataset
          --------------------------------------------------------- */}
      {datasetModal && (
        <Modal
          title="Nuevo dataset"
          onClose={() => setDatasetModal(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setDatasetModal(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={(event) =>
                  void handleDatasetSubmit(event as unknown as FormEvent)
                }
                disabled={submitting}
              >
                {submitting ? "Guardando..." : "Crear"}
              </button>
            </>
          }
        >
          <form className="form-grid" onSubmit={(event) => void handleDatasetSubmit(event)}>
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field form-field-full">
              <span>Nombre *</span>
              <input
                className="form-input"
                value={datasetForm.name}
                onChange={(event) =>
                  setDatasetForm({ ...datasetForm, name: event.target.value })
                }
                minLength={2}
                maxLength={160}
                placeholder="ej. Ventas de la semana 07"
                required
              />
            </label>

            <label className="form-field">
              <span>Origen *</span>
              <select
                className="form-input"
                value={datasetForm.source_type}
                onChange={(event) =>
                  setDatasetForm({
                    ...datasetForm,
                    source_type: event.target.value,
                  })
                }
                required
              >
                <option value="manual">Manual</option>
                <option value="ventas">Ventas</option>
                <option value="inventario">Inventario</option>
                <option value="importado">Importado</option>
                <option value="otro">Otro</option>
              </select>
            </label>

            <label className="form-field">
              <span>Descripción</span>
              <input
                className="form-input"
                value={datasetForm.description}
                onChange={(event) =>
                  setDatasetForm({
                    ...datasetForm,
                    description: event.target.value,
                  })
                }
                maxLength={1000}
                placeholder="Opcional"
              />
            </label>

            <button type="submit" className="hidden-submit" aria-hidden="true" />
          </form>
        </Modal>
      )}

      {/* ---------------------------------------------------------
          Modal: nueva variable (clasificación estadística)
          --------------------------------------------------------- */}
      {variableModal && (
        <Modal
          title="Nueva variable"
          onClose={() => setVariableModal(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setVariableModal(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={(event) =>
                  void handleVariableSubmit(event as unknown as FormEvent)
                }
                disabled={submitting}
              >
                {submitting ? "Guardando..." : "Registrar"}
              </button>
            </>
          }
        >
          <form className="form-grid" onSubmit={(event) => void handleVariableSubmit(event)}>
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field form-field-full">
              <span>Nombre *</span>
              <input
                className="form-input"
                value={variableForm.name}
                onChange={(event) =>
                  setVariableForm({
                    ...variableForm,
                    name: event.target.value,
                  })
                }
                maxLength={120}
                placeholder="ej. monto_venta"
                required
              />
            </label>

            <label className="form-field">
              <span>Tipo de dato *</span>
              <select
                className="form-input"
                value={variableForm.data_type}
                onChange={(event) =>
                  setVariableForm({
                    ...variableForm,
                    data_type: event.target.value as
                      | "numeric"
                      | "text",
                  })
                }
                required
              >
                <option value="numeric">Numérico</option>
                <option value="text">Texto</option>
              </select>
            </label>

            <label className="form-field">
              <span>Clasificación estadística *</span>
              <select
                className="form-input"
                value={variableForm.variable_type}
                onChange={(event) =>
                  setVariableForm({
                    ...variableForm,
                    variable_type: event.target.value as
                      | "cualitativa"
                      | "discreta"
                      | "continua",
                  })
                }
                required
              >
                <option value="cualitativa">Cualitativa (categórica)</option>
                <option value="discreta">Cuantitativa discreta</option>
                <option value="continua">Cuantitativa continua</option>
              </select>
            </label>

            <label className="form-field form-field-full">
              <span>Descripción</span>
              <input
                className="form-input"
                value={variableForm.description}
                onChange={(event) =>
                  setVariableForm({
                    ...variableForm,
                    description: event.target.value,
                  })
                }
                maxLength={500}
                placeholder="Opcional"
              />
            </label>

            <button type="submit" className="hidden-submit" aria-hidden="true" />
          </form>
        </Modal>
      )}

      {/* ---------------------------------------------------------
          Modal: agregar observaciones
          --------------------------------------------------------- */}
      {observationsModal && (
        <Modal
          title="Agregar observaciones"
          onClose={() => setObservationsModal(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setObservationsModal(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={(event) =>
                  void handleObservationsSubmit(
                    event as unknown as FormEvent,
                  )
                }
                disabled={submitting}
              >
                {submitting ? "Guardando..." : "Registrar"}
              </button>
            </>
          }
        >
          <form
            className="form-grid"
            onSubmit={(event) => void handleObservationsSubmit(event)}
          >
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field form-field-full">
              <span>Variable *</span>
              <select
                className="form-input"
                value={observationsForm.variable_id}
                onChange={(event) =>
                  setObservationsForm({
                    ...observationsForm,
                    variable_id: event.target.value,
                  })
                }
                required
              >
                <option value="">Selecciona una variable...</option>
                {detail?.variables.map((variable) => (
                  <option key={variable.id} value={variable.id}>
                    {variable.name} ·{" "}
                    {variable.data_type === "numeric" ? "numérico" : "texto"}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field form-field-full">
              <span>Valores (uno por línea) *</span>
              <textarea
                className="form-input"
                rows={6}
                value={observationsForm.values}
                onChange={(event) =>
                  setObservationsForm({
                    ...observationsForm,
                    values: event.target.value,
                  })
                }
                placeholder={
                  detail?.variables.find(
                    (item) =>
                      item.id === Number(observationsForm.variable_id),
                  )?.data_type === "text"
                    ? "Norte\nSur\nEste"
                    : "10\n20\n30"
                }
                required
              />
            </label>

            <button type="submit" className="hidden-submit" aria-hidden="true" />
          </form>
        </Modal>
      )}

      {/* ---------------------------------------------------------
          Modal: detalle del análisis en el historial
          --------------------------------------------------------- */}
      {historyDetail && (
        <Modal
          title={`Análisis #${historyDetail.id} · ${ANALYSIS_LABELS[historyDetail.analysis_type]}`}
          onClose={() => setHistoryDetail(null)}
        >
          <div className="form-grid">
            <p className="form-field form-field-full">
              {formatDate(historyDetail.created_at)} ·{" "}
              {historyDetail.dataset_name ?? "Análisis general"} · estado:{" "}
              {historyDetail.status}
            </p>

            <div className="table-scroll form-field-full">
              <table className="transactions-table">
                <thead>
                  <tr>
                    <th>MÉTRICA</th>
                    <th>VALOR</th>
                    <th>DETALLE</th>
                  </tr>
                </thead>
                <tbody>
                  {historyDetail.results.map((result) => (
                    <tr key={result.id}>
                      <td>{result.metric_name}</td>
                      <td className="amount-cell">
                        {stat(result.numeric_result)}
                      </td>
                      <td>
                        {String(
                          result.result_payload.interpretation ??
                            result.result_payload.explanation ??
                            result.result_payload.formula ??
                            "",
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {historyDetail.bayes && (
              <div className="info-panel form-field-full">
                <strong>Teorema de Bayes</strong>
                <p>{historyDetail.bayes.explanation}</p>
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
