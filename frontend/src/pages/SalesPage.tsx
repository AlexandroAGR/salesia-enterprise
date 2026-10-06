import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  Minus,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
  Trash2,
} from "lucide-react";
import Modal from "../components/Modal";
import { useSearch } from "../context/search-context";
import { api, ApiError } from "../lib/api";
import type {
  Customer,
  InventoryItem,
  Page,
  PaymentMethod,
  Sale,
  SaleDetail,
  SaleInput,
} from "../types";
import { formatDate, money } from "../utils/format";

const PAGE_SIZE = 10;
const TAX_RATE = 0.18;

type Tab = "historial" | "nueva";

type CartItem = {
  product_id: number;
  name: string;
  sku: string;
  unit_price: string;
  quantity: string;
  discount: string;
  stock: string;
};

const round2 = (value: number) => Math.round(value * 100) / 100;

const statusMeta: Record<Sale["status"], { label: string; cls: string }> = {
  draft: { label: "Borrador", cls: "status-pendiente" },
  pending: { label: "Pendiente", cls: "status-pendiente" },
  completed: { label: "Completada", cls: "status-completada" },
  cancelled: { label: "Cancelada", cls: "status-cancelada" },
  refunded: { label: "Reembolsada", cls: "status-cancelada" },
};

export default function SalesPage() {
  const { search, setSearch } = useSearch();
  const [tab, setTab] = useState<Tab>("historial");

  // --- historial ---
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Sale> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  // --- detalle ---
  const [detail, setDetail] = useState<SaleDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // --- datos auxiliares ---
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [auxError, setAuxError] = useState<string | null>(null);

  // --- nueva venta ---
  const [cart, setCart] = useState<CartItem[]>([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [cartError, setCartError] = useState<string | null>(null);
  const [customerId, setCustomerId] = useState("");
  const [saleDiscount, setSaleDiscount] = useState("0");
  const [paymentMethodId, setPaymentMethodId] = useState("");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // ---------------------------------------------------------------
  // Carga de datos
  // ---------------------------------------------------------------
  const loadSales = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<Sale>>("/sales", {
        query: {
          search: search.trim() || undefined,
          status: statusFilter || undefined,
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
          : "No se pudieron cargar las ventas.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  const loadAux = useCallback(async () => {
    setAuxError(null);

    try {
      const [inv, cust, pay] = await Promise.all([
        api.get<Page<InventoryItem>>("/inventory", {
          query: { page: 1, page_size: 100 },
        }),
        api.get<Page<Customer>>("/customers", {
          query: { page: 1, page_size: 100 },
        }),
        api.get<PaymentMethod[]>("/payment-methods"),
      ]);

      setInventory(inv.items);
      setCustomers(cust.items);
      setMethods(pay);
    } catch (caught) {
      setAuxError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar los datos auxiliares.",
      );
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(loadSales, 0);
    return () => window.clearTimeout(timer);
  }, [loadSales]);

  useEffect(() => {
    const timer = window.setTimeout(loadSales, 250);
    return () => window.clearTimeout(timer);
  }, [loadSales]);

  useEffect(() => {
    const timer = window.setTimeout(loadAux, 0);
    return () => window.clearTimeout(timer);
  }, [loadAux]);

  // ---------------------------------------------------------------
  // Carrito
  // ---------------------------------------------------------------
  function addToCart() {
    const item = inventory.find(
      (entry) => entry.product_id === Number(selectedProduct),
    );
    if (!item) return;

    if (cart.some((entry) => entry.product_id === item.product_id)) {
      setCartError(`'${item.product_name}' ya está en el carrito.`);
      return;
    }

    setCartError(null);
    setCart((current) => [
      ...current,
      {
        product_id: item.product_id,
        name: item.product_name,
        sku: item.sku,
        unit_price: "0",
        quantity: "1",
        discount: "0",
        stock: item.quantity_on_hand,
      },
    ]);
    setSelectedProduct("");

    // Precio del producto desde el catálogo
    void (async () => {
      try {
        const product = await api.get<{ unit_price: string }>(
          `/products/${item.product_id}`,
        );
        setCart((current) =>
          current.map((entry) =>
            entry.product_id === item.product_id
              ? { ...entry, unit_price: product.unit_price }
              : entry,
          ),
        );
      } catch {
        /* el usuario puede escribir el precio a mano si falla */
      }
    })();
  }

  function updateCartItem(productId: number, patch: Partial<CartItem>) {
    setCart((current) =>
      current.map((entry) =>
        entry.product_id === productId ? { ...entry, ...patch } : entry,
      ),
    );
  }

  function removeCartItem(productId: number) {
    setCart((current) =>
      current.filter((entry) => entry.product_id !== productId),
    );
  }

  const totals = useMemo(() => {
    const gross = cart.reduce(
      (sum, item) =>
        sum + Number(item.unit_price || 0) * Number(item.quantity || 0),
      0,
    );
    const lineDiscounts = cart.reduce(
      (sum, item) => sum + Number(item.discount || 0),
      0,
    );
    const discount = round2(lineDiscounts + Number(saleDiscount || 0));
    const base = round2(Math.max(gross - discount, 0));
    const tax = round2(base * TAX_RATE);

    return {
      gross: round2(gross),
      discount,
      tax,
      total: round2(base + tax),
    };
  }, [cart, saleDiscount]);

  // ---------------------------------------------------------------
  // Envío
  // ---------------------------------------------------------------
  async function handleCreateSale(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    if (cart.length === 0) {
      setFormError("Agrega al menos un producto al carrito.");
      return;
    }

    for (const item of cart) {
      const quantity = Number(item.quantity);

      if (!Number.isFinite(quantity) || quantity <= 0) {
        setFormError(`Cantidad inválida para '${item.name}'.`);
        return;
      }
      if (quantity > Number(item.stock)) {
        setFormError(
          `Stock insuficiente de '${item.name}' (disponible: ${item.stock}).`,
        );
        return;
      }
    }

    setSubmitting(true);

    const payload: SaleInput = {
      customer_id: customerId ? Number(customerId) : null,
      items: cart.map((item) => ({
        product_id: item.product_id,
        quantity: Number(item.quantity),
        discount_amount: Number(item.discount || 0),
      })),
      discount_amount: Number(saleDiscount || 0),
      tax_rate: TAX_RATE,
      payment: paymentMethodId
        ? {
            payment_method_id: Number(paymentMethodId),
            reference: reference.trim() || null,
          }
        : null,
      notes: notes.trim() || null,
    };

    try {
      const created = await api.post<SaleDetail>("/sales", payload);

      // limpiar formulario y abrir el detalle
      setCart([]);
      setCustomerId("");
      setSaleDiscount("0");
      setPaymentMethodId("");
      setReference("");
      setNotes("");
      setTab("historial");
      setDetail(created);
      await loadSales();
      await loadAux(); // el stock cambió
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo registrar la venta.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function openDetail(saleId: number) {
    setDetailLoading(true);
    try {
      const result = await api.get<SaleDetail>(`/sales/${saleId}`);
      setDetail(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo cargar el detalle.",
      );
    } finally {
      setDetailLoading(false);
    }
  }

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;

  // ---------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            GESTIÓN COMERCIAL
          </div>
          <h1>Ventas</h1>
          <p>
            Registro de ventas con detalle, descuentos, impuestos, pagos y
            actualización automática de inventario.
          </p>
        </div>
        <div className="heading-actions">
          <button className="button-secondary" onClick={loadSales}>
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
          <button
            className="button-primary"
            onClick={() => {
              setFormError(null);
              setCartError(null);
              setTab("nueva");
            }}
          >
            <Plus size={17} />
            Nueva venta
          </button>
        </div>
      </section>

      <div className="tabs">
        <button
          className={`tab ${tab === "historial" ? "tab-active" : ""}`}
          onClick={() => setTab("historial")}
        >
          <ShoppingCart size={16} /> Historial
        </button>
        <button
          className={`tab ${tab === "nueva" ? "tab-active" : ""}`}
          onClick={() => setTab("nueva")}
        >
          <Plus size={16} /> Nueva venta
        </button>
      </div>

      {tab === "historial" ? (
        <section className="panel data-panel">
          <div className="panel-header data-toolbar">
            <div>
              <h3>Ventas registradas</h3>
              <p>
                {data
                  ? `${data.total} registro${data.total === 1 ? "" : "s"}`
                  : "Cargando..."}
              </p>
            </div>
            <div className="toolbar-controls">
              <select
                className="form-input"
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value);
                  setPage(1);
                }}
                aria-label="Filtrar por estado"
              >
                <option value="">Todos los estados</option>
                <option value="completed">Completadas</option>
                <option value="pending">Pendientes</option>
                <option value="cancelled">Canceladas</option>
                <option value="refunded">Reembolsadas</option>
              </select>
              <label className="search-box">
                <Search size={17} />
                <input
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                  placeholder="Buscar por correlativo..."
                  aria-label="Buscar ventas"
                />
              </label>
            </div>
          </div>

          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>VENTA</th>
                  <th>CLIENTE</th>
                  <th>FECHA</th>
                  <th>ESTADO</th>
                  <th>TOTAL</th>
                  <th>ACCIONES</th>
                </tr>
              </thead>
              <tbody>
                {loading && !data && (
                  <tr>
                    <td colSpan={6} className="table-state">
                      <Loader2 size={19} className="spin" /> Cargando ventas...
                    </td>
                  </tr>
                )}

                {!loading && error && (
                  <tr>
                    <td colSpan={6} className="table-state table-state-error">
                      {error}
                    </td>
                  </tr>
                )}

                {!loading && !error && data && data.items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="table-state">
                      <ShoppingCart size={19} />
                      {search
                        ? `Sin coincidencias para "${search}".`
                        : "Aún no hay ventas registradas."}
                    </td>
                  </tr>
                )}

                {data?.items.map((sale) => {
                  const meta = statusMeta[sale.status];

                  return (
                    <tr key={sale.id}>
                      <td>
                        <div className="customer-cell">
                          <div className="customer-avatar avatar-cyan">
                            <ShoppingCart size={15} />
                          </div>
                          <div className="customer-copy">
                            <strong>{sale.sale_number}</strong>
                            <span>{sale.currency}</span>
                          </div>
                        </div>
                      </td>
                      <td>{sale.customer_name ?? "Consumidor final"}</td>
                      <td className="date-cell">{formatDate(sale.sold_at)}</td>
                      <td>
                        <span className={`status ${meta.cls}`}>
                          <i />
                          {meta.label}
                        </span>
                      </td>
                      <td className="amount-cell">
                        {money(sale.total_amount)}
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="icon-button"
                            aria-label="Ver detalle"
                            onClick={() => openDetail(sale.id)}
                          >
                            <Eye size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="table-footer">
            <span />
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
                Página {page} de {totalPages}
              </span>
              <button
                className="icon-button"
                disabled={page >= totalPages}
                onClick={() => setPage((value) => value + 1)}
                aria-label="Página siguiente"
              >
                <ChevronRight size={17} />
              </button>
            </div>
          </div>
        </section>
      ) : (
        <form className="panel" onSubmit={handleCreateSale}>
          <div className="panel-header data-toolbar">
            <div>
              <h3>Nueva venta</h3>
              <p>Los totales se calculan automáticamente.</p>
            </div>
          </div>

          {auxError && (
            <div className="form-alert form-alert-block" role="alert">
              {auxError}
            </div>
          )}
          {formError && (
            <div className="form-alert" role="alert">
              {formError}
            </div>
          )}

          {/* --- selector de producto --- */}
          <div className="toolbar-controls" style={{ marginBottom: 16 }}>
            <select
              className="form-input"
              value={selectedProduct}
              onChange={(event) => setSelectedProduct(event.target.value)}
              aria-label="Producto a agregar"
            >
              <option value="">Selecciona un producto...</option>
              {inventory.map((item) => (
                <option
                  key={item.product_id}
                  value={item.product_id}
                  disabled={Number(item.quantity_on_hand) <= 0}
                >
                  {item.product_name} · stock {item.quantity_on_hand}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="button-secondary"
              onClick={addToCart}
              disabled={!selectedProduct}
            >
              <Plus size={16} /> Agregar
            </button>
          </div>

          {cartError && (
            <div className="form-alert" role="alert">
              {cartError}
            </div>
          )}

          {/* --- carrito --- */}
          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>PRODUCTO</th>
                  <th>PRECIO</th>
                  <th>CANT.</th>
                  <th>DESCUENTO</th>
                  <th>IMPORTE</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {cart.length === 0 && (
                  <tr>
                    <td colSpan={6} className="table-state">
                      El carrito está vacío.
                    </td>
                  </tr>
                )}

                {cart.map((item) => {
                  const lineTotal = round2(
                    Number(item.unit_price || 0) * Number(item.quantity || 0) -
                      Number(item.discount || 0),
                  );

                  return (
                    <tr key={item.product_id}>
                      <td>
                        <strong>{item.name}</strong>
                        <br />
                        <span className="muted">{item.sku}</span>
                      </td>
                      <td>
                        <input
                          className="form-input"
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.unit_price}
                          onChange={(event) =>
                            updateCartItem(item.product_id, {
                              unit_price: event.target.value,
                            })
                          }
                          aria-label="Precio unitario"
                        />
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="icon-button"
                            aria-label="Restar"
                            onClick={() =>
                              updateCartItem(item.product_id, {
                                quantity: String(
                                  Math.max(
                                    1,
                                    Number(item.quantity || 1) - 1,
                                  ),
                                ),
                              })
                            }
                          >
                            <Minus size={15} />
                          </button>
                          <input
                            className="form-input"
                            style={{ width: 70, textAlign: "center" }}
                            type="number"
                            min="1"
                            max={item.stock}
                            value={item.quantity}
                            onChange={(event) =>
                              updateCartItem(item.product_id, {
                                quantity: event.target.value,
                              })
                            }
                            aria-label="Cantidad"
                          />
                          <button
                            type="button"
                            className="icon-button"
                            aria-label="Sumar"
                            onClick={() =>
                              updateCartItem(item.product_id, {
                                quantity: String(
                                  Math.min(
                                    Number(item.stock),
                                    Number(item.quantity || 1) + 1,
                                  ),
                                ),
                              })
                            }
                          >
                            <Plus size={15} />
                          </button>
                        </div>
                      </td>
                      <td>
                        <input
                          className="form-input"
                          type="number"
                          min="0"
                          step="0.01"
                          value={item.discount}
                          onChange={(event) =>
                            updateCartItem(item.product_id, {
                              discount: event.target.value,
                            })
                          }
                          aria-label="Descuento de línea"
                        />
                      </td>
                      <td className="amount-cell">{money(lineTotal)}</td>
                      <td>
                        <button
                          type="button"
                          className="icon-button"
                          aria-label="Quitar"
                          onClick={() => removeCartItem(item.product_id)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* --- datos de la venta --- */}
          <div className="form-grid" style={{ marginTop: 16 }}>
            <label className="form-field">
              <span>Cliente</span>
              <select
                className="form-input"
                value={customerId}
                onChange={(event) => setCustomerId(event.target.value)}
              >
                <option value="">Consumidor final</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.full_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Descuento adicional (S/)</span>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.01"
                value={saleDiscount}
                onChange={(event) => setSaleDiscount(event.target.value)}
              />
            </label>

            <label className="form-field">
              <span>Método de pago</span>
              <select
                className="form-input"
                value={paymentMethodId}
                onChange={(event) => setPaymentMethodId(event.target.value)}
              >
                <option value="">Sin pago (pendiente)</option>
                {methods.map((method) => (
                  <option key={method.id} value={method.id}>
                    {method.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Referencia</span>
              <input
                className="form-input"
                value={reference}
                onChange={(event) => setReference(event.target.value)}
                maxLength={120}
                placeholder="Opcional"
                disabled={!paymentMethodId}
              />
            </label>

            <label className="form-field form-field-full">
              <span>Notas</span>
              <textarea
                className="form-input"
                rows={2}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Opcional"
              />
            </label>
          </div>

          {/* --- resumen --- */}
          <div className="summary-box" style={{ marginTop: 16 }}>
            <div>
              <span>Subtotal</span>
              <strong>{money(totals.gross)}</strong>
            </div>
            <div>
              <span>Descuentos</span>
              <strong>− {money(totals.discount)}</strong>
            </div>
            <div>
              <span>IGV (18%)</span>
              <strong>{money(totals.tax)}</strong>
            </div>
            <div>
              <span>Total</span>
              <strong>{money(totals.total)}</strong>
            </div>
          </div>

          <div className="modal-footer" style={{ marginTop: 16 }}>
            <button
              type="button"
              className="button-secondary"
              onClick={() => setTab("historial")}
              disabled={submitting}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="button-primary"
              disabled={submitting || cart.length === 0}
            >
              {submitting ? "Registrando..." : "Registrar venta"}
            </button>
          </div>
        </form>
      )}

      {/* --- modal de detalle --- */}
      {(detail || detailLoading) && (
        <Modal
          title={detail ? `Venta ${detail.sale_number}` : "Cargando..."}
          onClose={() => setDetail(null)}
          footer={
            <button
              className="button-primary"
              onClick={() => setDetail(null)}
            >
              Cerrar
            </button>
          }
        >
          {detailLoading && !detail && (
            <div className="table-state">
              <Loader2 size={19} className="spin" /> Cargando detalle...
            </div>
          )}

          {detail && (
            <>
              <div className="form-grid">
                <div className="form-field">
                  <span>Cliente</span>
                  <strong>
                    {detail.customer_name ?? "Consumidor final"}
                  </strong>
                </div>
                <div className="form-field">
                  <span>Fecha</span>
                  <strong>{formatDate(detail.sold_at)}</strong>
                </div>
                <div className="form-field">
                  <span>Estado</span>
                  <span className={`status ${statusMeta[detail.status].cls}`}>
                    <i />
                    {statusMeta[detail.status].label}
                  </span>
                </div>
                <div className="form-field">
                  <span>Pago</span>
                  <strong>
                    {detail.payment
                      ? `${detail.payment.payment_method_name} · ${money(detail.payment.amount)}`
                      : "Pendiente"}
                  </strong>
                </div>
              </div>

              <div className="table-scroll" style={{ marginTop: 16 }}>
                <table className="transactions-table">
                  <thead>
                    <tr>
                      <th>PRODUCTO</th>
                      <th>CANT.</th>
                      <th>PRECIO</th>
                      <th>DESC.</th>
                      <th>IMPORTE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.items.map((item) => (
                      <tr key={item.product_id}>
                        <td>{item.product_name}</td>
                        <td>{item.quantity}</td>
                        <td className="amount-cell">
                          {money(item.unit_price)}
                        </td>
                        <td className="amount-cell">
                          {money(item.discount_amount)}
                        </td>
                        <td className="amount-cell">
                          {money(item.line_total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="summary-box" style={{ marginTop: 16 }}>
                <div>
                  <span>Subtotal</span>
                  <strong>{money(detail.subtotal)}</strong>
                </div>
                <div>
                  <span>Descuentos</span>
                  <strong>− {money(detail.discount_amount)}</strong>
                </div>
                <div>
                  <span>IGV</span>
                  <strong>{money(detail.tax_amount)}</strong>
                </div>
                <div>
                  <span>Total</span>
                  <strong>{money(detail.total_amount)}</strong>
                </div>
              </div>
            </>
          )}
        </Modal>
      )}
    </>
  );
}