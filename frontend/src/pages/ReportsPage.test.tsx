import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ReportsPage from "./ReportsPage";

function jsonResponse(data: unknown, status = 200): Response {
  const body = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => data,
  } as unknown as Response;
}

const types = [
  {
    code: "ventas",
    name: "Reporte de ventas",
    description: "Detalle de las ventas del periodo con totales y estados.",
  },
  {
    code: "estadistico",
    name: "Reporte estadístico",
    description: "KPIs, estadística descriptiva e interpretación.",
  },
  {
    code: "productos",
    name: "Reporte de productos",
    description: "Ranking de productos por ingresos.",
  },
  {
    code: "clientes",
    name: "Reporte de clientes",
    description: "Ranking de clientes por facturación.",
  },
  {
    code: "vendedores",
    name: "Reporte de vendedores",
    description: "Desempeño de cada vendedor.",
  },
];

const ventasSummary = {
  id: 1,
  report_type: "ventas",
  report_type_label: "Reporte de ventas",
  title: "Reporte de ventas · 2026-10-06 al 2026-10-12",
  filters: {
    period: "7",
    date_from: "2026-10-06",
    date_to: "2026-10-12",
    seller_id: null,
    category_id: null,
  },
  created_by: 1,
  created_by_name: "Admin SalesIA",
  created_at: "2026-10-12T10:00:00",
};

const ventasReport = {
  ...ventasSummary,
  content: {
    scope: {
      date_from: "2026-10-06",
      date_to: "2026-10-12",
      seller_id: null,
      category_id: null,
    },
    summary: {
      sales_count: 4,
      revenue: 2551.16,
      avg_ticket: 637.79,
      customers_count: 2,
      items_sold: 13,
    },
    rows: [
      {
        sale_number: "V-DEMO-001",
        sold_at: "2026-10-11T12:00:00",
        customer: "Cliente Demo Uno",
        seller: "Vendedor Demo",
        status: "completed",
        subtotal: 498,
        discount_amount: 0,
        tax_amount: 89.64,
        total_amount: 587.64,
      },
      {
        sale_number: "V-DEMO-002",
        sold_at: "2026-10-10T12:00:00",
        customer: "Cliente Demo Uno",
        seller: "Admin SalesIA",
        status: "pending",
        subtotal: 378,
        discount_amount: 0,
        tax_amount: 68.04,
        total_amount: 446.04,
      },
    ],
  },
};

const estadisticoSummary = {
  id: 2,
  report_type: "estadistico",
  report_type_label: "Reporte estadístico",
  title: "Reporte estadístico · 2026-09-13 al 2026-10-12",
  filters: {
    period: "30",
    date_from: "2026-09-13",
    date_to: "2026-10-12",
    seller_id: null,
    category_id: null,
  },
  created_by: 1,
  created_by_name: "Admin SalesIA",
  created_at: "2026-10-12T10:05:00",
};

const estadisticoReport = {
  ...estadisticoSummary,
  content: {
    scope: {
      date_from: "2026-09-13",
      date_to: "2026-10-12",
      seller_id: null,
      category_id: null,
    },
    kpis: {
      sales_count: 12,
      revenue: 6150.16,
      avg_ticket: 512.51,
      customers_count: 3,
      items_sold: 40,
    },
    statistics: {
      count: 12,
      mean: 512.51,
      median: 480,
      min: 120.5,
      max: 1060.82,
      stddev: 260.11,
    },
    previous_period: {
      revenue: 5200,
      sales_count: 10,
      revenue_change_pct: 18.27,
    },
    interpretation: [
      "La media (S/ 512.51) supera a la mediana (S/ 480.00): valores altos puntuales elevan el promedio.",
      "Los importes se mantienen agrupados: coeficiente de variación 0.51 (desviación S/ 260.11 sobre media S/ 512.51).",
      "Los tickets van de S/ 120.50 a S/ 1060.82 con un ticket promedio de S/ 512.51.",
      "Los ingresos suben 18.3% frente al periodo anterior (S/ 5200.00).",
    ],
  },
};

const listPage = {
  items: [ventasSummary, estadisticoSummary],
  total: 45,
  page: 1,
  page_size: 20,
};

const emptyPage = { items: [], total: 0, page: 1, page_size: 20 };

/** Router común: types, listado, detalle, generación. */
function makeFetch(options?: { list?: object; generate?: object }) {
  return vi.fn((url: string, init?: RequestInit) => {
    const path = String(url);
    const method = init?.method ?? "GET";

    if (path.includes("/api/reports/types")) {
      return Promise.resolve(jsonResponse(types));
    }
    if (method === "POST" && path.includes("/api/reports/generate")) {
      const generate =
        options?.generate ?? ({ ...estadisticoReport } as object);
      return Promise.resolve(jsonResponse(generate));
    }
    const detail = path.match(/\/api\/reports\/(\d+)/);
    if (detail) {
      if (Number(detail[1]) === 1) {
        return Promise.resolve(jsonResponse(ventasReport));
      }
      return Promise.resolve(jsonResponse(null, 404));
    }
    if (path.includes("/api/reports")) {
      return Promise.resolve(jsonResponse(options?.list ?? listPage));
    }
    return Promise.resolve(jsonResponse(null, 404));
  });
}

function mount() {
  return render(<ReportsPage />);
}

describe("ReportsPage", () => {
  beforeEach(() => {
    localStorage.setItem("salesia_token", "token-de-prueba");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("lista el histórico con tipo, título, usuario y paginación", async () => {
    vi.stubGlobal("fetch", makeFetch());

    mount();

    expect(
      await screen.findByRole("heading", { name: "Reportes" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Reporte de ventas · 2026-10-06 al 2026-10-12"),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Admin SalesIA")).toHaveLength(2);
    expect(
      screen.getByText("Reporte de ventas", { selector: ".insight-link" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/45 reportes guardados/)).toBeInTheDocument();
    expect(screen.getByText("Página 1 de 3")).toBeInTheDocument();
  });

  it("genera un reporte, avisa y abre su instantánea", async () => {
    const fetchMock = makeFetch();
    vi.stubGlobal("fetch", fetchMock);

    mount();

    const typeSelect = await screen.findByLabelText(
      "Tipo de reporte a generar",
    );
    // Evita la carrera con la carga del catálogo: los cambios sólo
    // tienen efecto cuando el select ya ofrece las opciones.
    await waitFor(() =>
      expect((typeSelect as HTMLSelectElement).options.length).toBe(5),
    );
    fireEvent.change(typeSelect, { target: { value: "estadistico" } });
    fireEvent.change(await screen.findByLabelText("Período del reporte"), {
      target: { value: "30" },
    });

    fireEvent.click(
      await screen.findByRole("button", { name: /generar reporte/i }),
    );

    expect(
      await screen.findByText(/generado correctamente/),
    ).toBeInTheDocument();

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).includes("/api/reports/generate") &&
        (init as RequestInit)?.method === "POST",
    );
    expect(postCall).toBeTruthy();
    expect(
      JSON.parse(String((postCall?.[1] as RequestInit).body)),
    ).toEqual({ report_type: "estadistico", period: "30" });

    // La instantánea se abre sola, con su interpretación y estadística
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByText(/coeficiente de variación/),
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Registros")).toBeInTheDocument();
    expect(within(dialog).getByText("S/ 120.50")).toBeInTheDocument();
    expect(
      within(dialog).getByText(/frente al periodo anterior/),
    ).toBeInTheDocument();
  });

  it("abre el detalle, exporta a CSV e imprime la vista", async () => {
    vi.stubGlobal("fetch", makeFetch());
    const createObjectURL = vi.fn((blob: Blob) => {
      // El export se hace siempre sobre un Blob CSV
      expect(blob).toBeInstanceOf(Blob);
      return "blob:csv";
    });
    const revokeObjectURL = vi.fn((url: string) => url);
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const printSpy = vi.fn();
    vi.stubGlobal("print", printSpy);

    mount();

    fireEvent.click((await screen.findAllByText("Ver reporte"))[0]);

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("V-DEMO-001")).toBeInTheDocument();
    expect(
      within(dialog).getByText("Completada", { selector: "span.status" }),
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Pendiente", { selector: "span.status" }))
      .toBeInTheDocument();
    expect(within(dialog).getByText("S/ 587.64")).toBeInTheDocument();
    expect(
      within(dialog).getAllByText("Cliente Demo Uno"),
    ).toHaveLength(2);
    expect(within(dialog).getByText(/Del .+ al .+/)).toBeInTheDocument();

    // Exportación CSV: genera un Blob y lo descarga
    fireEvent.click(within(dialog).getByRole("button", { name: /csv/i }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:csv");

    // Vista imprimible: delega en window.print()
    fireEvent.click(
      within(dialog).getByRole("button", { name: /imprimir/i }),
    );
    expect(printSpy).toHaveBeenCalledTimes(1);
  });

  it("filtra por tipo de reporte recargando la lista", async () => {
    const fetchMock = makeFetch();
    vi.stubGlobal("fetch", fetchMock);

    mount();

    const typeSelect = await screen.findByLabelText(
      "Filtrar por tipo de reporte",
    );
    // El filtro sólo acepta valores cuando el catálogo ya está cargado
    // (5 tipos + «Todos los tipos»).
    await waitFor(() =>
      expect((typeSelect as HTMLSelectElement).options.length).toBe(6),
    );
    fireEvent.change(typeSelect, { target: { value: "ventas" } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes("report_type=ventas"),
        ),
      ).toBe(true);
    });

    fireEvent.change(typeSelect, { target: { value: "vendedores" } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes("report_type=vendedores"),
        ),
      ).toBe(true);
    });
  });

  it("muestra el estado vacío cuando no hay reportes", async () => {
    vi.stubGlobal("fetch", makeFetch({ list: emptyPage }));

    mount();

    expect(await screen.findByText(/Aún no hay reportes/)).toBeInTheDocument();
    expect(screen.getByText(/0 reportes guardados/)).toBeInTheDocument();
  });
});
