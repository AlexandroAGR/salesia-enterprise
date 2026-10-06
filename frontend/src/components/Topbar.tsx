import { Link, useLocation, useNavigate } from "react-router-dom";
import { Bell, LogOut, Menu, Search } from "lucide-react";
import { useAuth } from "../context/auth-context";
import { useSearch } from "../context/search-context";
import { titleForPath } from "../navigation";
import { initials } from "../utils/format";

type TopbarProps = {
  onOpenMenu: () => void;
};

export default function Topbar({ onOpenMenu }: TopbarProps) {
  const { user, logout } = useAuth();
  const { search, setSearch } = useSearch();
  const location = useLocation();
  const navigate = useNavigate();

  const avatar = initials(user?.full_name ?? "Usuario") || "US";

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          className="icon-button mobile-menu-button"
          onClick={onOpenMenu}
          aria-label="Abrir menú"
        >
          <Menu size={21} />
        </button>

        <div className="breadcrumb">
          <span>Workspace</span>
          <span className="breadcrumb-separator">/</span>
          <strong>{titleForPath(location.pathname)}</strong>
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
        </label>

        <Link
          to="/ayuda"
          className="icon-button notification-button"
          aria-label="Ayuda"
        >
          <Bell size={19} />
          <span className="notification-dot" />
        </Link>

        <div className="topbar-avatar" title={user?.full_name ?? "Usuario"}>
          {avatar}
        </div>

        <button
          type="button"
          className="logout-button"
          onClick={handleLogout}
          aria-label="Cerrar sesión"
          title="Cerrar sesión"
        >
          <LogOut size={18} />
          <span>Cerrar sesión</span>
        </button>
      </div>
    </header>
  );
}