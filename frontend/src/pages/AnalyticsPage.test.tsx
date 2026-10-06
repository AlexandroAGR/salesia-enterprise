import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SearchProvider } from "../context/SearchContext";
import AnalyticsPage from "./AnalyticsPage";

function jsonResponse(data: unknown, status = 200): Response {
  const body = JSON.stringify(data);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => data,
  } as unknown as Response;
}

const emptyPage = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
};

const datasetPage = {
  items: [
    {
      id: 7,
      name: "Ventas S07",
      source_type: "manual",
      description: "Dataset de prueba",
      variables_count: 2,
      created_at: "2026-10-06T10:00:00",
    },
  ],
  total: 1,
  page: 1,
  page_size: 100,
};

const datasetDetail = {
  ...datasetPage.items[0],
  variables: [
    {
      id: 11,
      dataset_id: 7,
      name: "monto_venta",
      data_type: "numeric",
      variable_type: "continua",
      description: "Monto de cada venta",
      observations_count: 5,
    },
    {
      id: 12,
      dataset_id: 7,
      name: "zona",
      data_type: "text",
      variable_type: "cualitativa",
      description: "Zona de venta",
      observations_count: 3,
    },
  ],
};

const meanMedianResult = {
  id: 101,
  analysis_type: "mean_median",
  dataset_id: 7,
  dataset_name: "Ventas S07",
  status: "completed",
  parameters: {
    variable_id: 11,
    variable_name: "monto_venta",
    observations: 5,
  },
  created_at: "2026-10-06T12:00:00",
  results: [
    { id: 1, metric_name: "count", numeric_result: 5, result_payload: {} },
    {
      id: 2,
      metric_name: "mean",
      numeric_result: 40,
      result_payload: { formula: "suma de valores / cantidad de valores" },
    },
    { id: 3, metric_name: "median", numeric_result: 30, result_payload: {} },
    {
      id: 4,
      metric_name: "comparison",
      numeric_result: 10,
      result_payload: {
        relation: "media_mayor_mediana",
        difference: 10,
        interpretation:
          "La media supera a la mediana: sesgo positivo (cola hacia la derecha).",
      },
    },
  ],
  bayes: null,
};

const bayesResult = {
  id: 102,
  analysis_type: "bayes",
  dataset_id: null,
  dataset_name: null,
  status: "completed",
  parameters: { probability_a: 0.01 },
  created_at: "2026-10-06T12:05:00",
  results: [
    {
      id: 5,
      metric_name: "posterior_probability",
      numeric_result: 0.043478,
      result_payload: { formula: "P(A|B) = P(A)·P(B|A) / P(B)" },
    },
    {
      id: 6,
      metric_name: "marginal_probability",
      numeric_result: 0.207,
      result_payload: { computed_from_complement: true },
    },
  ],
  bayes: {
    probability_a: 0.01,
    probability_b_given_a: 0.9,
    probability_b: 0.207,
    posterior_probability: 0.043478,
    explanation:
      "P(A|B) = [P(A) · P(B|A)] / P(B) = [0.01 · 0.9] / 0.207 = 0.043478",
  },
};

function mount() {
  return render(
    <SearchProvider>
      <AnalyticsPage />
    </SearchProvider>,
  );
}

describe("AnalyticsPage", () => {
  beforeEach(() => {
    localStorage.setItem("salesia_token", "token-de-prueba");
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("muestra las pestañas del motor estadístico", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse(emptyPage))),
    );

    mount();

    expect(
      await screen.findByRole("heading", { name: "Analytics" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /datasets/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /análisis/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /historial/i }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(/sin datasets/i),
    ).toBeInTheDocument();
  });

  it("lista datasets y abre el detalle con sus variables clasificadas", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        const path = String(url);
        if (path.includes("/api/datasets/7")) {
          return Promise.resolve(jsonResponse(datasetDetail));
        }
        if (path.includes("/api/datasets")) {
          return Promise.resolve(jsonResponse(datasetPage));
        }
        return Promise.resolve(jsonResponse(emptyPage));
      }),
    );

    mount();

    fireEvent.click(await screen.findByText("Ver detalle"));

    expect(await screen.findByText("monto_venta")).toBeInTheDocument();
    expect(screen.getByText("zona")).toBeInTheDocument();
    expect(screen.getByText("Continua")).toBeInTheDocument();
    expect(screen.getByText("Cualitativa")).toBeInTheDocument();
    expect(screen.getAllByText("Agregar datos").length).toBeGreaterThan(0);
  });

  it("ejecuta el análisis de media y mediana y muestra el resultado", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const path = String(url);
      const method = init?.method ?? "GET";

      if (method === "POST" && path.includes("/api/analyses/mean-median")) {
        return Promise.resolve(jsonResponse(meanMedianResult, 201));
      }
      if (path.includes("/api/datasets/7")) {
        return Promise.resolve(jsonResponse(datasetDetail));
      }
      if (path.includes("/api/datasets")) {
        return Promise.resolve(jsonResponse(datasetPage));
      }
      if (path.includes("/api/analyses")) {
        return Promise.resolve(jsonResponse(emptyPage));
      }
      return Promise.resolve(jsonResponse(null, 404));
    });
    vi.stubGlobal("fetch", fetchMock);

    mount();

    fireEvent.click(await screen.findByRole("button", { name: /análisis/i }));

    // Selección de dataset y variable numérica
    const datasetSelect = await screen.findByLabelText("Seleccionar dataset");
    // La lista de datasets se carga con debounce (250 ms): esperar a que
    // exista la opción del dataset 7 antes de hacer change.
    await waitFor(() => {
      expect(datasetSelect.querySelectorAll("option").length).toBeGreaterThan(
        1,
      );
    });
    fireEvent.change(datasetSelect, { target: { value: "7" } });

    const variableSelect = await screen.findByLabelText("Seleccionar variable");
    await screen.findByText("monto_venta · Continua");
    fireEvent.change(variableSelect, { target: { value: "11" } });

    fireEvent.click(screen.getByRole("button", { name: /calcular/i }));

    expect(await screen.findByText("Media aritmética")).toBeInTheDocument();
    const mediaCard = screen.getByText("Media aritmética").closest("article");
    expect(mediaCard?.textContent).toContain("40");

    const medianCard = screen.getByText("Mediana").closest("article");
    expect(medianCard?.textContent).toContain("30");

    const comparisonCard = screen
      .getByText("Comparación")
      .closest("article");
    expect(comparisonCard?.textContent).toContain("Media > Mediana");

    const meanCall = fetchMock.mock.calls.find(([url, init]) =>
      String(url).includes("/api/analyses/mean-median") &&
      (init as RequestInit)?.method === "POST",
    );
    expect(meanCall).toBeTruthy();
    expect(
      JSON.parse(String((meanCall?.[1] as RequestInit).body)),
    ).toEqual({ variable_id: 11 });
  });

  it("calcula el posterior del Teorema de Bayes con explicación", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        const path = String(url);
        const method = init?.method ?? "GET";

        if (method === "POST" && path.includes("/api/analyses/bayes")) {
          return Promise.resolve(jsonResponse(bayesResult, 201));
        }
        if (path.includes("/api/analyses")) {
          return Promise.resolve(jsonResponse(emptyPage));
        }
        if (path.includes("/api/datasets")) {
          return Promise.resolve(jsonResponse(datasetPage));
        }
        return Promise.resolve(jsonResponse(null, 404));
      }),
    );

    mount();

    fireEvent.click(await screen.findByRole("button", { name: /análisis/i }));
    fireEvent.click(screen.getByRole("button", { name: /bayes/i }));

    fireEvent.change(await screen.findByPlaceholderText("ej. 0.01"), {
      target: { value: "0.01" },
    });
    fireEvent.change(screen.getByPlaceholderText("ej. 0.9"), {
      target: { value: "0.9" },
    });
    fireEvent.change(screen.getByPlaceholderText("ej. 0.42"), {
      target: { value: "0.207" },
    });

    fireEvent.click(screen.getByRole("button", { name: /calcular/i }));

    expect(await screen.findByText("Posterior P(A|B)")).toBeInTheDocument();
    const posteriorCard = screen
      .getByText("Posterior P(A|B)")
      .closest("article");
    expect(posteriorCard?.textContent).toContain("0.043478");
    expect(
      await screen.findByText(/P\(A\|B\) = \[P\(A\) · P\(B\|A\)\]/),
    ).toBeInTheDocument();
  });

  it("consulta el historial de análisis almacenados", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        const path = String(url);
        if (path.includes("/api/analyses")) {
          return Promise.resolve(
            jsonResponse({
              items: [meanMedianResult, bayesResult],
              total: 2,
              page: 1,
              page_size: 10,
            }),
          );
        }
        return Promise.resolve(jsonResponse(emptyPage));
      }),
    );

    mount();

    fireEvent.click(await screen.findByRole("button", { name: /historial/i }));

    expect(
      await screen.findByText("2 análisis registrados"),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Media 40 · Mediana 30"),
    ).toBeInTheDocument();
    expect(screen.getByText("P(A|B) = 0.043478")).toBeInTheDocument();

    // Detalle del análisis
    fireEvent.click(screen.getAllByText("Ver detalle")[0]);
    await waitFor(() =>
      expect(screen.getByText(/Análisis #101/)).toBeInTheDocument(),
    );
    expect(screen.getByText("comparison")).toBeInTheDocument();
    expect(screen.getByText("mean")).toBeInTheDocument();
  });
});
