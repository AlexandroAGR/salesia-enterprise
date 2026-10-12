import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { SearchProvider } from "../context/SearchContext";
import DashboardPage from "./DashboardPage";
import { money } from "../utils/format";

function jsonResponse(data: unknown, status = 200): Response {
  const body = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => data,
  } as unknown as Response;
}

const summaryFixture = {
  filters: {
    date_from: "2026-09-13",
    date_to: "2026-10-12",
    seller_id: null,
    category_id: null,
  },
  kpis: {
    revenue: 8092.44,
    sales_count: 6,
    avg_ticket: 1348.74,
    customers_count: 2,
    items_sold: 12,
  },
  statistics: {
    count: 6,
    mean: 1348.74,
    median: 824.23,
    min: 446.04,
    max: 3892.82,
    stddev: 1213.47,
  },
  previous_period: {
    revenue: 7504.8,
    sales_count: 5,
    revenue_change_pct: 7.83,
  },
};

const seriesFixture = {
  granularity: "day",
  items: [
    { bucket: "2026-10-10", sales_count: 1, revenue: 446.04 },
    { bucket: "2026-10-11", sales_count: 1, revenue: 1060.82 },
    { bucket: "2026-10-12", sales_count: 4, revenue: 6585.58 },
  ],
};

const categoryFixture = {
  group_by: "category",
  items: [
    {
      id: 1,
      label: "Tecnología Demo",
      revenue: 6602.1,
      sales_count: 4,
      quantity: 6,
    },
    {
      id: 2,
      label: "Oficina Demo",
      revenue: 1490.34,
      sales_count: 3,
      quantity: 8,
    },
  ],
};

const productFixture = {
  group_by: "product",
  items: [
    {
      id: 1,
      label: "Laptop empresarial",
      revenue: 3892.82,
      sales_count: 1,
      quantity: 1,
    },
  ],
};

const sellerFixture = {
  group_by: "seller",
  items: [
    {
      id: 1,
      label: "Admin SalesIA",
      revenue: 7504.8,
      sales_count: 5,
      quantity: null,
    },
  ],
};

const frequenciesFixture = {
  count: 6,
  min: 446.04,
  max: 3892.82,
  mean: 1348.74,
  median: 824.23,
  bins: [
    { bin_start: 446.04, bin_end: 1307.74, frequency: 4, relative: 0.6667 },
    { bin_start: 1307.74, bin_end: 2169.43, frequency: 1, relative: 0.1667 },
    { bin_start: 2169.43, bin_end: 3031.12, frequency: 0, relative: 0 },
    { bin_start: 3031.12, bin_end: 3892.82, frequency: 1, relative: 0.1667 },
  ],
};

const optionsFixture = {
  sellers: [
    { id: 1, name: "Admin SalesIA" },
    { id: 2, name: "Vendedor Demo" },
  ],
  categories: [
    { id: 1, name: "Tecnología Demo" },
    { id: 2, name: "Oficina Demo" },
  ],
};

const salesFixture = {
  items: [
    {
      id: 8,
      sale_number: "V-20261012-ABC123",
      status: "completed",
      currency: "PEN",
      customer_id: 1,
      customer_name: "Cliente Demo Uno",
      subtotal: "500.00",
      discount_amount: "0.00",
      tax_amount: "90.00",
      total_amount: "590.00",
      notes: null,
      sold_at: "2026-10-12T09:00:00Z",
      created_at: "2026-10-12T09:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  page_size: 5,
};

function apiFetchMock() {
  return vi.fn((url: string) => {
    const path = String(url);

    if (path.includes("/api/analytics/summary")) {
      return jsonResponse(summaryFixture);
    }
    if (path.includes("/api/analytics/series")) {
      return jsonResponse(seriesFixture);
    }
    if (path.includes("/api/analytics/frequencies")) {
      return jsonResponse(frequenciesFixture);
    }
    if (path.includes("/api/analytics/filters")) {
      return jsonResponse(optionsFixture);
    }
    if (path.includes("/api/analytics/breakdown")) {
      if (path.includes("group_by=product")) return jsonResponse(productFixture);
      if (path.includes("group_by=seller")) return jsonResponse(sellerFixture);
      return jsonResponse(categoryFixture);
    }
    if (path.includes("/api/sales")) return jsonResponse(salesFixture);

    return jsonResponse({ items: [], total: 0, page: 1, page_size: 20 });
  });
}

function mount() {
  return render(
    <MemoryRouter>
      <SearchProvider>
        <DashboardPage />
      </SearchProvider>
    </MemoryRouter>,
  );
}

/**
 * `money()` usa el espacio duro de es-PE (U+00A0) después de "S/", que el
 * matcher de texto no compara bien; se normaliza a espacio simple.
 */
function moneyNode(value: number | string) {
  const expected = money(value).replace(/\u00a0/g, " ").trim();
  return (content: string) =>
    content.replace(/\u00a0/g, " ").trim() === expected;
}

describe("DashboardPage", () => {
  beforeEach(() => {
    localStorage.setItem("salesia_token", "token-de-prueba");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("muestra los KPIs reales del periodo con su comparativa", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount();

    expect(await screen.findByText(moneyNode(8092.44))).toBeInTheDocument();
    expect(screen.queryAllByText(moneyNode(1348.74)).length).toBeGreaterThan(0);
    expect(
      screen.getByText("+7.8% vs. periodo anterior"),
    ).toBeInTheDocument();

    const clientsCard = screen.getByText("Clientes").closest("article");
    expect(clientsCard).not.toBeNull();
    expect(within(clientsCard as HTMLElement).getByText("2")).toBeInTheDocument();
  });

  it("pinta los gráficos, la distribución y la media/mediana", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount();

    expect(
      await screen.findByRole("heading", { name: "Evolución de ingresos" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Ventas por categoría" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Ventas por producto" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Ventas por vendedor" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Distribución de montos" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Media y mediana del periodo" }),
    ).toBeInTheDocument();

    // Reparto real por categoría: 6602.10 de 8092.44 → 82 %.
    expect(
      (await screen.findAllByText("Tecnología Demo")).length,
    ).toBeGreaterThan(0);
    expect(screen.getAllByText("82%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("18%").length).toBeGreaterThan(0);

    // Mediana en el panel de estadística descriptiva.
    expect(
      screen.queryAllByText(moneyNode(824.23)).length,
    ).toBeGreaterThan(0);
  });

  it("muestra la actividad comercial reciente con su estado", async () => {
    vi.stubGlobal("fetch", apiFetchMock());

    mount();

    expect(await screen.findByText("Cliente Demo Uno")).toBeInTheDocument();
    expect(screen.getByText("V-20261012-ABC123")).toBeInTheDocument();
    expect(screen.getByText("Completada")).toBeInTheDocument();
    expect(await screen.findByText(moneyNode(590))).toBeInTheDocument();
  });

  it("carga los selectores y refresca el dashboard al filtrar", async () => {
    const fetchMock = apiFetchMock();
    vi.stubGlobal("fetch", fetchMock);

    mount();

    const sellerSelect = await screen.findByLabelText("Vendedor");
    await waitFor(() =>
      expect(
        within(sellerSelect).getByRole("option", { name: "Vendedor Demo" }),
      ).toBeInTheDocument(),
    );
    expect(
      within(await screen.findByLabelText("Categoría")).getByRole("option", {
        name: "Oficina Demo",
      }),
    ).toBeInTheDocument();

    fireEvent.change(sellerSelect, { target: { value: "2" } });

    await waitFor(() => {
      const refreshed = fetchMock.mock.calls.some(
        ([url]) =>
          String(url).includes("/api/analytics/summary") &&
          String(url).includes("seller_id=2"),
      );
      expect(refreshed).toBe(true);
    });
  });

  it("muestra un aviso cuando la API falla", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("sin conexión"))),
    );

    mount();

    expect(
      await screen.findByText(/No se pudo cargar el dashboard/),
    ).toBeInTheDocument();
  });
});
