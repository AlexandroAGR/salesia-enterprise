import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronDown,
  CreditCard,
  Download,
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
import { money } from "../utils/format";

const revenueData = [
  { day: "01 Sep", sales: 8200, previous: 6100 },
  { day: "04 Sep", sales: 10500, previous: 7200 },
  { day: "07 Sep", sales: 9100, previous: 6800 },
  { day: "10 Sep", sales: 14200, previous: 9300 },
  { day: "13 Sep", sales: 11800, previous: 8400 },
  { day: "16 Sep", sales: 16500, previous: 10500 },
  { day: "19 Sep", sales: 13900, previous: 9600 },
  { day: "22 Sep", sales: 18800, previous: 12800 },
  { day: "25 Sep", sales: 15700, previous: 11100 },
  { day: "28 Sep", sales: 22100, previous: 14300 },
];

const categoryData = [
  { name: "Tecnología", value: 38, color: "#2563eb" },
  { name: "Accesorios", value: 27, color: "#06b6d4" },
  { name: "Oficina", value: 20, color: "#818cf8" },
  { name: "Otros", value: 15, color: "#cbd5e1" },
];

const transactions = [
  {
    name: "María Fernanda",
    initials: "MF",
    email: "maria.fernanda@example.com",
    product: "Laptop empresarial",
    date: "30 sep, 09:42",
    amount: 3299,
    status: "Completada",
    color: "blue",
  },
  {
    name: "Carlos Mendoza",
    initials: "CM",
    email: "carlos.m@example.com",
    product: "Monitor 27 pulgadas",
    date: "30 sep, 09:18",
    amount: 899,
    status: "Pendiente",
    color: "violet",
  },
  {
    name: "Lucía Ramírez",
    initials: "LR",
    email: "lucia.r@example.com",
    product: "Teclado mecánico",
    date: "30 sep, 08:56",
    amount: 249,
    status: "Completada",
    color: "cyan",
  },
  {
    name: "Diego Torres",
    initials: "DT",
    email: "diego.t@example.com",
    product: "Mouse inalámbrico",
    date: "29 sep, 17:31",
    amount: 129,
    status: "Cancelada",
    color: "orange",
  },
];

export default function DashboardPage() {
  const navigate = useNavigate();
  const { search, setSearch } = useSearch();
  const [period, setPeriod] = useState("30 días");

  const filteredTransactions = transactions.filter((item) =>
    `${item.name} ${item.product} ${item.email}`
      .toLowerCase()
      .includes(search.toLowerCase()),
  );

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
            Conecta tus operaciones y descubre qué sucede en tu negocio a
            través de la analítica comercial.
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
        <label className="period-select">
          <CalendarDays size={16} />
          <select
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            aria-label="Periodo de los indicadores"
          >
            <option>7 días</option>
            <option>30 días</option>
            <option>90 días</option>
            <option>12 meses</option>
          </select>
          <ChevronDown size={15} />
        </label>
      </section>

      <section className="metrics-grid">
        <MetricCard
          title="Ingresos por ventas"
          value={money(0)}
          change="Sin datos"
          icon={<CreditCard size={19} />}
          color="blue"
          description="Importe registrado en ventas"
        />
        <MetricCard
          title="Ventas registradas"
          value="0"
          change="Sin datos"
          icon={<ShoppingCart size={19} />}
          color="cyan"
          description="Transacciones registradas"
        />
        <MetricCard
          title="Clientes"
          value="0"
          change="Sin datos"
          icon={<Users size={19} />}
          color="violet"
          description="Clientes registrados"
        />
        <MetricCard
          title="Ticket promedio"
          value={money(0)}
          change="Sin datos"
          icon={<Target size={19} />}
          color="orange"
          description="Promedio por transacción"
        />
      </section>

      <div className="demo-notice">
        <Activity size={17} />
        <span>
          <strong>Vista inicial:</strong> los indicadores se muestran en cero
          hasta conectar la base de datos y registrar ventas. Los gráficos
          siguientes son datos ilustrativos de diseño.
        </span>
      </div>

      <section className="analytics-grid">
        <article className="panel revenue-panel">
          <div className="panel-header">
            <div>
              <h3>Evolución de ingresos</h3>
              <p>Ejemplo visual · valores en soles</p>
            </div>
            <button
              className="icon-button panel-menu"
              aria-label="Opciones del gráfico"
              onClick={() =>
                alert("El gráfico usará datos reales al integrar la API.")
              }
            >
              <Download size={17} />
            </button>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-dot legend-current" /> Periodo actual
            </span>
            <span>
              <i className="legend-dot legend-previous" /> Periodo anterior
            </span>
          </div>
          <div className="revenue-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={revenueData}
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
                  dataKey="day"
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
                  dataKey="previous"
                  stroke="#a5b4fc"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  fill="transparent"
                  name="Periodo anterior"
                />
                <Area
                  type="monotone"
                  dataKey="sales"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  fill="url(#salesGradient)"
                  name="Periodo actual"
                  activeDot={{ r: 5, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footnote">
            <span className="footnote-dot" />
            Datos ilustrativos, no corresponden a transacciones reales.
          </div>
        </article>

        <article className="panel category-panel">
          <div className="panel-header">
            <div>
              <h3>Ventas por categoría</h3>
              <p>Distribución ilustrativa</p>
            </div>
            <button
              className="icon-button panel-menu"
              aria-label="Ver productos"
              onClick={() => navigate("/productos")}
            >
              <ArrowRight size={17} />
            </button>
          </div>
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  dataKey="value"
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
                <Tooltip formatter={(value) => `${value}%`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-center">
              <strong>100%</strong>
              <span>Ejemplo</span>
            </div>
          </div>
          <div className="category-legend">
            {categoryData.map((category) => (
              <div className="category-row" key={category.name}>
                <span className="category-name">
                  <i style={{ background: category.color }} />
                  {category.name}
                </span>
                <strong>{category.value}%</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel transactions-panel">
        <div className="panel-header transaction-heading">
          <div>
            <h3>Actividad comercial</h3>
            <p>Ejemplo de presentación de transacciones</p>
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
                <th>PRODUCTO</th>
                <th>FECHA</th>
                <th>IMPORTE</th>
                <th>ESTADO</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.map((item) => (
                <tr key={item.email}>
                  <td>
                    <div className="customer-cell">
                      <div
                        className={`customer-avatar avatar-${item.color}`}
                      >
                        {item.initials}
                      </div>
                      <div className="customer-copy">
                        <strong>{item.name}</strong>
                        <span>{item.email}</span>
                      </div>
                    </div>
                  </td>
                  <td>{item.product}</td>
                  <td className="date-cell">{item.date}</td>
                  <td className="amount-cell">{money(item.amount)}</td>
                  <td>
                    <span
                      className={`status status-${item.status.toLowerCase()}`}
                    >
                      <i />
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredTransactions.length === 0 && (
            <p className="no-results">
              No se encontraron coincidencias para "{search}".
            </p>
          )}
        </div>
        <div className="table-footer">
          <span>4 filas ilustrativas · Sin conexión a la base de datos</span>
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
          <span className="insight-kicker">PRÓXIMAMENTE · ANALYTICS</span>
          <h3>De los registros a los insights</h3>
          <p>
            Analizaremos media, mediana, distribuciones y probabilidades
            sobre las operaciones guardadas en PostgreSQL.
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
