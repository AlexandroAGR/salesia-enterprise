import type { ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import {
  Boxes,
  ChartNoAxesCombined,
  CircleHelp,
  Command,
  CreditCard,
  FileBarChart,
  Lightbulb,
  Loader2,
  Settings,
  ShoppingCart,
} from "lucide-react";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/auth-context";
import AppLayout, { ModulePlaceholder } from "./layouts/AppLayout";
import CustomersPage from "./pages/CustomersPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import ProductsPage from "./pages/ProductsPage";
import "./index.css";

function FullScreenLoader({ label }: { label: string }) {
  return (
    <div className="full-screen-loader" role="status">
      <Loader2 size={26} className="spin" />
      <span>{label}</span>
    </div>
  );
}

function ProtectedLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <FullScreenLoader label="Cargando sesión..." />;
  }

  if (!user) {
    return (
      <Navigate to="/login" state={{ from: location.pathname }} replace />
    );
  }

  return <AppLayout />;
}

function LoginRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <FullScreenLoader label="Cargando sesión..." />;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              <LoginRoute>
                <LoginPage />
              </LoginRoute>
            }
          />

          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/clientes" element={<CustomersPage />} />
            <Route path="/productos" element={<ProductsPage />} />

            <Route
              path="/analytics"
              element={
                <ModulePlaceholder
                  title="Analytics"
                  icon={<ChartNoAxesCombined size={29} />}
                  description="KPIs, ventas por periodo, producto y vendedor, ticket promedio, media y mediana con filtros por periodo, sucursal, vendedor y categoría."
                />
              }
            />
            <Route
              path="/insights"
              element={
                <ModulePlaceholder
                  title="Insights"
                  icon={<Lightbulb size={29} />}
                  description="Observaciones generadas a partir de reglas estadísticas, con evidencia numérica y vínculo al análisis que las origina."
                />
              }
            />
            <Route
              path="/ventas"
              element={
                <ModulePlaceholder
                  title="Ventas"
                  icon={<ShoppingCart size={29} />}
                  description="Registro de ventas con detalle, descuentos, impuestos, pagos y actualización automática de inventario."
                />
              }
            />
            <Route
              path="/pedidos"
              element={
                <ModulePlaceholder
                  title="Pedidos"
                  icon={<FileBarChart size={29} />}
                  description="Gestión de pedidos y su seguimiento hasta convertirse en venta."
                />
              }
            />
            <Route
              path="/inventario"
              element={
                <ModulePlaceholder
                  title="Inventario"
                  icon={<Boxes size={29} />}
                  description="Existencias por producto, entradas, salidas y trazabilidad de movimientos."
                />
              }
            />
            <Route
              path="/pagos"
              element={
                <ModulePlaceholder
                  title="Pagos"
                  icon={<CreditCard size={29} />}
                  description="Registro de pagos, métodos de pago y conciliación con cada venta."
                />
              }
            />
            <Route
              path="/reportes"
              element={
                <ModulePlaceholder
                  title="Reportes"
                  icon={<FileBarChart size={29} />}
                  description="Reportes comerciales y estadísticos con exportación y vista imprimible."
                />
              }
            />
            <Route
              path="/configuracion"
              element={
                <ModulePlaceholder
                  title="Configuración"
                  icon={<Settings size={29} />}
                  description="Usuarios, roles, parámetros fiscales y preferencias del sistema."
                />
              }
            />
            <Route
              path="/ayuda"
              element={
                <ModulePlaceholder
                  title="Centro de ayuda"
                  icon={<CircleHelp size={29} />}
                  description="Guía de uso del sistema, preguntas frecuentes y contactos de soporte."
                />
              }
            />

            <Route
              path="*"
              element={
                <ModulePlaceholder
                  title="Módulo no encontrado"
                  icon={<Command size={29} />}
                  description="La ruta solicitada no existe en SalesIA Enterprise."
                />
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
