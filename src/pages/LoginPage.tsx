import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ChartNoAxesCombined, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useAuth } from "../context/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const from =
    (location.state as { from?: string } | null)?.from ?? "/";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (caught) {
      const message =
        caught instanceof Error
          ? caught.message
          : "No se pudo iniciar sesión.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <section className="login-brand">
        <div className="login-brand-mark">
          <ChartNoAxesCombined size={30} strokeWidth={2.3} />
        </div>
        <h1>SalesIA Enterprise</h1>
        <p>
          Gestión comercial y analítica estadística en una sola plataforma:
          ventas, clientes, productos, inventario e insights.
        </p>
        <ul>
          <li>Registro operativo completo</li>
          <li>Motor estadístico: media, mediana y Bayes</li>
          <li>Roles y auditoría por usuario</li>
        </ul>
      </section>

      <section className="login-panel">
        <form className="login-form" onSubmit={handleSubmit}>
          <span className="eyebrow">
            <span className="eyebrow-dot" />
            ACCESO SEGURO
          </span>
          <h2>Inicia sesión</h2>
          <p>Ingresa con tu cuenta corporativa para continuar.</p>

          {error && (
            <div className="form-alert" role="alert">
              {error}
            </div>
          )}

          <label className="form-field">
            <span>Correo electrónico</span>
            <div className="input-with-icon">
              <Mail size={17} />
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="admin@salesia.com"
                autoComplete="username"
                required
              />
            </div>
          </label>

          <label className="form-field">
            <span>Contraseña</span>
            <div className="input-with-icon">
              <Lock size={17} />
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={
                  showPassword ? "Ocultar contraseña" : "Mostrar contraseña"
                }
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>

          <button
            type="submit"
            className="button-primary login-submit"
            disabled={submitting}
          >
            {submitting ? "Validando..." : "Ingresar al sistema"}
          </button>

          <p className="login-hint">
            Desarrollo: admin@salesia.com / Admin123*
          </p>
        </form>
      </section>
    </div>
  );
}
