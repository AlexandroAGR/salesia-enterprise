import type { ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import {
  CircleHelp,
  Command,
  FileBarChart,
  Loader2,
  Lock,
  Settings,
} from "lucide-react";
import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/auth-context";
import AppLayout, { ModulePlaceholder } from "./layouts/AppLayout";
import { canAccess, type ModuleKey } from "./permissions";
import AnalyticsPage from "./pages/AnalyticsPage";
import CustomersPage from "./pages/CustomersPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import ProductsPage from "./pages/ProductsPage";
import "./index.css";
import InventoryPage from "./pages/InventoryPage";
import InsightsPage from "./pages/InsightsPage";
import PaymentsPage from "./pages/PaymentsPage";
import ReportsPage from "./pages/ReportsPage";
import SalesPage from "./pages/SalesPage";

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

function ModuleGuard({
  module,
  children,
}: {
  module: ModuleKey;
  children: ReactNode;
}) {
  const { user } = useAuth();

  if (!canAccess(user?.role, module)) {
    return (
      <ModulePlaceholder
        title="Acceso restringido"
        icon={<Lock size={29} />}
        description="Tu rol no tiene permisos para consultar este módulo. Si necesitas acceso, solicítalo al administrador del sistema."
      />
    );
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
            <Route
              path="/"
              element={
                <ModuleGuard module="dashboard">
                  <DashboardPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/clientes"
              element={
                <ModuleGuard module="clientes">
                  <CustomersPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/productos"
              element={
                <ModuleGuard module="productos">
                  <ProductsPage />
                </ModuleGuard>
              }
            />

            <Route
              path="/analytics"
              element={
                <ModuleGuard module="analytics">
                  <AnalyticsPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/insights"
              element={
                <ModuleGuard module="insights">
                  <InsightsPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/ventas"
              element={
                <ModuleGuard module="ventas">
                  <SalesPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/pedidos"
              element={
                <ModuleGuard module="pedidos">
                  <ModulePlaceholder
                    title="Pedidos"
                    icon={<FileBarChart size={29} />}
                    description="Gestión de pedidos y su seguimiento hasta convertirse en venta."
                  />
                </ModuleGuard>
              }
            />
            <Route
              path="/inventario"
              element={
                <ModuleGuard module="inventario">
                  <InventoryPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/pagos"
              element={
                <ModuleGuard module="pagos">
                  <PaymentsPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/reportes"
              element={
                <ModuleGuard module="reportes">
                  <ReportsPage />
                </ModuleGuard>
              }
            />
            <Route
              path="/configuracion"
              element={
                <ModuleGuard module="configuracion">
                  <ModulePlaceholder
                    title="Configuración"
                    icon={<Settings size={29} />}
                    description="Usuarios, roles, parámetros fiscales y preferencias del sistema."
                  />
                </ModuleGuard>
              }
            />
            <Route
              path="/ayuda"
              element={
                <ModuleGuard module="ayuda">
                  <ModulePlaceholder
                    title="Centro de ayuda"
                    icon={<CircleHelp size={29} />}
                    description="Guía de uso del sistema, preguntas frecuentes y contactos de soporte."
                  />
                </ModuleGuard>
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
