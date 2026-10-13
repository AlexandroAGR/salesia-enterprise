import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "../context/auth-context";
import { SearchProvider } from "../context/SearchContext";
import CustomersPage from "./CustomersPage";
import type { SessionUser } from "../types";

function jsonResponse(data: unknown, status = 200): Response {
  const body = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => data,
  } as unknown as Response;
}

const adminUser: SessionUser = {
  id: 1,
  email: "admin@salesia.com",
  full_name: "Administrador General",
  company_id: 1,
  role_id: 1,
  role: "Administrador",
  is_active: true,
};

const gerenteUser: SessionUser = {
  ...adminUser,
  id: 2,
  email: "gerente@salesia.com",
  role_id: 2,
  role: "Gerente",
};

const customer = {
  id: 7,
  full_name: "María Fernanda López",
  document_type: "DNI",
  document_number: "45678912",
  email: "maria@correo.com",
  phone: "999 888 777",
  address: "Av. Principal 123",
  is_active: true,
  created_at: "2026-10-01T10:00:00Z",
};

const emptyPage = {
  items: [],
  total: 0,
  page: 1,
  page_size: 10,
};

/**
 * Mock de fetch que responde la API de clientes y registra los POST/PATCH.
 * `mode` permite forzar un error del servidor en la creación.
 */
function apiFetchMock(mode: "ok" | "error" = "ok") {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = String(url);
    const method = init?.method ?? "GET";

    if (path.includes("/api/customers") && method === "POST") {
      if (mode === "error") {
        return jsonResponse(
          { detail: "El documento ya está registrado" },
          409,
        );
      }

      const payload = JSON.parse(String(init?.body)) as {
        full_name: string;
      };
      return jsonResponse(
        { ...customer, id: 99, full_name: payload.full_name },
        201,
      );
    }

    if (path.includes("/api/customers/") && method === "PATCH") {
      return jsonResponse(customer);
    }

    if (path.includes("/api/customers/") && method === "DELETE") {
      return jsonResponse(null, 204);
    }

    if (path.includes("/api/customers")) {
      return jsonResponse({
        items: [customer],
        total: 1,
        page: 1,
        page_size: 10,
      });
    }

    return jsonResponse(emptyPage);
  });
}

/** Busca la primera llamada a fetch que coincide y devuelve su cuerpo JSON. */
function bodyOf(
  fetchMock: ReturnType<typeof vi.fn>,
  match: (url: string, init?: RequestInit) => boolean,
): Record<string, unknown> | null {
  const call = fetchMock.mock.calls.find(([url, init]) =>
    match(String(url), init as RequestInit | undefined),
  );

  if (!call) return null;
  const body = (call[1] as RequestInit | undefined)?.body;
  return body === undefined ? null : (JSON.parse(String(body)) as Record<string, unknown>);
}

function mount(user: SessionUser) {
  return render(
    <MemoryRouter>
      <AuthContext.Provider
        value={{
          user,
          loading: false,
          login: async () => undefined,
          logout: () => undefined,
        }}
      >
        <SearchProvider>
          <CustomersPage />
        </SearchProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe("CustomersPage", () => {
  beforeEach(() => {
    localStorage.setItem("salesia_token", "token-de-prueba");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lista los clientes devueltos por la API", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(adminUser);

    expect(
      await screen.findByText("María Fernanda López"),
    ).toBeInTheDocument();
    expect(screen.getByText("maria@correo.com")).toBeInTheDocument();
    expect(screen.getByText("1 registro")).toBeInTheDocument();
    expect(screen.getByText("DNI 45678912")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
  });

  it("declara las restricciones de validación en el formulario", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: /Nuevo cliente/ }),
    );

    const name = await screen.findByPlaceholderText(
      "Ej. María Fernanda López",
    );
    expect(name).toBeRequired();
    expect(name).toHaveAttribute("minlength", "2");
    expect(name).toHaveAttribute("maxlength", "160");

    const email = screen.getByPlaceholderText("cliente@correo.com");
    expect(email).toHaveAttribute("type", "email");

    expect(
      screen.getByRole("button", { name: "Crear cliente" }),
    ).toBeInTheDocument();
  });

  it("crea un cliente y recarga el listado", async () => {
    const fetchMock = apiFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: /Nuevo cliente/ }),
    );

    fireEvent.change(
      await screen.findByPlaceholderText("Ej. María Fernanda López"),
      { target: { value: "Carlos Ramírez" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Crear cliente" }),
    );

    // El modal se cierra tras guardar.
    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Crear cliente" }),
      ).not.toBeInTheDocument();
    });

    const payload = bodyOf(
      fetchMock,
      (url, init) =>
        url.includes("/api/customers") && init?.method === "POST",
    );
    expect(payload).not.toBeNull();
    expect(payload?.full_name).toBe("Carlos Ramírez");
    expect(payload?.document_type).toBe("DNI");
    expect(payload?.email).toBeNull();

    // Se vuelve a pedir la lista.
    await waitFor(() => {
      const reloads = fetchMock.mock.calls.filter(
        ([url, init]) =>
          String(url).includes("/api/customers") &&
          (!(init as RequestInit | undefined)?.method ||
            (init as RequestInit).method === "GET"),
      );
      expect(reloads.length).toBeGreaterThan(1);
    });
  });

  it("muestra el detalle del error cuando el servidor rechaza la creación", async () => {
    vi.stubGlobal("fetch", apiFetchMock("error"));

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: /Nuevo cliente/ }),
    );
    fireEvent.change(
      await screen.findByPlaceholderText("Ej. María Fernanda López"),
      { target: { value: "Cliente Duplicado" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Crear cliente" }),
    );

    expect(
      await screen.findByText("El documento ya está registrado"),
    ).toBeInTheDocument();
    // El modal sigue abierto para que el usuario corrija.
    expect(
      screen.getByRole("button", { name: "Crear cliente" }),
    ).toBeInTheDocument();
  });

  it("abre el formulario de edición precargado y envía PATCH", async () => {
    const fetchMock = apiFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: "Editar cliente" }),
    );

    const name = await screen.findByPlaceholderText(
      "Ej. María Fernanda López",
    );
    expect(name).toHaveValue("María Fernanda López");
    expect(screen.getByText("Editar cliente")).toBeInTheDocument();

    fireEvent.change(name, { target: { value: "María F. López" } });
    fireEvent.click(
      screen.getByRole("button", { name: "Guardar cambios" }),
    );

    await waitFor(() => {
      const patch = bodyOf(
        fetchMock,
        (url, init) =>
          url.includes("/api/customers/7") && init?.method === "PATCH",
      );
      expect(patch).not.toBeNull();
    });

    const patch = bodyOf(
      fetchMock,
      (url, init) =>
        url.includes("/api/customers/7") && init?.method === "PATCH",
    );
    expect(patch?.full_name).toBe("María F. López");
  });

  it("desactiva un cliente cuando se confirma", async () => {
    const confirmSpy = vi
      .spyOn(window, "confirm")
      .mockReturnValue(true);
    const fetchMock = apiFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: "Desactivar cliente" }),
    );

    expect(confirmSpy).toHaveBeenCalledOnce();

    await waitFor(() => {
      const remove = fetchMock.mock.calls.find(
        ([url, init]) =>
          String(url).includes("/api/customers/7") &&
          (init as RequestInit | undefined)?.method === "DELETE",
      );
      expect(remove).toBeDefined();
    });
  });

  it("no cancela la desactivación si el usuario cancela el diálogo", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchMock = apiFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: "Desactivar cliente" }),
    );

    const remove = fetchMock.mock.calls.find(
      (call) => (call[1] as RequestInit | undefined)?.method === "DELETE",
    );
    expect(remove).toBeUndefined();
    expect(
      screen.getByRole("button", { name: "Desactivar cliente" }),
    ).toBeInTheDocument();
  });

  it("el rol Gerente no ve acciones de creación ni de edición", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(gerenteUser);

    expect(
      await screen.findByText("María Fernanda López"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Nuevo cliente/ }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Editar cliente" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Desactivar cliente" }),
    ).not.toBeInTheDocument();
  });

  it("muestra el estado vacío cuando no hay clientes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => jsonResponse(emptyPage)),
    );

    mount(adminUser);

    expect(
      await screen.findByText("Aún no hay clientes registrados."),
    ).toBeInTheDocument();
    expect(screen.getByText("0 registros")).toBeInTheDocument();
  });

  it("muestra un aviso cuando la API falla", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("sin conexión"))),
    );

    mount(adminUser);

    expect(
      await screen.findByText(
        "No se pudo conectar con el servidor. Verifica que el backend esté activo.",
      ),
    ).toBeInTheDocument();
  });
});
