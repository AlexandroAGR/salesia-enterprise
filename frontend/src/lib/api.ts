export const TOKEN_KEY = "salesia_token";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined | null>;
};

function buildQuery(query: RequestOptions["query"]): string {
  if (!query) return "";

  const params = new URLSearchParams();

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });

  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;

  try {
    response = await fetch(`/api${path}${buildQuery(options.query)}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(
      "No se pudo conectar con el servidor. Verifica que el backend esté activo.",
      0,
    );
  }

  // Un 401 fuera del login significa sesión expirada: limpiamos y redirigimos.
  // En el propio intento de login, el 401 indica credenciales incorrectas.
  const isLoginAttempt = path.startsWith("/auth/login");

  if (response.status === 401 && token && !isLoginAttempt) {
    localStorage.removeItem(TOKEN_KEY);

    if (!window.location.pathname.startsWith("/login")) {
      window.location.assign("/login");
    }

    throw new ApiError("Sesión expirada. Inicia sesión nuevamente.", 401);
  }

  const text = await response.text();
  const data = text ? (JSON.parse(text) as unknown) : null;

  if (!response.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    let message = `Error ${response.status}`;

    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail
        .map((item) => (item as { msg?: string }).msg ?? "dato inválido")
        .join(" · ");
    }

    throw new ApiError(message, response.status, detail);
  }

  return data as T;
}

export const api = {
  get: <T>(path: string, options?: Omit<RequestOptions, "method" | "body">) =>
    request<T>(path, { ...options, method: "GET" }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
