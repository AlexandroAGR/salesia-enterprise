import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronDown,
  CreditCard,
  Download,
  Filter,
  Plus,
  ShoppingCart,
  Sparkles,
  Target,
  Users,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import MetricCard from "../components/MetricCard";
import { useSearch } from "../context/search-context";
import { api, ApiError } from "../lib/api";
import type {
  AnalyticsBreakdownItem,
  AnalyticsFilterOptions,
  AnalyticsFrequencies,
  AnalyticsSeries,
  AnalyticsSummary,
  Page,
  Sale,
} from "../types";
import { formatDate, initials, money } from "../utils/format";

// -----------------------------------------------------------
// Configuración de periodos
// -----------------------------------------------------------
const PERIODS: Record<
  string,
  { days?: number; months?: number; granularity: "day" | "week" | "month" }
> = {
  "7 días": { days: 7, granularity: "day" },
  "30 días": { days: 30, granularity: "day" },
  "90 días": { days: 90, granularity: "week" },
  "12 meses": { months: 12, granularity: "month" },
};

const CATEGORY_COLORS = [
  "#2563eb",
  "#06b6d4",
  "#818cf8",
  "#34d399",
  "#fbbf24",
  "#cbd5e1",
];

const STATUS_LABELS: Record<string, string> = {
  draft: "Borrador",
  pending: "Pendiente",
  completed: "Completada",
  cancelled: "Cancelada",
  refunded: "Reembolsada",
};

const EMPTY_STATISTICS = {
  count: 0,
  mean: null,
  median: null,
  min: null,
  max: null,
  stddev: null,
};

function toISODate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function periodRange(period: string) {
  const config = PERIODS[period] ?? PERIODS["30 días"];
  const end = new Date();
  const start = new Date();

  if (config.months) {
    start.setMonth(start.getMonth() - config.months);
    start.setDate(start.getDate() + 1);
  } else {
    start.setDate(start.getDate() - ((config.days ?? 30) - 1));
  }

  return {
    date_from: toISODate(start),
    date_to: toISODate(end),
    granularity: config.granularity,
  };
}

/** "2026-10-12" → "10-12"; "2026-10" → "10" (etiqueta compacta del eje). */
function bucketLabel(bucket: string): string {
  return bucket.slice(5);
}

function changeInfo(
  current: number,
  previous: number | null | undefined,
): { text: string; trend?: "up" | "down" } {
  if (previous === null || previous === undefined) {
    return { text: "Sin periodo anterior" };
  }
  if (previous === 0) {
    return current > 0
      ? { text: "Sin base de comparación", trend: "up" }
      : { text: "Sin ventas en el periodo" };
  }

  const pct = ((current - previous) / previous) * 100;
  const formatted = pct.toLocaleString("es-PE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return {
    text: `${pct > 0 ? "+" : ""}${formatted}% vs. periodo anterior`,
    trend: pct < 0 ? "down" : "up",
  };
}

function moneyOrDash(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : money(value);
}

function compactNumber(value: number): string {
  return value.toLocaleString("es-PE", { maximumFractionDigits: 0 });
}

// -----------------------------------------------------------
// Página
// -----------------------------------------------------------
export default function DashboardPage() {
  const navigate = useNavigate();
  const { search, setSearch } = useSearch();

  const [period, setPeriod] = useState("30 días");
  const [sellerId, setSellerId] = useState("");
  const [categoryId, setCategoryId] = useState("");

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [series, setSeries] = useState<AnalyticsSeries | null>(null);
  const [byProduct, setByProduct] = useState<AnalyticsBreakdownItem[]>([]);
  const [byCategory, setByCategory] = useState<AnalyticsBreakdownItem[]>([]);
  const [bySeller, setBySeller] = useState<AnalyticsBreakdownItem[]>([]);
  const [frequencies, setFrequencies] =
    useState<AnalyticsFrequencies | null>(null);
  const [options, setOptions] = useState<AnalyticsFilterOptions | null>(null);
  const [recentSales, setRecentSales] = useState<Sale[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const range = useMemo(() => periodRange(period), [period]);

  // -----------------------------------------------------------
  // Cargas de datos
  // -----------------------------------------------------------
  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    const query = {
      date_from: range.date_from,
      date_to: range.date_to,
      seller_id: sellerId ? Number(sellerId) : undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
    };

    try {
      const [
        nextSummary,
        nextSeries,
        nextProducts,
        nextCategories,
        nextSellers,
        nextFrequencies,
      ] = await Promise.all([
        api.get<AnalyticsSummary>("/analytics/summary", { query }),
        api.get<AnalyticsSeries>("/analytics/series", {
          query: { ...query, granularity: range.granularity },
        }),
        api.get<{ items: AnalyticsBreakdownItem[] }>("/analytics/breakdown", {
          query: { ...query, group_by: "product", limit: 5 },
        }),
        api.get<{ items: AnalyticsBreakdownItem[] }>("/analytics/breakdown", {
          query: { ...query, group_by: "category", limit: 6 },
        }),
        api.get<{ items: AnalyticsBreakdownItem[] }>("/analytics/breakdown", {
          query: { ...query, group_by: "seller", limit: 6 },
        }),
        api.get<AnalyticsFrequencies>("/analytics/frequencies", { query }),
      ]);

      setSummary(nextSummary);
      setSeries(nextSeries);
      setByProduct(
        Array.isArray(nextProducts?.items) ? nextProducts.items : [],
      );
      setByCategory(
        Array.isArray(nextCategories?.items) ? nextCategories.items : [],
      );
      setBySeller(Array.isArray(nextSellers?.items) ? nextSellers.items : []);
      setFrequencies(nextFrequencies);
    } catch (caught) {
      setSummary(null);
      setSeries(null);
      setFrequencies(null);
      setByProduct([]);
      setByCategory([]);
      setBySeller([]);
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo cargar el dashboard.",
      );
    } finally {
      setLoading(false);
    }
  }, [range, sellerId, categoryId]);

  const loadOptions = useCallback(async () => {
    try {
      setOptions(await api.get<AnalyticsFilterOptions>("/analytics/filters"));
    } catch {
      setOptions(null);
    }
  }, []);

  const loadRecentSales = useCallback(async () => {
    try {
      const result = await api.get<Page<Sale>>("/sales", {
        query: {
          search: search.trim() || undefined,
          page: 1,
          page_size: 5,
        },
      });
      setRecentSales(Array.isArray(result?.items) ? result.items : []);
    } catch {
      setRecentSales([]);
    }
  }, [search]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadDashboard(), 0);
    return () => window.clearTimeout(timer);
  }, [loadDashboard]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadOptions(), 0);
    return () => window.clearTimeout(timer);
  }, [loadOptions]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadRecentSales(), 250);
    return () => window.clearTimeout(timer);
  }, [loadRecentSales]);

  // -----------------------------------------------------------
  // Datos derivados
  // -----------------------------------------------------------
  const kpis = summary?.kpis ?? {
    revenue: 0,
    sales_count: 0,
    avg_ticket: 0,
    customers_count: 0,
    items_sold: 0,
  };
  const statistics = summary?.statistics ?? EMPTY_STATISTICS;
  const previous = summary?.previous_period ?? null;

  const revenueChange = changeInfo(kpis.revenue, previous?.revenue);
  const salesChange = changeInfo(kpis.sales_count, previous?.sales_count);

  const sellerOptions = Array.isArray(options?.sellers) ? options.sellers : [];
  const categoryOptions = Array.isArray(options?.categories)
    ? options.categories
    : [];

  const seriesItems = Array.isArray(series?.items) ? series.items : [];
  const revenuePoints = seriesItems.map((point) => ({
    label: bucketLabel(point.bucket),
    sales: point.revenue,
  }));

  const categoryTotal = byCategory.reduce(
    (sum, item) => sum + item.revenue,
    0,
  );
  const categoryData = byCategory.map((item, index) => ({
    name: item.label,
    revenue: item.revenue,
    share:
      categoryTotal > 0
        ? Math.round((item.revenue / categoryTotal) * 100)
        : 0,
    color: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
  }));
  const leadingCategory = categoryData[0];

  const productPoints = byProduct.map((item) => ({
    name: item.label,
    revenue: item.revenue,
  }));
  const sellerPoints = bySeller.map((item) => ({
    name: item.label,
    revenue: item.revenue,
  }));

  const frequencyBins = Array.isArray(frequencies?.bins)
    ? frequencies.bins
    : [];
  const histogramPoints = frequencyBins.map((bin) => ({
    range: `${compactNumber(bin.bin_start)}–${compactNumber(bin.bin_end)}`,
    frequency: bin.frequency,
  }));

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            PANEL DE CONTROL
          </div>
          <h1>Dashboard ejecutivo</h1>
          <p>
            Conoce el estado de tu negocio y explora tus indicadores
            comerciales.
          </p>
        </div>
        <div className="heading-actions">
          <button
            className="button-secondary"
            onClick={() => window.print()}
          >
            <Download size={16} />
            <span>Exportar</span>
          </button>
          <button
            className="button-primary"
            onClick={() => navigate("/ventas")}
          >
            <Plus size={17} />
            Nueva venta
          </button>
        </div>
      </section>

      <section className="welcome-banner">
        <div className="welcome-copy">
          <div className="welcome-label">
            <Zap size={14} /> VISIÓN GENERAL
          </div>
          <h2>Los datos cuentan una historia.</h2>
          <p>
            Tus KPIs, gráficos y distribuciones se calculan en vivo sobre las
            ventas registradas en el sistema.
          </p>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <div className="art-ring ring-one" />
          <div className="art-ring ring-two" />
          <div className="art-center">
            <ChartNoAxesCombined size={42} />
          </div>
          <span className="art-dot dot-one" />
          <span className="art-dot dot-two" />
          <span className="art-dot dot-three" />
        </div>
      </section>

      <section className="section-heading">
        <div>
          <h2>Resumen comercial</h2>
          <p>Indicadores principales del periodo seleccionado</p>
        </div>
        <div className="dashboard-filters">
          <label className="period-select">
            <CalendarDays size={16} />
            <select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              aria-label="Periodo de los indicadores"
            >
              {Object.keys(PERIODS).map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
            <ChevronDown size={15} />
          </label>
          <label className="period-select">
            <Users size={16} />
            <select
              value={sellerId}
              onChange={(event) => setSellerId(event.target.value)}
              aria-label="Vendedor"
            >
              <option value="">Todos los vendedores</option>
              {sellerOptions.map((seller) => (
                <option key={seller.id} value={seller.id}>
                  {seller.name}
                </option>
              ))}
            </select>
            <ChevronDown size={15} />
          </label>
          <label className="period-select">
            <Filter size={16} />
            <select
              value={categoryId}
              onChange={(event) => setCategoryId(event.target.value)}
              aria-label="Categoría"
            >
              <option value="">Todas las categorías</option>
              {categoryOptions.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            <ChevronDown size={15} />
          </label>
        </div>
      </section>

      {error && (
        <div className="form-alert" role="alert">
          <strong>No se pudo cargar el dashboard:</strong> {error}
        </div>
      )}

      <section className="metrics-grid">
        <MetricCard
          title="Ingresos por ventas"
          value={summary ? money(kpis.revenue) : "—"}
          change={revenueChange.text}
          trend={revenueChange.trend}
          icon={<CreditCard size={19} />}
          color="blue"
          description="Importe registrado en ventas"
        />
        <MetricCard
          title="Ventas registradas"
          value={summary ? String(kpis.sales_count) : "—"}
          change={salesChange.text}
          trend={salesChange.trend}
          icon={<ShoppingCart size={19} />}
          color="cyan"
          description="Transacciones en el periodo"
        />
        <MetricCard
          title="Clientes"
          value={summary ? String(kpis.customers_count) : "—"}
          change="Periodo seleccionado"
          icon={<Users size={19} />}
          color="violet"
          description="Clientes con compras"
        />
        <MetricCard
          title="Ticket promedio"
          value={summary ? money(kpis.avg_ticket) : "—"}
          change="Promedio por venta"
          icon={<Target size={19} />}
          color="orange"
          description="Importe medio por transacción"
        />
      </section>

      {!loading && !error && summary && kpis.sales_count === 0 && (
        <div className="demo-notice">
          <Activity size={17} />
          <span>
            <strong>Sin ventas:</strong> no hay ventas en el periodo
            seleccionado (ni con los filtros aplicados). Registra una venta o
            cambia el periodo.
          </span>
        </div>
      )}

      <section className="analytics-grid">
        <article className="panel revenue-panel">
          <div className="panel-header">
            <div>
              <h3>Evolución de ingresos</h3>
              <p>Ingresos registrados · valores en soles</p>
            </div>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-dot legend-current" /> Ingresos del periodo
            </span>
          </div>
          {revenuePoints.length > 0 ? (
            <div className="revenue-chart">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                  data={revenuePoints}
                  margin={{ top: 12, right: 4, left: -15, bottom: 0 }}
                >
                  <defs>
                    <linearGradient
                      id="salesGradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="#2563eb"
                        stopOpacity={0.2}
                      />
                      <stop
                        offset="95%"
                        stopColor="#2563eb"
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke="#edf0f5"
                    vertical={false}
                    strokeDasharray="4 4"
                  />
                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8994a7", fontSize: 11 }}
                    dy={10}
                    minTickGap={22}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8994a7", fontSize: 11 }}
                    tickFormatter={(value: number) =>
                      value === 0 ? "0" : `${value / 1000}k`
                    }
                  />
                  <Tooltip
                    formatter={(value) => money(Number(value))}
                    contentStyle={{
                      border: "1px solid #e8edf5",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="sales"
                    stroke="#2563eb"
                    strokeWidth={2.5}
                    fill="url(#salesGradient)"
                    name="Ingresos"
                    activeDot={{ r: 5, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="no-results">
              Sin ventas en el periodo seleccionado.
            </p>
          )}
          <div className="chart-footnote">
            <span className="footnote-dot" />
            Los periodos sin ventas se muestran en cero · moneda: PEN (S/).
          </div>
        </article>

        <article className="panel category-panel">
          <div className="panel-header">
            <div>
              <h3>Ventas por categoría</h3>
              <p>Reparto de ingresos por categoría</p>
            </div>
            <button
              className="icon-button panel-menu"
              aria-label="Ver productos"
              onClick={() => navigate("/productos")}
            >
              <ArrowRight size={17} />
            </button>
          </div>
          {categoryData.length > 0 ? (
            <>
              <div className="donut-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={categoryData}
                      dataKey="revenue"
                      nameKey="name"
                      innerRadius="66%"
                      outerRadius="88%"
                      paddingAngle={4}
                      stroke="none"
                    >
                      {categoryData.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => money(Number(value))} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="donut-center">
                  <strong>{leadingCategory?.share ?? 0}%</strong>
                  <span>Categoría líder</span>
                </div>
              </div>
              <div className="category-legend">
                {categoryData.map((category) => (
                  <div className="category-row" key={category.name}>
                    <span className="category-name">
                      <i style={{ background: category.color }} />
                      {category.name}
                    </span>
                    <strong>{category.share}%</strong>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="no-results">Sin ventas por categoría.</p>
          )}
        </article>
      </section>

      <section className="dashboard-secondary">
        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Ventas por producto</h3>
              <p>Top ingresos por producto</p>
            </div>
          </div>
          {productPoints.length > 0 ? (
            <div className="revenue-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={productPoints}
                  margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
                >
                  <CartesianGrid
                    stroke="#edf0f5"
                    horizontal={false}
                    vertical={false}
                    strokeDasharray="4 4"
                  />
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={118}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8994a7", fontSize: 10 }}
                  />
                  <Tooltip
                    formatter={(value) => money(Number(value))}
                    contentStyle={{
                      border: "1px solid #e8edf5",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Bar
                    dataKey="revenue"
                    fill="#2563eb"
                    radius={[0, 6, 6, 0]}
                    barSize={14}
                    name="Ingresos"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="no-results">Sin ventas por producto.</p>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Ventas por vendedor</h3>
              <p>Ingresos por usuario que registró</p>
            </div>
          </div>
          {sellerPoints.length > 0 ? (
            <div className="revenue-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={sellerPoints}
                  margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
                >
                  <CartesianGrid
                    stroke="#edf0f5"
                    horizontal={false}
                    vertical={false}
                    strokeDasharray="4 4"
                  />
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={118}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8994a7", fontSize: 10 }}
                  />
                  <Tooltip
                    formatter={(value) => money(Number(value))}
                    contentStyle={{
                      border: "1px solid #e8edf5",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Bar
                    dataKey="revenue"
                    fill="#06b6d4"
                    radius={[0, 6, 6, 0]}
                    barSize={14}
                    name="Ingresos"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="no-results">Sin ventas por vendedor.</p>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <h3>Distribución de montos</h3>
              <p>Frecuencia de los importes de venta</p>
            </div>
          </div>
          {histogramPoints.length > 0 ? (
            <div className="revenue-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={histogramPoints}
                  margin={{ top: 10, right: 4, left: -20, bottom: 0 }}
                >
                  <CartesianGrid
                    stroke="#edf0f5"
                    vertical={false}
                    strokeDasharray="4 4"
                  />
                  <XAxis
                    dataKey="range"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8994a7", fontSize: 9 }}
                    interval={0}
                  />
                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8994a7", fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(value) => `${value} ventas`}
                    labelFormatter={(label) => `Montos S/ ${label}`}
                    contentStyle={{
                      border: "1px solid #e8edf5",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                  />
                  <Bar
                    dataKey="frequency"
                    fill="#818cf8"
                    radius={[6, 6, 0, 0]}
                    barSize={26}
                    name="Ventas"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="no-results">Sin montos que distribuir.</p>
          )}
          <div className="chart-footnote">
            <span className="footnote-dot" />
            Media: {moneyOrDash(statistics.mean)} · Mediana:{" "}
            {moneyOrDash(statistics.median)}
          </div>
        </article>
      </section>

      <section className="panel stats-panel">
        <div className="panel-header">
          <div>
            <h3>Media y mediana del periodo</h3>
            <p>Estadística descriptiva de los importes de venta</p>
          </div>
        </div>
        <div className="stats-grid">
          <div className="stat-item">
            <span>Ventas analizadas</span>
            <strong>{statistics.count}</strong>
          </div>
          <div className="stat-item">
            <span>Unidades vendidas</span>
            <strong>{kpis.items_sold}</strong>
          </div>
          <div className="stat-item">
            <span>Media</span>
            <strong>{moneyOrDash(statistics.mean)}</strong>
          </div>
          <div className="stat-item">
            <span>Mediana</span>
            <strong>{moneyOrDash(statistics.median)}</strong>
          </div>
          <div className="stat-item">
            <span>Mínimo</span>
            <strong>{moneyOrDash(statistics.min)}</strong>
          </div>
          <div className="stat-item">
            <span>Máximo</span>
            <strong>{moneyOrDash(statistics.max)}</strong>
          </div>
          <div className="stat-item">
            <span>Desviación típica</span>
            <strong>{moneyOrDash(statistics.stddev)}</strong>
          </div>
        </div>
      </section>

      <section className="panel transactions-panel">
        <div className="panel-header transaction-heading">
          <div>
            <h3>Actividad comercial</h3>
            <p>Últimas ventas registradas en el sistema</p>
          </div>
          <button
            className="text-button"
            onClick={() => navigate("/ventas")}
          >
            Ver módulo de ventas <ArrowRight size={15} />
          </button>
        </div>
        <div className="table-scroll">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>CLIENTE</th>
                <th>N° VENTA</th>
                <th>FECHA</th>
                <th>IMPORTE</th>
                <th>ESTADO</th>
              </tr>
            </thead>
            <tbody>
              {recentSales.map((sale) => {
                const label = STATUS_LABELS[sale.status] ?? sale.status;
                return (
                  <tr key={sale.id}>
                    <td>
                      <div className="customer-cell">
                        <div className="customer-avatar avatar-blue">
                          {sale.customer_name
                            ? initials(sale.customer_name)
                            : "SC"}
                        </div>
                        <div className="customer-copy">
                          <strong>{sale.customer_name ?? "Sin cliente"}</strong>
                          <span>{sale.currency}</span>
                        </div>
                      </div>
                    </td>
                    <td>{sale.sale_number}</td>
                    <td className="date-cell">{formatDate(sale.sold_at)}</td>
                    <td className="amount-cell">
                      {money(sale.total_amount)}
                    </td>
                    <td>
                      <span
                        className={`status status-${label.toLowerCase()}`}
                      >
                        <i />
                        {label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {recentSales.length === 0 && (
            <p className="no-results">
              {search
                ? `No se encontraron coincidencias para "${search}".`
                : "Todavía no hay ventas registradas."}
            </p>
          )}
        </div>
        <div className="table-footer">
          <span>
            {recentSales.length} de las ventas más recientes
            {search ? ` · búsqueda: "${search}"` : ""}
          </span>
          <button className="text-button" onClick={() => setSearch("")}>
            Limpiar búsqueda
          </button>
        </div>
      </section>

      <section className="insight-banner">
        <div className="insight-icon">
          <Sparkles size={21} />
        </div>
        <div>
          <span className="insight-kicker">MÓDULO ANALYTICS · EN VIVO</span>
          <h3>De los registros a los insights</h3>
          <p>
            Media, mediana, distribuciones y probabilidades calculadas sobre
            las operaciones guardadas en el sistema.
          </p>
        </div>
        <button
          className="button-secondary insight-button"
          onClick={() => navigate("/analytics")}
        >
          Explorar módulo <ArrowRight size={16} />
        </button>
      </section>
    </>
  );
}
