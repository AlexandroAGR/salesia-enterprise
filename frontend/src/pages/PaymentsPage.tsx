import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  Banknote,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Loader2,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import Modal from "../components/Modal";
import { useSearch } from "../context/search-context";
import { useAuth } from "../context/auth-context";
import { api, ApiError } from "../lib/api";
import { can } from "../permissions";
import type { Page, Payment, PaymentMethod, Sale } from "../types";
import { formatDate, money } from "../utils/format";

const PAGE_SIZE = 10;

type Tab = "pagos" | "metodos";

const STATUS_LABEL: Record<Payment["status"], string> = {
  pending: "Pendiente",
  paid: "Pagado",
  failed: "Fallido",
  refunded: "Reembolsado",
};

const STATUS_CLASS: Record<Payment["status"], string> = {
  pending: "status-pendiente",
  paid: "status-completada",
  failed: "status-cancelada",
  refunded: "status-cancelada",
};

const emptyForm = {
  sale_id: "",
  payment_method_id: "",
  amount: "",
  reference: "",
};

export default function PaymentsPage() {
  const { search, setSearch } = useSearch();
  const { user } = useAuth();
  const canWrite = can(user?.role, "payments:create");

  const [tab, setTab] = useState<Tab>("pagos");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Payment> | null>(null);
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  // Ventas con saldo pendiente, para el selector del formulario.
  const [pendingSales, setPendingSales] = useState<Sale[]>([]);
  const [salesLoading, setSalesLoading] = useState(false);

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;

  const loadMethods = useCallback(async () => {
    try {
      const result = await api.get<PaymentMethod[]>("/payment-methods");
      setMethods(result);
    } catch {
      setMethods([]);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<Payment>>("/payments", {
        query: {
          search: search.trim() || undefined,
          status: statusFilter || undefined,
          page,
          page_size: PAGE_SIZE,
        },
      });
      setData(result);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Error de conexión con el servidor.",
      );
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, page]);

  const loadPendingSales = useCallback(async () => {
    setSalesLoading(true);
    try {
      const result = await api.get<Page<Sale>>("/sales", {
        query: { has_balance: true, page_size: 100 },
      });
      setPendingSales(result.items);
    } catch {
      setPendingSales([]);
    } finally {
      setSalesLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(load, 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    const timer = window.setTimeout(loadMethods, 0);
    return () => window.clearTimeout(timer);
  }, [loadMethods]);

  const openModal = () => {
    setForm(emptyForm);
    setFormError(null);
    setLastResult(null);
    setModal(true);
    void loadPendingSales();
  };

  const selectedSale = pendingSales.find(
    (sale) => String(sale.id) === form.sale_id,
  );

  const handleSelectSale = (saleId: string) => {
    const sale = pendingSales.find((item) => String(item.id) === saleId);
    setForm({
      ...form,
      sale_id: saleId,
      // Sugerimos el saldo pendiente como importe.
      amount: sale ? sale.balance : "",
    });
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setFormError(null);

    if (!form.sale_id || !form.payment_method_id || !form.amount) {
      setFormError("Selecciona la venta, el método de pago y el importe.");
      return;
    }

    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setFormError("El importe debe ser un número mayor que cero.");
      return;
    }

    if (selectedSale && amount > Number(selectedSale.balance)) {
      setFormError(
        `El importe supera el saldo pendiente (${money(selectedSale.balance)}).`,
      );
      return;
    }

    setSubmitting(true);
    try {
      const created = await api.post<Payment>("/payments", {
        sale_id: Number(form.sale_id),
        payment_method_id: Number(form.payment_method_id),
        amount: form.amount,
        currency: selectedSale?.currency ?? "PEN",
        reference: form.reference.trim() || null,
      });
      setModal(false);
      setLastResult(
        `Pago de ${money(created.amount)} registrado para ${
          created.sale_number ?? `la venta #${created.sale_id}`
        }.`,
      );
      setPage(1);
      await load();
      void loadPendingSales();
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo registrar el pago.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const methodName = (id: number) =>
    methods.find((method) => method.id === id)?.name ?? `Método #${id}`;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            GESTIÓN COMERCIAL
          </div>
          <h1>Pagos</h1>
          <p>Cobros, métodos de pago y conciliación con cada venta.</p>
        </div>
        <div className="heading-actions">
          <button
            className="button-secondary"
            onClick={() => void load()}
            disabled={loading}
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
          {canWrite && (
            <button className="button-primary" onClick={openModal}>
              <Plus size={17} />
              Registrar pago
            </button>
          )}
        </div>
      </section>

      <div className="tabs">
        <button
          className={`tab ${tab === "pagos" ? "tab-active" : ""}`}
          onClick={() => setTab("pagos")}
        >
          <Banknote size={16} /> Pagos
        </button>
        <button
          className={`tab ${tab === "metodos" ? "tab-active" : ""}`}
          onClick={() => setTab("metodos")}
        >
          <CreditCard size={16} /> Métodos de pago
        </button>
      </div>

      {lastResult && (
        <div className="form-alert form-alert-block" role="status">
          {lastResult}
        </div>
      )}

      {tab === "pagos" ? (
        <section className="panel data-panel">
          <div className="panel-header data-toolbar">
            <div>
              <h3>Pagos registrados</h3>
              <p>
                {data
                  ? `${data.total} pago${data.total === 1 ? "" : "s"}`
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
                <option value="paid">Pagados</option>
                <option value="pending">Pendientes</option>
                <option value="failed">Fallidos</option>
                <option value="refunded">Reembolsados</option>
              </select>
              <label className="search-box">
                <Search size={17} />
                <input
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                  placeholder="Buscar venta o referencia..."
                  aria-label="Buscar"
                />
              </label>
            </div>
          </div>

          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>FECHA</th>
                  <th>VENTA</th>
                  <th>MÉTODO</th>
                  <th>REFERENCIA</th>
                  <th>IMPORTE</th>
                  <th>ESTADO</th>
                </tr>
              </thead>
              <tbody>
                {loading && !data && (
                  <tr>
                    <td colSpan={6} className="table-state">
                      <Loader2 size={19} className="spin" /> Cargando pagos...
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
                      <Banknote size={19} /> Sin pagos registrados.
                    </td>
                  </tr>
                )}

                {data?.items.map((payment) => (
                  <tr key={payment.id}>
                    <td className="date-cell">
                      {formatDate(payment.paid_at ?? payment.created_at)}
                    </td>
                    <td>{payment.sale_number ?? `#${payment.sale_id}`}</td>
                    <td>{methodName(payment.payment_method_id)}</td>
                    <td>{payment.reference ?? "—"}</td>
                    <td className="amount-cell">{money(payment.amount)}</td>
                    <td>
                      <span className={`status ${STATUS_CLASS[payment.status]}`}>
                        <i />
                        {STATUS_LABEL[payment.status]}
                      </span>
                    </td>
                  </tr>
                ))}
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
        <section className="panel data-panel">
          <div className="panel-header data-toolbar">
            <div>
              <h3>Métodos de pago</h3>
              <p>
                {methods.length} método{methods.length === 1 ? "" : "s"}{" "}
                disponible{methods.length === 1 ? "" : "s"}
              </p>
            </div>
          </div>

          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>MÉTODO</th>
                  <th>CÓDIGO</th>
                  <th>ESTADO</th>
                </tr>
              </thead>
              <tbody>
                {methods.length === 0 && (
                  <tr>
                    <td colSpan={3} className="table-state">
                      <CreditCard size={19} /> Sin métodos de pago.
                    </td>
                  </tr>
                )}
                {methods.map((method) => (
                  <tr key={method.id}>
                    <td>
                      <div className="customer-cell">
                        <div className="customer-avatar avatar-cyan">
                          <CreditCard size={15} />
                        </div>
                        <div className="customer-copy">
                          <strong>{method.name}</strong>
                        </div>
                      </div>
                    </td>
                    <td>{method.code}</td>
                    <td>
                      <span
                        className={`status ${
                          method.is_active
                            ? "status-completada"
                            : "status-cancelada"
                        }`}
                      >
                        <i />
                        {method.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {modal && (
        <Modal
          title="Registrar pago"
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
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? "Guardando..." : "Registrar"}
              </button>
            </>
          }
        >
          <form className="form-grid" onSubmit={handleSubmit}>
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field form-field-full">
              <span>Venta con saldo pendiente *</span>
              <select
                className="form-input"
                value={form.sale_id}
                onChange={(event) => handleSelectSale(event.target.value)}
                required
                disabled={salesLoading}
              >
                <option value="">
                  {salesLoading
                    ? "Cargando ventas..."
                    : pendingSales.length === 0
                      ? "No hay ventas con saldo pendiente"
                      : "Selecciona una venta..."}
                </option>
                {pendingSales.map((sale) => (
                  <option key={sale.id} value={sale.id}>
                    {sale.sale_number} · saldo {money(sale.balance)}
                  </option>
                ))}
              </select>
            </label>

            {selectedSale && (
              <div className="form-field form-field-full">
                <div className="summary-box">
                  <div>
                    <span>Total de la venta</span>
                    <strong>{money(selectedSale.total_amount)}</strong>
                  </div>
                  <div>
                    <span>Ya pagado</span>
                    <strong>{money(selectedSale.amount_paid)}</strong>
                  </div>
                  <div>
                    <span>Saldo pendiente</span>
                    <strong>{money(selectedSale.balance)}</strong>
                  </div>
                </div>
              </div>
            )}

            <label className="form-field">
              <span>Método de pago *</span>
              <select
                className="form-input"
                value={form.payment_method_id}
                onChange={(event) =>
                  setForm({ ...form, payment_method_id: event.target.value })
                }
                required
              >
                <option value="">
                  {methods.length === 0
                    ? "Cargando métodos..."
                    : "Selecciona un método..."}
                </option>
                {methods.map((method) => (
                  <option key={method.id} value={method.id}>
                    {method.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Importe *</span>
              <input
                className="form-input"
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount}
                onChange={(event) =>
                  setForm({ ...form, amount: event.target.value })
                }
                required
                placeholder="0.00"
              />
            </label>

            <label className="form-field form-field-full">
              <span>Referencia</span>
              <input
                className="form-input"
                value={form.reference}
                onChange={(event) =>
                  setForm({ ...form, reference: event.target.value })
                }
                maxLength={100}
                placeholder="Opcional · p. ej. número de operación"
              />
            </label>

            <button type="submit" className="hidden-submit" aria-hidden="true" />
          </form>
        </Modal>
      )}
    </>
  );
}
