import { useCallback, useEffect, useState, type FormEvent } from "react";import {
  Ban,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  UserRound,
  Users,
} from "lucide-react";
import Modal from "../components/Modal";
import { useSearch } from "../context/search-context";
import { api, ApiError } from "../lib/api";
import { DOCUMENT_TYPES, type Customer, type CustomerInput, type Page } from "../types";
import { formatDate, initials } from "../utils/format";

const PAGE_SIZE = 10;

const emptyForm = {
  full_name: "",
  document_type: "DNI",
  document_number: "",
  email: "",
  phone: "",
  address: "",
};

export default function CustomersPage() {
  const { search, setSearch } = useSearch();

  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Customer> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Customer | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<Customer>>("/customers", {
        query: {
          search: search.trim() || undefined,
          page,
          page_size: PAGE_SIZE,
          include_inactive: includeInactive,
        },
      });
      setData(result);

      // Si los filtros dejaron la página fuera de rango, volvemos a la última válida
      if (result.items.length === 0 && result.page > 1 && result.total > 0) {
        setPage(Math.max(1, Math.ceil(result.total / result.page_size)));
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar los clientes.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, search, includeInactive]);

  useEffect(() => {
    const timer = window.setTimeout(load, 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(customer: Customer) {
    setEditing(customer);
    setForm({
      full_name: customer.full_name,
      document_type: customer.document_type ?? "DNI",
      document_number: customer.document_number ?? "",
      email: customer.email ?? "",
      phone: customer.phone ?? "",
      address: customer.address ?? "",
    });
    setFormError(null);
    setModalOpen(true);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);

    const payload: CustomerInput = {
      full_name: form.full_name.trim(),
      document_type: form.document_type || null,
      document_number: form.document_number.trim() || null,
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      address: form.address.trim() || null,
    };

    try {
      if (editing) {
        await api.patch(`/customers/${editing.id}`, payload);
      } else {
        await api.post("/customers", payload);
      }

      setModalOpen(false);
      await load();
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo guardar el cliente.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(customer: Customer) {
    const confirmed = window.confirm(
      `¿Desactivar al cliente "${customer.full_name}"? Podrás reactivarlo luego.`,
    );

    if (!confirmed) return;

    setDeleting(customer.id);

    try {
      await api.del(`/customers/${customer.id}`);
      await load();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo desactivar el cliente.",
      );
    } finally {
      setDeleting(null);
    }
  }

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1;

  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            GESTIÓN COMERCIAL
          </div>
          <h1>Clientes</h1>
          <p>Registro, historial y comportamiento comercial de tus clientes.</p>
        </div>
        <div className="heading-actions">
          <button className="button-secondary" onClick={load}>
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
          <button className="button-primary" onClick={openCreate}>
            <Plus size={17} />
            Nuevo cliente
          </button>
        </div>
      </section>

      <section className="panel data-panel">
        <div className="panel-header data-toolbar">
          <div>
            <h3>Directorio de clientes</h3>
            <p>
              {data
                ? `${data.total} registro${data.total === 1 ? "" : "s"}`
                : "Cargando..."}
            </p>
          </div>
          <label className="search-box">
            <Search size={17} />
            <input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Buscar por nombre, correo o documento..."
              aria-label="Buscar clientes"
            />
          </label>
        </div>

        <div className="table-scroll">
          <table className="transactions-table">
            <thead>
              <tr>
                <th>CLIENTE</th>
                <th>DOCUMENTO</th>
                <th>TELÉFONO</th>
                <th>REGISTRO</th>
                <th>ESTADO</th>
                <th>ACCIONES</th>
              </tr>
            </thead>
            <tbody>
              {loading && !data && (
                <tr>
                  <td colSpan={6} className="table-state">
                    <Loader2 size={19} className="spin" /> Cargando clientes...
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
                    <UserRound size={19} />
                    {search
                      ? `Sin coincidencias para "${search}".`
                      : "Aún no hay clientes registrados."}
                  </td>
                </tr>
              )}

              {data?.items.map((customer) => (
                <tr key={customer.id}>
                  <td>
                    <div className="customer-cell">
                      <div className="customer-avatar avatar-blue">
                        {initials(customer.full_name)}
                      </div>
                      <div className="customer-copy">
                        <strong>{customer.full_name}</strong>
                        <span>{customer.email ?? "Sin correo"}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    {customer.document_number
                      ? `${customer.document_type ?? ""} ${customer.document_number}`
                      : "—"}
                  </td>
                  <td>{customer.phone ?? "—"}</td>
                  <td className="date-cell">{formatDate(customer.created_at)}</td>
                  <td>
                    <span
                      className={`status ${
                        customer.is_active
                          ? "status-completada"
                          : "status-cancelada"
                      }`}
                    >
                      <i />
                      {customer.is_active ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td>
                    <div className="row-actions">
                      <button
                        className="icon-button"
                        aria-label="Editar cliente"
                        onClick={() => openEdit(customer)}
                      >
                        <Pencil size={16} />
                      </button>
                      {customer.is_active && (
                        <button
                          className="icon-button"
                          aria-label="Desactivar cliente"
                          disabled={deleting === customer.id}
                          onClick={() => handleDelete(customer)}
                        >
                          {deleting === customer.id ? (
                            <Loader2 size={16} className="spin" />
                          ) : (
                            <Trash2 size={16} />
                          )}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table-footer">
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(event) => {
                setIncludeInactive(event.target.checked);
                setPage(1);
              }}
            />
            <span>
              <Ban size={14} /> Incluir inactivos
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

      <section className="panel info-panel">
        <div className="info-icon">
          <Users size={19} />
        </div>
        <div>
          <h3>Flujo empresarial</h3>
          <p>
            Cliente → Pedido → Venta → Pago → Inventario. Cada cliente
            alimentará el módulo Analytics con frecuencia de compra y ticket
            promedio.
          </p>
        </div>
      </section>

      {modalOpen && (
        <Modal
          title={editing ? "Editar cliente" : "Nuevo cliente"}
          onClose={() => setModalOpen(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setModalOpen(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? "Guardando..." : editing ? "Guardar cambios" : "Crear cliente"}
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
              <span>Nombre completo *</span>
              <input
                className="form-input"
                value={form.full_name}
                onChange={(event) =>
                  setForm({ ...form, full_name: event.target.value })
                }
                minLength={2}
                maxLength={160}
                required
                placeholder="Ej. María Fernanda López"
              />
            </label>

            <label className="form-field">
              <span>Tipo de documento</span>
              <select
                className="form-input"
                value={form.document_type}
                onChange={(event) =>
                  setForm({ ...form, document_type: event.target.value })
                }
              >
                {DOCUMENT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Número de documento</span>
              <input
                className="form-input"
                value={form.document_number}
                onChange={(event) =>
                  setForm({ ...form, document_number: event.target.value })
                }
                maxLength={30}
                placeholder="Opcional"
              />
            </label>

            <label className="form-field">
              <span>Correo electrónico</span>
              <input
                className="form-input"
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm({ ...form, email: event.target.value })
                }
                placeholder="cliente@correo.com"
              />
            </label>

            <label className="form-field">
              <span>Teléfono</span>
              <input
                className="form-input"
                value={form.phone}
                onChange={(event) =>
                  setForm({ ...form, phone: event.target.value })
                }
                maxLength={30}
                placeholder="999 888 777"
              />
            </label>

            <label className="form-field form-field-full">
              <span>Dirección</span>
              <input
                className="form-input"
                value={form.address}
                onChange={(event) =>
                  setForm({ ...form, address: event.target.value })
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
