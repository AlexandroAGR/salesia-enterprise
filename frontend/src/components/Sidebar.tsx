import { NavLink, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { useAuth } from "../context/auth-context";
import { navigation } from "../navigation";
import { canAccess, moduleForPath } from "../permissions";
import { initials } from "../utils/format";

type SidebarProps = {
  open: boolean;
  onClose: () => void;
};

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { user } = useAuth();
  const navigate = useNavigate();

  const displayName = user?.full_name ?? "Usuario";
  const displayEmail = user?.email ?? "";
  const avatar = initials(displayName) || "US";

  const groups = navigation
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => {
        const module = moduleForPath(item.path);
        return module === null || canAccess(user?.role, module);
      }),
    }))
    .filter((group) => group.items.length > 0);

  const showAnalyticsCta = canAccess(user?.role, "analytics");
  const showSettings = canAccess(user?.role, "configuracion");

  return (
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
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
          onClick={onClose}
          aria-label="Cerrar menú"
        >
          <X size={19} />
        </button>
      </div>

      <div className="workspace">
        <div className="workspace-avatar">SE</div>
        <div className="workspace-copy">
          <strong>SalesIA Enterprise</strong>
          <span>Entorno de desarrollo</span>
        </div>
        <ChevronDown size={16} className="muted-icon" />
      </div>

      <div className="nav-scroll">
        {groups.map((group) => (
          <div className="nav-group" key={group.title}>
            <p className="nav-heading">{group.title}</p>
            {group.items.map(({ label, path, icon: Icon }) => (
              <NavLink
                key={label}
                to={path}
                end={path === "/"}
                className={({ isActive }) =>
                  `nav-link ${isActive ? "nav-link-active" : ""}`
                }
                onClick={onClose}
              >
                <Icon size={18} strokeWidth={1.8} />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="sidebar-bottom">
        {showAnalyticsCta && (
          <div className="upgrade-card">
            <div className="upgrade-icon">
              <Sparkles size={17} />
            </div>
            <strong>Inteligencia comercial</strong>
            <p>Convierte tus datos en decisiones basadas en evidencia.</p>
            <button onClick={() => navigate("/analytics")}>
              Explorar Analytics <ArrowRight size={15} />
            </button>
          </div>
        )}
        <NavLink
          to="/ayuda"
          className={({ isActive }) =>
            `nav-link help-link ${isActive ? "nav-link-active" : ""}`
          }
          onClick={onClose}
        >
          <CircleHelp size={18} />
          <span>Centro de ayuda</span>
        </NavLink>
        <div className="profile">
          <div className="profile-avatar">{avatar}</div>
          <div className="profile-copy">
            <strong>{displayName}</strong>
            <span>{displayEmail}</span>
          </div>
          {showSettings && (
            <NavLink
              to="/configuracion"
              className="icon-button profile-settings"
              aria-label="Configuración del perfil"
            >
              <Settings size={17} />
            </NavLink>
          )}
        </div>
      </div>
    </aside>
  );
}
