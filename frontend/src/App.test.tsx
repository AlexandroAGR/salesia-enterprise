import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const sessionUser = {
  id: 1,
  email: "admin@salesia.com",
  full_name: "Administrador General",
  company_id: 1,
  role_id: 1,
  role: "Administrador",
  is_active: true,
};

const vendedorUser = {
  id: 3,
  email: "vendedor@salesia.com",
  full_name: "Vendedor Demo",
  company_id: 1,
  role_id: 3,
  role: "Vendedor",
  is_active: true,
};

function sessionFetch(user: typeof sessionUser) {
  return vi.fn((url: string) => {
    const path = String(url);

    if (path.includes("/api/auth/me")) {
      return Promise.resolve(jsonResponse(user));
    }

    return Promise.resolve(
      jsonResponse({ items: [], total: 0, page: 1, page_size: 20 }),
    );
  });
}

function navLabels(): string[] {
  return Array.from(document.querySelectorAll(".nav-link")).map(
    (element) => element.textContent ?? "",
  );
}

function jsonResponse(data: unknown, status = 200): Response {
  const body = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => data,
  } as unknown as Response;
}

describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    window.history.replaceState({}, "", "/");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("redirige al login cuando no hay sesión", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Inicia sesión" }),
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("admin@salesia.com"),
    ).toBeInTheDocument();
  });

  it("inicia sesión y muestra el dashboard", async () => {
    const fetchMock = vi.fn((url: string) => {
      const path = String(url);

      if (path.includes("/api/auth/login")) {
        return Promise.resolve(
          jsonResponse({ access_token: "token-de-prueba" }),
        );
      }

      if (path.includes("/api/auth/me")) {
        return Promise.resolve(jsonResponse(sessionUser));
      }

      return Promise.resolve(
        jsonResponse({ items: [], total: 0, page: 1, page_size: 20 }),
      );
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(
      await screen.findByPlaceholderText("admin@salesia.com"),
      { target: { value: "admin@salesia.com" } },
    );
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "Admin123*" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /ingresar al sistema/i }),
    );

    expect(
      await screen.findByRole("heading", { name: "Dashboard ejecutivo" }),
    ).toBeInTheDocument();
  });

  it("muestra error con credenciales inválidas", async () => {
    const fetchMock = vi.fn((url: string) => {
      const path = String(url);

      if (path.includes("/api/auth/login")) {
        return Promise.resolve(
          jsonResponse({ detail: "Credenciales incorrectas" }, 401),
        );
      }

      return Promise.resolve(jsonResponse(null, 500));
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.change(
      await screen.findByPlaceholderText("admin@salesia.com"),
      { target: { value: "mal@correo.com" } },
    );
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "incorrecta" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /ingresar al sistema/i }),
    );

    expect(
      await screen.findByText("Credenciales incorrectas"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Inicia sesión" }),
    ).toBeInTheDocument();
  });

  it("protege las rutas privadas sin sesión", async () => {
    window.history.replaceState({}, "", "/clientes");

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Inicia sesión" }),
    ).toBeInTheDocument();
  });

  it("oculta los módulos que el rol no puede consultar", async () => {
    localStorage.setItem("salesia_token", "token-de-prueba");
    vi.stubGlobal("fetch", sessionFetch(vendedorUser));

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Dashboard ejecutivo" }),
    ).toBeInTheDocument();

    const labels = navLabels();
    expect(labels).toContain("Ventas");
    expect(labels).toContain("Clientes");
    expect(labels).not.toContain("Insights");
    expect(labels).not.toContain("Reportes");
    expect(labels).not.toContain("Inventario");
    expect(labels).not.toContain("Configuración");
    expect(screen.queryByRole("button", { name: /explorar analytics/i })).toBe(
      null,
    );
  });

  it("bloquea el acceso directo a un módulo restringido", async () => {
    localStorage.setItem("salesia_token", "token-de-prueba");
    window.history.replaceState({}, "", "/reportes");
    vi.stubGlobal("fetch", sessionFetch(vendedorUser));

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "Acceso restringido" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Reportes" }),
    ).not.toBeInTheDocument();
  });
});
