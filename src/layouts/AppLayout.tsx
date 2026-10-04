import { useState, type ReactNode } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import { SearchProvider } from "../context/SearchContext";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <SearchProvider>
      <div className="app-shell">
        {mobileOpen && (
          <button
            className="mobile-overlay"
            aria-label="Cerrar menú"
            onClick={() => setMobileOpen(false)}
          />
        )}

        <Sidebar open={mobileOpen} onClose={() => setMobileOpen(false)} />

        <main className="main-area">
          <Topbar onOpenMenu={() => setMobileOpen(true)} />

          <div className="page-content">
            <Outlet />

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
    </SearchProvider>
  );
}

type ModulePlaceholderProps = {
  title: string;
  icon: ReactNode;
  description?: string;
};

export function ModulePlaceholder({
  title,
  icon,
  description,
}: ModulePlaceholderProps) {
  return (
    <section className="module-placeholder">
      <div className="placeholder-icon">{icon}</div>
      <span className="eyebrow">SALESIA ENTERPRISE</span>
      <h1>{title}</h1>
      <p>
        {description ??
          "Este módulo forma parte del sistema. Lo implementaremos en su fase correspondiente y lo conectaremos con FastAPI y PostgreSQL."}
      </p>
      <div className="placeholder-note">
        <span>La estructura de navegación ya está preparada.</span>
      </div>
    </section>
  );
}
