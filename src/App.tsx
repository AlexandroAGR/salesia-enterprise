
import { useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Boxes,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  Command,
  CreditCard,
  Download,
  FileBarChart,
  LayoutDashboard,
  Lightbulb,
  Menu,
  Package,
  Plus,
  Search,
  Settings,
  ShoppingCart,
  Sparkles,
  Target,
  Users,
  X,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import "./index.css";

const navigation = [
  {
    title: "GENERAL",
    items: [
      { label: "Dashboard", icon: LayoutDashboard },
      { label: "Analytics", icon: ChartNoAxesCombined },
      { label: "Insights", icon: Lightbulb },
    ],
  },
  {
    title: "GESTIÓN COMERCIAL",
    items: [
      { label: "Ventas", icon: ShoppingCart },
      { label: "Pedidos", icon: FileBarChart },
      { label: "Clientes", icon: Users },
      { label: "Productos", icon: Package },
      { label: "Inventario", icon: Boxes },
      { label: "Pagos", icon: CreditCard },
    ],
  },
  {
    title: "SISTEMA",
    items: [
      { label: "Reportes", icon: FileBarChart },
      { label: "Configuración", icon: Settings },
    ],
  },
];

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

const money = (value: number) =>
  new Intl.NumberFormat("es-PE", {
    style: "currency",
    currency: "PEN",
    maximumFractionDigits: 2,
  }).format(value);

function App() {
  const [activePage, setActivePage] = useState("Dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [period, setPeriod] = useState("30 días");
  const [search, setSearch] = useState("");

  const isDashboard = activePage === "Dashboard";

  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          className="mobile-overlay"
          aria-label="Cerrar menú"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <ChartNoAxesCombined size={23} strokeWidth={2.4} />
          </div>
          <div className="brand-copy">
            <span className="brand-name">SalesIA</span>
            <span className="brand-edition">ENTERPRISE</span>
          </div>
          <button
            className="icon-button sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Cerrar menú"
          >
            <X size={19} />
          </button>
        </div>

        <div className="workspace">
          <div className="workspace-avatar">AC</div>
          <div className="workspace-copy">
            <strong>Acme Corporation</strong>
            <span>Plan empresarial</span>
          </div>
          <ChevronDown size={16} className="muted-icon" />
        </div>

        <div className="nav-scroll">
          {navigation.map((group) => (
            <div className="nav-group" key={group.title}>
              <p className="nav-heading">{group.title}</p>
              {group.items.map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  className={`nav-link ${
                    activePage === label ? "nav-link-active" : ""
                  }`}
                  onClick={() => {
                    setActivePage(label);
                    setMobileOpen(false);
                  }}
                >
                  <Icon size={18} strokeWidth={1.8} />
                  <span>{label}</span>
                  {label === "Insights" && (
                    <span className="nav-count">3</span>
                  )}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="upgrade-card">
            <div className="upgrade-icon">
              <Sparkles size={17} />
            </div>
            <strong>Inteligencia comercial</strong>
            <p>Convierte tus datos en decisiones basadas en evidencia.</p>
            <button
              onClick={() => {
                setActivePage("Analytics");
                setMobileOpen(false);
              }}
            >
              Explorar Analytics <ArrowRight size={15} />
            </button>
          </div>
          <button
            className="nav-link help-link"
            onClick={() => setActivePage("Ayuda")}
          >
            <CircleHelp size={18} />
            <span>Centro de ayuda</span>
          </button>
          <div className="profile">
            <div className="profile-avatar">AG</div>
            <div className="profile-copy">
              <strong>Administrador</strong>
              <span>admin@salesia.local</span>
            </div>
            <button
              className="icon-button profile-settings"
              aria-label="Configuración del perfil"
              onClick={() => setActivePage("Configuración")}
            >
              <Settings size={17} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu-button"
              onClick={() => setMobileOpen(true)}
              aria-label="Abrir menú"
            >
              <Menu size={21} />
            </button>
            <div className="breadcrumb">
              <span>Workspace</span>
              <span className="breadcrumb-separator">/</span>
              <strong>{activePage}</strong>
            </div>
          </div>

          <div className="topbar-actions">
            <label className="search-box">
              <Search size={17} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar..."
                aria-label="Buscar en el panel"
              />
              <kbd>⌘ K</kbd>
            </label>
            <button
              className="icon-button notification-button"
              aria-label="Notificaciones"
              onClick={() => alert("Las notificaciones se conectarán al backend.")}
            >
              <Bell size={19} />
              <span className="notification-dot" />
            </button>
            <div className="topbar-avatar">AG</div>
          </div>
        </header>

        <div className="page-content">
          {isDashboard ? (
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
                    onClick={() => setActivePage("Ventas")}
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
                    Conecta tus operaciones y descubre qué sucede en tu
                    negocio a través de la analítica comercial.
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
                  <strong>Vista inicial:</strong> los indicadores se muestran
                  en cero hasta conectar la base de datos y registrar ventas.
                  Los gráficos siguientes son datos ilustrativos de diseño.
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
                    <span><i className="legend-dot legend-current" /> Periodo actual</span>
                    <span><i className="legend-dot legend-previous" /> Periodo anterior</span>
                  </div>
                  <div className="revenue-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={revenueData}
                        margin={{ top: 12, right: 4, left: -15, bottom: 0 }}
                      >
                        <defs>
                          <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#2563eb" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
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
                      onClick={() => setActivePage("Productos")}
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
                    onClick={() => setActivePage("Ventas")}
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
                      {transactions
                        .filter((item) =>
                          `${item.name} ${item.product} ${item.email}`
                            .toLowerCase()
                            .includes(search.toLowerCase())
                        )
                        .map((item) => (
                          <tr key={item.email}>
                            <td>
                              <div className="customer-cell">
                                <div className={`customer-avatar avatar-${item.color}`}>
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
                  {transactions.filter((item) =>
                    `${item.name} ${item.product} ${item.email}`
                      .toLowerCase()
                      .includes(search.toLowerCase())
                  ).length === 0 && (
                    <p className="no-results">
                      No se encontraron coincidencias para "{search}".
                    </p>
                  )}
                </div>
                <div className="table-footer">
                  <span>4 filas ilustrativas · Sin conexión a la base de datos</span>
                  <button
                    className="text-button"
                    onClick={() => setSearch("")}
                  >
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
                  onClick={() => setActivePage("Analytics")}
                >
                  Explorar módulo <ArrowRight size={16} />
                </button>
              </section>
            </>
          ) : (
            <section className="module-placeholder">
              <div className="placeholder-icon">
                {activePage === "Analytics" ? (
                  <ChartNoAxesCombined size={29} />
                ) : activePage === "Clientes" ? (
                  <Users size={29} />
                ) : activePage === "Productos" ? (
                  <Package size={29} />
                ) : activePage === "Ventas" ? (
                  <ShoppingCart size={29} />
                ) : (
                  <Command size={29} />
                )}
              </div>
              <span className="eyebrow">SALESIA ENTERPRISE</span>
              <h1>{activePage}</h1>
              <p>
                Este módulo forma parte del sistema. Lo implementaremos en su
                fase correspondiente y lo conectaremos con FastAPI y PostgreSQL.
              </p>
              <div className="placeholder-note">
                <Activity size={17} />
                <span>La estructura de navegación ya está preparada.</span>
              </div>
              <button
                className="button-primary"
                onClick={() => setActivePage("Dashboard")}
              >
                <ArrowRight size={16} className="back-arrow" />
                Volver al dashboard
              </button>
            </section>
          )}

          <footer className="app-footer">
            <span>© 2026 SalesIA Enterprise</span>
            <span className="footer-status">
              <i /> Entorno de desarrollo
            </span>
            <span>React · TypeScript · FastAPI · PostgreSQL</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

type MetricCardProps = {
  title: string;
  value: string;
  change: string;
  icon: React.ReactNode;
  color: string;
  description: string;
};

function MetricCard({
  title,
  value,
  change,
  icon,
  color,
  description,
}: MetricCardProps) {
  const TrendIcon = color === "orange" ? ArrowDownRight : ArrowUpRight;

  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className={`metric-icon metric-${color}`}>{icon}</span>
        <span className="metric-period">Este periodo</span>
      </div>
      <p className="metric-title">{title}</p>
      <div className="metric-value-row">
        <strong>{value}</strong>
      </div>
      <div className="metric-bottom">
        <span className="metric-change">
          <TrendIcon size={14} />
          {change}
        </span>
        <span className="metric-description">{description}</span>
      </div>
    </article>
  );
}

export default App;