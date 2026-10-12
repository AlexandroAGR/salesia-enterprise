import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import InsightsPage from "./InsightsPage";

function jsonResponse(data: unknown, status = 200): Response {
  const body = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => data,
  } as unknown as Response;
}

const rules = [
  {
    code: "revenue_trend",
    name: "Tendencia de ingresos",
    description: "Compara los ingresos con el periodo anterior.",
    source: "ventas",
  },
  {
    code: "category_concentration",
    name: "Concentración por categoría",
    description: "Una categoría concentra el 50% o más de los ingresos.",
    source: "ventas",
  },
  {
    code: "mean_median_skew",
    name: "Sesgo media/mediana",
    description: "La media y la mediana de un análisis no coinciden.",
    source: "analisis",
  },
];

const salesInsight = {
  id: 1,
  rule_code: "category_concentration",
  rule_name: "Concentración por categoría",
  title: "«Oficina Demo» concentra 58% de los ingresos por categoría",
  description:
    "Facturó S/ 1,490.34 de S/ 2,551.16 entre 2 categorías del " +
    "2026-10-06 al 2026-10-12. Supera el umbral de concentración del 50%.",
  severity: "warning",
  evidence: {
    date_from: "2026-10-06",
    date_to: "2026-10-12",
    seller_id: null,
    category_id: null,
    category: "Oficina Demo",
    revenue: 1490.34,
    total_revenue: 2551.16,
    share_pct: 58.42,
    groups_count: 2,
  },
  analysis_id: null,
  analysis_type: null,
  dataset_id: null,
  dataset_name: null,
  created_at: "2026-10-12T10:00:00",
};

const analysisInsight = {
  id: 2,
  rule_code: "mean_median_skew",
  rule_name: "Sesgo media/mediana",
  title: "La media supera a la mediana en «monto»",
  description:
    "Media 28.00 frente a mediana 10.00 en 5 observaciones: valores " +
    "altos puntuales elevan el promedio.",
  severity: "info",
  evidence: {
    variable: "monto",
    count: 5,
    mean: 28,
    median: 10,
    relation: "media_mayor_mediana",
  },
  analysis_id: 9,
  analysis_type: "mean_median",
  dataset_id: 4,
  dataset_name: "Ventas S08",
  created_at: "2026-10-12T10:05:00",
};

const insightPage = {
  items: [salesInsight, analysisInsight],
  total: 45,
  page: 1,
  page_size: 20,
};

const emptyPage = { items: [], total: 0, page: 1, page_size: 20 };

function mount() {
  return render(<InsightsPage />);
}

describe("InsightsPage", () => {
  beforeEach(() => {
    localStorage.setItem("salesia_token", "token-de-prueba");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("lista observaciones con severidad, evidencia y vínculos", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        const path = String(url);
        if (path.includes("/api/insights/rules")) {
          return Promise.resolve(jsonResponse(rules));
        }
        if (path.includes("/api/insights")) {
          return Promise.resolve(jsonResponse(insightPage));
        }
        return Promise.resolve(jsonResponse(null, 404));
      }),
    );

    mount();

    expect(
      await screen.findByRole("heading", { name: "Insights" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(
        "«Oficina Demo» concentra 58% de los ingresos por categoría",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Advertencia", { selector: "span.status" })).toBeInTheDocument();
    expect(screen.getByText("Informativo", { selector: "span.status" })).toBeInTheDocument();

    // Chips de evidencia (los valores nulos del ámbito se omiten y el
    // límite de 3 deja el resto en «+N más»)
    expect(screen.getByText(/Hasta/)).toBeInTheDocument();
    expect(screen.getByText(/Categoría/)).toBeInTheDocument();
    expect(screen.getByText("2026-10-12")).toBeInTheDocument();
    expect(screen.getByText("+4 más")).toBeInTheDocument();

    // Vínculos con análisis y dataset
    expect(screen.getByText("Análisis #9")).toBeInTheDocument();
    expect(screen.getByText("Ventas S08")).toBeInTheDocument();
    expect(screen.getByText("Ventas")).toBeInTheDocument();

    expect(screen.getByText(/45 observaciones registradas/)).toBeInTheDocument();
    expect(screen.getByText("Página 1 de 3")).toBeInTheDocument();

    // El detalle muestra la evidencia completa con formato
    fireEvent.click((await screen.findAllByText("Ver detalle"))[0]);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Participación")).toBeInTheDocument();
    expect(within(dialog).getByText("58.42%")).toBeInTheDocument();
    expect(within(dialog).getByText("Ingresos")).toBeInTheDocument();
  });

  it("genera insights con el período elegido y muestra el resultado", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const path = String(url);
      const method = init?.method ?? "GET";

      if (method === "POST" && path.includes("/api/insights/generate")) {
        return Promise.resolve(
          jsonResponse({ created: [salesInsight], skipped: 3 }),
        );
      }
      if (path.includes("/api/insights/rules")) {
        return Promise.resolve(jsonResponse(rules));
      }
      if (path.includes("/api/insights")) {
        return Promise.resolve(jsonResponse(insightPage));
      }
      return Promise.resolve(jsonResponse(null, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    mount();

    const periodSelect = await screen.findByLabelText("Período de análisis");
    fireEvent.change(periodSelect, { target: { value: "30" } });

    fireEvent.click(
      await screen.findByRole("button", { name: /generar insights/i }),
    );

    expect(
      await screen.findByText(
        /Se crearon 1 observación nueva y se omitieron 3 duplicadas/,
      ),
    ).toBeInTheDocument();

    const postCall = fetchMock.mock.calls.find(
      ([url, init]) =>
        String(url).includes("/api/insights/generate") &&
        (init as RequestInit)?.method === "POST",
    );
    expect(postCall).toBeTruthy();
    expect(
      JSON.parse(String((postCall?.[1] as RequestInit).body)),
    ).toEqual({ period: "30" });
  });

  it("avisa cuando la generación no produce observaciones nuevas", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const path = String(url);
        const method = init?.method ?? "GET";

        if (method === "POST" && path.includes("/api/insights/generate")) {
          return Promise.resolve(jsonResponse({ created: [], skipped: 7 }));
        }
        if (path.includes("/api/insights/rules")) {
          return Promise.resolve(jsonResponse(rules));
        }
        if (path.includes("/api/insights")) {
          return Promise.resolve(jsonResponse(insightPage));
        }
        return Promise.resolve(jsonResponse(null, 404));
      }),
    );

    mount();

    fireEvent.click(
      await screen.findByRole("button", { name: /generar insights/i }),
    );

    expect(
      await screen.findByText(
        /Sin observaciones nuevas: 7 resultados ya registrados/,
      ),
    ).toBeInTheDocument();
  });

  it("filtra por regla y por severidad recargando la lista", async () => {
    const fetchMock = vi.fn((url: string) => {
      const path = String(url);
      if (path.includes("/api/insights/rules")) {
        return Promise.resolve(jsonResponse(rules));
      }
      if (path.includes("/api/insights")) {
        return Promise.resolve(jsonResponse(insightPage));
      }
      return Promise.resolve(jsonResponse(null, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    mount();

    const ruleSelect = await screen.findByLabelText("Filtrar por regla");
    fireEvent.change(ruleSelect, { target: { value: "category_concentration" } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes("rule_code=category_concentration"),
        ),
      ).toBe(true);
    });

    const severitySelect = screen.getByLabelText("Filtrar por severidad");
    fireEvent.change(severitySelect, { target: { value: "warning" } });

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([url]) =>
          String(url).includes("severity=warning"),
        ),
      ).toBe(true);
    });
  });

  it("muestra el estado vacío cuando no hay observaciones", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        const path = String(url);
        if (path.includes("/api/insights/rules")) {
          return Promise.resolve(jsonResponse(rules));
        }
        if (path.includes("/api/insights")) {
          return Promise.resolve(jsonResponse(emptyPage));
        }
        return Promise.resolve(jsonResponse(null, 404));
      }),
    );

    mount();

    expect(
      await screen.findByText(/Aún no hay observaciones/),
    ).toBeInTheDocument();
    expect(screen.getByText(/0 observaciones registradas/)).toBeInTheDocument();
  });

  it("abre el detalle con la evidencia completa y el análisis de origen", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        const path = String(url);
        if (path.includes("/api/insights/rules")) {
          return Promise.resolve(jsonResponse(rules));
        }
        if (path.includes("/api/insights")) {
          return Promise.resolve(jsonResponse(insightPage));
        }
        return Promise.resolve(jsonResponse(null, 404));
      }),
    );

    mount();

    fireEvent.click((await screen.findAllByText("Ver detalle"))[1]);

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveAttribute("aria-label", "Observación #2");

    const evidenceTable = within(dialog).getByText("Evidencia numérica")
      .parentElement as HTMLElement;
    const rows = within(evidenceTable).getAllByRole("row");
    expect(rows.length).toBeGreaterThanOrEqual(6); // cabecera + 5 datos

    expect(within(dialog).getByText("Media > Mediana")).toBeInTheDocument();
    expect(
      within(dialog).getByText(
        /Generado por el análisis #9 \(Media y mediana\) · Dataset: Ventas S08/,
      ),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/La media y la mediana de un análisis no coinciden/),
    ).toBeInTheDocument();
  });
});
