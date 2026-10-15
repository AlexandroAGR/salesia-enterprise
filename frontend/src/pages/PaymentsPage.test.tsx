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
import PaymentsPage from "./PaymentsPage";
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

const analistaUser: SessionUser = {
  ...adminUser,
  id: 3,
  email: "analista@salesia.com",
  role_id: 3,
  role: "Analista",
};

const payment = {
  id: 13,
  sale_id: 3,
  sale_number: "V-SEED-0003",
  payment_method_id: 1,
  amount: "100.00",
  currency: "PEN",
  status: "paid",
  reference: "PARCIAL-1",
  paid_at: "2026-10-15T07:00:00Z",
  created_at: "2026-10-15T07:00:00Z",
};

const pendingSale = {
  id: 3,
  sale_number: "V-SEED-0003",
  status: "pending",
  currency: "PEN",
  customer_id: null,
  customer_name: null,
  subtotal: "387.10",
  discount_amount: "0.00",
  tax_amount: "69.56",
  total_amount: "456.66",
  amount_paid: "100.00",
  balance: "356.66",
  notes: null,
  sold_at: "2026-10-15T06:00:00Z",
  created_at: "2026-10-15T06:00:00Z",
};

const methods = [
  { id: 1, name: "Efectivo", code: "EFEC", is_active: true },
  { id: 2, name: "Tarjeta de crédito", code: "TARC", is_active: true },
];

const emptyPage = { items: [], total: 0, page: 1, page_size: 10 };

/** Mock de fetch que responde la API de pagos y registra los POST. */
function apiFetchMock(mode: "ok" | "error" = "ok") {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = String(url);
    const method = init?.method ?? "GET";

    if (path.includes("/api/payments") && method === "POST") {
      if (mode === "error") {
        return jsonResponse({ detail: "El monto supera el pendiente (59.00)" }, 409);
      }

      const payload = JSON.parse(String(init?.body)) as {
        amount: string;
        sale_id: number;
      };
      return jsonResponse(
        {
          ...payment,
          id: 99,
          amount: payload.amount,
          sale_id: payload.sale_id,
        },
        201,
      );
    }

    if (path.includes("/api/payments")) {
      return jsonResponse({
        items: [payment],
        total: 1,
        page: 1,
        page_size: 10,
      });
    }

    if (path.includes("/api/payment-methods")) {
      return jsonResponse(methods);
    }

    if (path.includes("/api/sales")) {
      return jsonResponse({ ...emptyPage, items: [pendingSale], total: 1 });
    }

    return jsonResponse(emptyPage);
  });
}

/** Primer body JSON de las llamadas POST a /api/payments. */
function paymentBody(fetchMock: ReturnType<typeof vi.fn>) {
  const call = fetchMock.mock.calls.find(
    ([url, init]) =>
      String(url).includes("/api/payments") &&
      (init as RequestInit | undefined)?.method === "POST",
  );
  const body = (call?.[1] as RequestInit | undefined)?.body;
  return body === undefined
    ? null
    : (JSON.parse(String(body)) as Record<string, unknown>);
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
          <PaymentsPage />
        </SearchProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}

describe("PaymentsPage", () => {
  beforeEach(() => {
    localStorage.setItem("salesia_token", "token-de-prueba");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lista los pagos con su número de venta e importe", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(adminUser);

    expect(await screen.findByText("V-SEED-0003")).toBeInTheDocument();
    expect(screen.getByText("PARCIAL-1")).toBeInTheDocument();
    expect(screen.getByText("S/ 100.00")).toBeInTheDocument();
    expect(screen.getByText("Pagado")).toBeInTheDocument();
    expect(screen.getByText("1 pago")).toBeInTheDocument();
  });

  it("permite registrar un pago con la venta y el saldo pendiente", async () => {
    const fetchMock = apiFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: /Registrar pago/ }),
    );

    const saleSelect = await screen.findByLabelText(
      /Venta con saldo pendiente/,
    );
    fireEvent.change(saleSelect, { target: { value: "3" } });

    // El saldo pendiente se sugiere como importe del pago.
    const amountInput = screen.getByLabelText(/^Importe/);
    expect(amountInput).toHaveValue(356.66);

    fireEvent.change(screen.getByLabelText(/Método de pago/), {
      target: { value: "1" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));

    await waitFor(() => {
      const body = paymentBody(fetchMock);
      expect(body).not.toBeNull();
      expect(body?.sale_id).toBe(3);
      expect(body?.payment_method_id).toBe(1);
      expect(body?.currency).toBe("PEN");
    });

    expect(
      await screen.findByText(/Pago de S\/ 356.66 registrado/),
    ).toBeInTheDocument();
  });

  it("muestra el error del servidor cuando el monto supera el pendiente", async () => {
    vi.stubGlobal("fetch", apiFetchMock("error"));

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: /Registrar pago/ }),
    );

    fireEvent.change(await screen.findByLabelText(/Venta con saldo pendiente/), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByLabelText(/Método de pago/), {
      target: { value: "1" },
    });
    // Dentro del saldo pendiente en cliente, pero el servidor lo rechaza.
    fireEvent.change(screen.getByLabelText(/^Importe/), {
      target: { value: "300" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));

    expect(
      await screen.findByText("El monto supera el pendiente (59.00)"),
    ).toBeInTheDocument();
  });

  it("impide en cliente enviar un importe mayor al saldo pendiente", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(adminUser);

    fireEvent.click(
      await screen.findByRole("button", { name: /Registrar pago/ }),
    );

    fireEvent.change(await screen.findByLabelText(/Venta con saldo pendiente/), {
      target: { value: "3" },
    });
    fireEvent.change(screen.getByLabelText(/Método de pago/), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText(/^Importe/), {
      target: { value: "9999" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));

    expect(
      await screen.findByText(/El importe supera el saldo pendiente/),
    ).toBeInTheDocument();
  });

  it("oculta el botón de registro a los roles sin permiso", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(analistaUser);

    expect(await screen.findByText("V-SEED-0003")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Registrar pago/ }),
    ).not.toBeInTheDocument();
  });

  it("lista el catálogo de métodos de pago en la segunda pestaña", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount(adminUser);

    fireEvent.click(await screen.findByRole("button", { name: /Métodos de pago/ }));

    expect(await screen.findByText("Efectivo")).toBeInTheDocument();
    expect(screen.getByText("Tarjeta de crédito")).toBeInTheDocument();
    expect(screen.getByText("EFEC")).toBeInTheDocument();
    expect(screen.getByText("TARC")).toBeInTheDocument();
  });
});
