import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Package,
  Pencil,
  RefreshCw,
  Search,
} from "lucide-react";
import Modal from "../components/Modal";
import { useSearch } from "../context/search-context";
import { api, ApiError } from "../lib/api";
import type {
  InventoryItem,
  InventoryMovement,
  InventoryMovementInput,
  Page,
} from "../types";
import { formatDate } from "../utils/format";

const PAGE_SIZE = 10;

type Tab = "stock" | "movimientos";

const emptyMovement = {
  product_id: "",
  movement_type: "entrada" as const,
  quantity: "",
  reason: "",
};

export default function InventoryPage() {
  const { search, setSearch } = useSearch();
  const [tab, setTab] = useState<Tab>("stock");

  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<InventoryItem> | null>(null);
  const [movements, setMovements] = useState<Page<InventoryMovement> | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [typeFilter, setTypeFilter] = useState("");

  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(emptyMovement);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const [productList, setProductList] = useState<InventoryItem[]>([]);

  const loadStock = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<InventoryItem>>("/inventory", {
        query: {
          search: search.trim() || undefined,
          low_stock_only: lowStockOnly,
          page,
          page_size: PAGE_SIZE,
        },
      });
      setData(result);

      if (result.items.length === 0 && result.page > 1 && result.total > 0) {
        setPage(Math.max(1, Math.ceil(result.total / result.page_size)));
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo cargar el inventario.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, search, lowStockOnly]);


  const loadProductList = useCallback(async () => {
  try {
    const result = await api.get<Page<InventoryItem>>("/inventory", {
      query: { page: 1, page_size: 100 },
    });
    setProductList(result.items);
  } catch {
    /* el error se muestra en loadStock */
  }
}, []);

  const loadMovements = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<InventoryMovement>>(
        "/inventory/movements",
        {
          query: {
            movement_type: typeFilter || undefined,
            page,
            page_size: PAGE_SIZE,
          },
        },
      );
      setMovements(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar los movimientos.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (tab === "stock") void loadStock();
      else void loadMovements();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [tab, loadStock, loadMovements]);

  useEffect(() => {
  const timer = window.setTimeout(loadProductList, 0);
  return () => window.clearTimeout(timer);
}, [loadProductList]);

  async function handleMovementSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    if (!form.product_id) {
      setFormError("Selecciona un producto.");
      return;
    }

    setSubmitting(true);

    const payload: InventoryMovementInput = {
      product_id: Number(form.product_id),
      movement_type: form.movement_type,
      quantity: Number(form.quantity),
      reason: form.reason.trim() || null,
    };

    try {
      const result = await api.post<{
        product_name: string;
        movement_type: string;
        quantity: string;
        previous_quantity: string;
        new_quantity: string;
      }>("/inventory/movements", payload);

      setLastResult(
        `${result.movement_type.toUpperCase()} de ${result.quantity} en ` +
          `${result.product_name}: ${result.previous_quantity} → ` +
          `${result.new_quantity}`,
      );
      setModal(false);
      setForm(emptyMovement);
      await loadStock();
      if (tab === "movements") await loadMovements();
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo registrar el movimiento.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;

  const movementPages = movements
    ? Math.max(1, Math.ceil(movements.total / movements.page_size))
    : 1;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            GESTIÓN COMERCIAL
          </div>
          <h1>Inventario</h1>
          <p>Existencias por producto, entradas, salidas y trazabilidad.</p>
        </div>
        <div className="heading-actions">
          <button
            className="button-secondary"
            onClick={() =>
              tab === "stock" ? loadStock() : loadMovements()
            }
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
          <button
            className="button-primary"
            onClick={() => {
              setFormError(null);
              setLastResult(null);
              setModal(true);
            }}
          >
            <ArrowDownToLine size={17} />
            Nuevo movimiento
          </button>
        </div>
      </section>

      <div className="tabs">
        <button
          className={`tab ${tab === "stock" ? "tab-active" : ""}`}
          onClick={() => {
            setTab("stock");
            setPage(1);
          }}
        >
          <Package size={16} /> Stock
        </button>
        <button
          className={`tab ${tab === "movimientos" ? "tab-active" : ""}`}
          onClick={() => {
            setTab("movimientos");
            setPage(1);
          }}
        >
          <ArrowUpFromLine size={16} /> Movimientos
        </button>
      </div>

      {lastResult && (
        <div className="form-alert form-alert-block" role="status">
          {lastResult}
        </div>
      )}

      <section className="panel data-panel">
        <div className="panel-header data-toolbar">
          <div>
            <h3>
              {tab === "stock" ? "Existencias" : "Historial de movimientos"}
            </h3>
            <p>
              {tab === "stock"
                ? data
                  ? `${data.total} producto${data.total === 1 ? "" : "s"}`
                  : "Cargando..."
                : movements
                  ? `${movements.total} movimiento${
                      movements.total === 1 ? "" : "s"
                    }`
                  : "Cargando..."}
            </p>
          </div>
          <div className="toolbar-controls">
            {tab === "movimientos" && (
              <select
                className="form-input"
                value={typeFilter}
                onChange={(event) => {
                  setTypeFilter(event.target.value);
                  setPage(1);
                }}
                aria-label="Filtrar por tipo"
              >
                <option value="">Todos los tipos</option>
                <option value="entrada">Entradas</option>
                <option value="salida">Salidas</option>
                <option value="ajuste">Ajustes</option>
              </select>
            )}
            <label className="search-box">
              <Search size={17} />
              <input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                placeholder={
                  tab === "stock"
                    ? "Buscar producto o SKU..."
                    : "Buscar producto..."
                }
                aria-label="Buscar"
              />
            </label>
          </div>
        </div>

        <div className="table-scroll">
          <table className="transactions-table">
            {tab === "stock" ? (
              <>
                <thead>
                  <tr>
                    <th>PRODUCTO</th>
                    <th>CATEGORÍA</th>
                    <th>STOCK</th>
                    <th>MÍNIMO</th>
                    <th>ESTADO</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && !data && (
                    <tr>
                      <td colSpan={5} className="table-state">
                        <Loader2 size={19} className="spin" /> Cargando
                        inventario...
                      </td>
                    </tr>
                  )}

                  {!loading && error && (
                    <tr>
                      <td
                        colSpan={5}
                        className="table-state table-state-error"
                      >
                        {error}
                      </td>
                    </tr>
                  )}

                  {!loading && !error && data && data.items.length === 0 && (
                    <tr>
                      <td colSpan={5} className="table-state">
                        <Package size={19} /> Sin resultados.
                      </td>
                    </tr>
                  )}

                  {data?.items.map((item) => (
                    <tr key={item.product_id}>
                      <td>
                        <div className="customer-cell">
                          <div className="customer-avatar avatar-cyan">
                            <Package size={15} />
                          </div>
                          <div className="customer-copy">
                            <strong>{item.product_name}</strong>
                            <span>{item.sku}</span>
                          </div>
                        </div>
                      </td>
                      <td>{item.category_name ?? "Sin categoría"}</td>
                      <td className="amount-cell">
                        {item.quantity_on_hand}
                      </td>
                      <td className="amount-cell">
                        {item.minimum_quantity}
                      </td>
                      <td>
                        <span
                          className={`status ${
                            item.low_stock
                              ? "status-pendiente"
                              : "status-completada"
                          }`}
                        >
                          <i />
                          {item.low_stock ? "Stock bajo" : "Óptimo"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </>
            ) : (
              <>
                <thead>
                  <tr>
                    <th>FECHA</th>
                    <th>PRODUCTO</th>
                    <th>TIPO</th>
                    <th>CANTIDAD</th>
                    <th>MOTIVO</th>
                    <th>VENTA</th>
                  </tr>
                </thead>
                <tbody>
                  {loading && !movements && (
                    <tr>
                      <td colSpan={6} className="table-state">
                        <Loader2 size={19} className="spin" /> Cargando
                        movimientos...
                      </td>
                    </tr>
                  )}

                  {!loading && error && (
                    <tr>
                      <td
                        colSpan={6}
                        className="table-state table-state-error"
                      >
                        {error}
                      </td>
                    </tr>
                  )}

                  {!loading &&
                    !error &&
                    movements &&
                    movements.items.length === 0 && (
                      <tr>
                        <td colSpan={6} className="table-state">
                          Aún no hay movimientos.
                        </td>
                      </tr>
                    )}

                  {movements?.items.map((movement) => (
                    <tr key={movement.id}>
                      <td className="date-cell">
                        {formatDate(movement.created_at)}
                      </td>
                      <td>
                        <strong>{movement.product_name}</strong>
                      </td>
                      <td>
                        <span
                          className={`status ${
                            movement.movement_type === "entrada"
                              ? "status-completada"
                              : movement.movement_type === "salida"
                                ? "status-pendiente"
                                : "status-cancelada"
                          }`}
                        >
                          <i />
                          {movement.movement_type}
                        </span>
                      </td>
                      <td className="amount-cell">{movement.quantity}</td>
                      <td>{movement.reason ?? "—"}</td>
                      <td>{movement.sale_id ? `#${movement.sale_id}` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </>
            )}
          </table>
        </div>

        <div className="table-footer">
          <label className="checkbox-inline">
            {tab === "stock" && (
              <input
                type="checkbox"
                checked={lowStockOnly}
                onChange={(event) => {
                  setLowStockOnly(event.target.checked);
                  setPage(1);
                }}
              />
            )}
            <span>
              {tab === "stock" ? "Solo stock bajo" : ""}
            </span>
          </label>

          <div className="pagination">
            <button
              className="icon-button"
              disabled={page <= 1}
              onClick={() => setPage((value) => value - 1)}
              aria-label="Página anterior"
            >
              <ChevronLeft size={17} />
            </button>
            <span>
              Página {page} de{" "}
              {tab === "stock" ? totalPages : movementPages}
            </span>
            <button
              className="icon-button"
              disabled={
                page >= (tab === "stock" ? totalPages : movementPages)
              }
              onClick={() => setPage((value) => value + 1)}
              aria-label="Página siguiente"
            >
              <ChevronRight size={17} />
            </button>
          </div>
        </div>
      </section>

      {modal && (
        <Modal
          title="Nuevo movimiento de inventario"
          onClose={() => setModal(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setModal(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={handleMovementSubmit}
                disabled={submitting}
              >
                {submitting ? "Guardando..." : "Registrar"}
              </button>
            </>
          }
        >
          <form className="form-grid" onSubmit={handleMovementSubmit}>
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field form-field-full">
              <span>Producto *</span>
              <select
                className="form-input"
                value={form.product_id}
                onChange={(event) =>
                  setForm({ ...form, product_id: event.target.value })
                }
                required
              >
                <option value="">
                  {productList.length === 0
                    ? "Cargando productos..."
                    : "Selecciona un producto..."}
                </option>
                {productList.map((item) => (
                  <option key={item.product_id} value={item.product_id}>
                    {item.product_name} · stock {item.quantity_on_hand}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Tipo *</span>
              <select
                className="form-input"
                value={form.movement_type}
                onChange={(event) =>
                  setForm({
                    ...form,
                    movement_type: event.target
                      .value as InventoryMovementInput["movement_type"],
                  })
                }
              >
                <option value="entrada">Entrada (+)</option>
                <option value="salida">Salida (−)</option>
                <option value="ajuste">Ajuste (valor absoluto)</option>
              </select>
            </label>

            <label className="form-field">
              <span>
                {form.movement_type === "ajuste"
                  ? "Nuevo stock *"
                  : "Cantidad *"}
              </span>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.001"
                value={form.quantity}
                onChange={(event) =>
                  setForm({ ...form, quantity: event.target.value })
                }
                required
              />
            </label>

            <label className="form-field form-field-full">
              <span>Motivo</span>
              <input
                className="form-input"
                value={form.reason}
                onChange={(event) =>
                  setForm({ ...form, reason: event.target.value })
                }
                maxLength={255}
                placeholder="Opcional"
              />
            </label>

            <button type="submit" className="hidden-submit" aria-hidden="true" />
          </form>
        </Modal>
      )}
    </>
  );
}