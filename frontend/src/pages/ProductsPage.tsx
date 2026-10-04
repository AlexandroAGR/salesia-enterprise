import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  Ban,
  ChevronLeft,
  ChevronRight,
  FolderTree,
  Loader2,
  Package,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Tag,
  Trash2,
} from "lucide-react";
import Modal from "../components/Modal";
import { useSearch } from "../context/search-context";
import { api, ApiError } from "../lib/api";
import type {
  Category,
  CategoryInput,
  Page,
  Product,
  ProductInput,
} from "../types";
import { formatDate, money } from "../utils/format";

const PAGE_SIZE = 10;

const emptyProduct = {
  sku: "",
  name: "",
  description: "",
  category_id: "",
  unit_price: "",
  cost_price: "0",
};

const emptyCategory = {
  name: "",
  description: "",
};

type Tab = "productos" | "categorias";

export default function ProductsPage() {
  const { search, setSearch } = useSearch();
  const [tab, setTab] = useState<Tab>("productos");

  const [categories, setCategories] = useState<Category[]>([]);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);

  // --- estado de productos ---
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Product> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryId, setCategoryId] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  // --- estado de modales ---
  const [productModal, setProductModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [productForm, setProductForm] = useState(emptyProduct);

  const [categoryModal, setCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [categoryForm, setCategoryForm] = useState(emptyCategory);

  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      const result = await api.get<Category[]>("/categories");
      setCategories(result);
      setCategoriesError(null);
    } catch (caught) {
      setCategoriesError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudieron cargar las categorías.",
      );
    }
  }, []);

  const loadProducts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await api.get<Page<Product>>("/products", {
        query: {
          search: search.trim() || undefined,
          category_id: categoryId || undefined,
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
          : "No se pudieron cargar los productos.",
      );
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryId, includeInactive]);

  useEffect(() => {
    const timer = window.setTimeout(loadCategories, 0);
    return () => window.clearTimeout(timer);
  }, [loadCategories]);

  useEffect(() => {
    const timer = window.setTimeout(loadProducts, 250);
    return () => window.clearTimeout(timer);
  }, [loadProducts]);

  // --- productos ---
  function openProductCreate() {
    setEditingProduct(null);
    setProductForm(emptyProduct);
    setFormError(null);
    setProductModal(true);
  }

  function openProductEdit(product: Product) {
    setEditingProduct(product);
    setProductForm({
      sku: product.sku,
      name: product.name,
      description: product.description ?? "",
      category_id: product.category_id ? String(product.category_id) : "",
      unit_price: product.unit_price,
      cost_price: product.cost_price,
    });
    setFormError(null);
    setProductModal(true);
  }

  async function handleProductSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);

    const payload: ProductInput = {
      sku: productForm.sku.trim(),
      name: productForm.name.trim(),
      description: productForm.description.trim() || null,
      category_id: productForm.category_id
        ? Number(productForm.category_id)
        : null,
      unit_price: productForm.unit_price,
      cost_price: productForm.cost_price || "0",
    };

    try {
      if (editingProduct) {
        await api.patch(`/products/${editingProduct.id}`, payload);
      } else {
        await api.post("/products", payload);
      }

      setProductModal(false);
      await loadProducts();
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo guardar el producto.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleProductDelete(product: Product) {
    const confirmed = window.confirm(
      `¿Desactivar el producto "${product.name}"?`,
    );
    if (!confirmed) return;

    setDeleting(product.id);

    try {
      await api.del(`/products/${product.id}`);
      await loadProducts();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo desactivar el producto.",
      );
    } finally {
      setDeleting(null);
    }
  }

  // --- categorías ---
  function openCategoryCreate() {
    setEditingCategory(null);
    setCategoryForm(emptyCategory);
    setFormError(null);
    setCategoryModal(true);
  }

  function openCategoryEdit(category: Category) {
    setEditingCategory(category);
    setCategoryForm({
      name: category.name,
      description: category.description ?? "",
    });
    setFormError(null);
    setCategoryModal(true);
  }

  async function handleCategorySubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);

    const payload: CategoryInput = {
      name: categoryForm.name.trim(),
      description: categoryForm.description.trim() || null,
    };

    try {
      if (editingCategory) {
        await api.patch(`/categories/${editingCategory.id}`, payload);
      } else {
        await api.post("/categories", payload);
      }

      setCategoryModal(false);
      await Promise.all([loadCategories(), loadProducts()]);
    } catch (caught) {
      setFormError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo guardar la categoría.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCategoryDelete(category: Category) {
    const confirmed = window.confirm(
      `¿Desactivar la categoría "${category.name}"? Los productos conservados quedarán sin categoría.`,
    );
    if (!confirmed) return;

    setDeleting(category.id);

    try {
      await api.del(`/categories/${category.id}`);
      await Promise.all([loadCategories(), loadProducts()]);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "No se pudo desactivar la categoría.",
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
          <h1>Productos</h1>
          <p>Catálogo, categorías, precios y estado del inventario.</p>
        </div>
        <div className="heading-actions">
          <button className="button-secondary" onClick={loadProducts}>
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            <span>Actualizar</span>
          </button>
          <button
            className="button-primary"
            onClick={tab === "productos" ? openProductCreate : openCategoryCreate}
          >
            <Plus size={17} />
            {tab === "productos" ? "Nuevo producto" : "Nueva categoría"}
          </button>
        </div>
      </section>

      <div className="tabs">
        <button
          className={`tab ${tab === "productos" ? "tab-active" : ""}`}
          onClick={() => setTab("productos")}
        >
          <Package size={16} /> Productos
        </button>
        <button
          className={`tab ${tab === "categorias" ? "tab-active" : ""}`}
          onClick={() => setTab("categorias")}
        >
          <FolderTree size={16} /> Categorías
        </button>
      </div>

      {tab === "productos" ? (
        <section className="panel data-panel">
          <div className="panel-header data-toolbar">
            <div>
              <h3>Catálogo de productos</h3>
              <p>
                {data
                  ? `${data.total} registro${data.total === 1 ? "" : "s"}`
                  : "Cargando..."}
              </p>
            </div>
            <div className="toolbar-controls">
              <select
                className="form-input"
                value={categoryId}
                onChange={(event) => {
                  setCategoryId(event.target.value);
                  setPage(1);
                }}
                aria-label="Filtrar por categoría"
              >
                <option value="">Todas las categorías</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <label className="search-box">
                <Search size={17} />
                <input
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                  placeholder="Buscar por nombre o SKU..."
                  aria-label="Buscar productos"
                />
              </label>
            </div>
          </div>

          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>PRODUCTO</th>
                  <th>CATEGORÍA</th>
                  <th>PRECIO</th>
                  <th>COSTO</th>
                  <th>ESTADO</th>
                  <th>ACCIONES</th>
                </tr>
              </thead>
              <tbody>
                {loading && !data && (
                  <tr>
                    <td colSpan={6} className="table-state">
                      <Loader2 size={19} className="spin" /> Cargando
                      productos...
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
                      <Package size={19} />
                      {search
                        ? `Sin coincidencias para "${search}".`
                        : "Aún no hay productos registrados."}
                    </td>
                  </tr>
                )}

                {data?.items.map((product) => (
                  <tr key={product.id}>
                    <td>
                      <div className="customer-cell">
                        <div className="customer-avatar avatar-cyan">
                          <Tag size={15} />
                        </div>
                        <div className="customer-copy">
                          <strong>{product.name}</strong>
                          <span>{product.sku}</span>
                        </div>
                      </div>
                    </td>
                    <td>{product.category_name ?? "Sin categoría"}</td>
                    <td className="amount-cell">{money(product.unit_price)}</td>
                    <td className="amount-cell">{money(product.cost_price)}</td>
                    <td>
                      <span
                        className={`status ${
                          product.is_active
                            ? "status-completada"
                            : "status-cancelada"
                        }`}
                      >
                        <i />
                        {product.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="icon-button"
                          aria-label="Editar producto"
                          onClick={() => openProductEdit(product)}
                        >
                          <Pencil size={16} />
                        </button>
                        {product.is_active && (
                          <button
                            className="icon-button"
                            aria-label="Desactivar producto"
                            disabled={deleting === product.id}
                            onClick={() => handleProductDelete(product)}
                          >
                            {deleting === product.id ? (
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
      ) : (
        <section className="panel data-panel">
          <div className="panel-header data-toolbar">
            <div>
              <h3>Categorías del catálogo</h3>
              <p>{categories.length} categorías activas</p>
            </div>
            <label className="search-box">
              <Search size={17} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar categoría..."
                aria-label="Buscar categorías"
              />
            </label>
          </div>

          {categoriesError && (
            <div className="form-alert form-alert-block" role="alert">
              {categoriesError}
            </div>
          )}

          <div className="table-scroll">
            <table className="transactions-table">
              <thead>
                <tr>
                  <th>CATEGORÍA</th>
                  <th>DESCRIPCIÓN</th>
                  <th>REGISTRO</th>
                  <th>ACCIONES</th>
                </tr>
              </thead>
              <tbody>
                {categories.length === 0 && !categoriesError && (
                  <tr>
                    <td colSpan={4} className="table-state">
                      <FolderTree size={19} /> Aún no hay categorías.
                    </td>
                  </tr>
                )}

                {categories
                  .filter((category) =>
                    `${category.name} ${category.description ?? ""}`
                      .toLowerCase()
                      .includes(search.toLowerCase()),
                  )
                  .map((category) => (
                    <tr key={category.id}>
                      <td>
                        <strong>{category.name}</strong>
                      </td>
                      <td>{category.description ?? "—"}</td>
                      <td className="date-cell">
                        {formatDate(category.created_at)}
                      </td>
                      <td>
                        <div className="row-actions">
                          <button
                            className="icon-button"
                            aria-label="Editar categoría"
                            onClick={() => openCategoryEdit(category)}
                          >
                            <Pencil size={16} />
                          </button>
                          <button
                            className="icon-button"
                            aria-label="Desactivar categoría"
                            disabled={deleting === category.id}
                            onClick={() => handleCategoryDelete(category)}
                          >
                            {deleting === category.id ? (
                              <Loader2 size={16} className="spin" />
                            ) : (
                              <Trash2 size={16} />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {productModal && (
        <Modal
          title={editingProduct ? "Editar producto" : "Nuevo producto"}
          onClose={() => setProductModal(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setProductModal(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={handleProductSubmit}
                disabled={submitting}
              >
                {submitting
                  ? "Guardando..."
                  : editingProduct
                    ? "Guardar cambios"
                    : "Crear producto"}
              </button>
            </>
          }
        >
          <form className="form-grid" onSubmit={handleProductSubmit}>
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field">
              <span>SKU *</span>
              <input
                className="form-input"
                value={productForm.sku}
                onChange={(event) =>
                  setProductForm({ ...productForm, sku: event.target.value })
                }
                maxLength={60}
                required
                placeholder="SKU-001"
              />
            </label>

            <label className="form-field">
              <span>Categoría</span>
              <select
                className="form-input"
                value={productForm.category_id}
                onChange={(event) =>
                  setProductForm({
                    ...productForm,
                    category_id: event.target.value,
                  })
                }
              >
                <option value="">Sin categoría</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field form-field-full">
              <span>Nombre *</span>
              <input
                className="form-input"
                value={productForm.name}
                onChange={(event) =>
                  setProductForm({ ...productForm, name: event.target.value })
                }
                maxLength={180}
                required
                placeholder="Ej. Laptop empresarial"
              />
            </label>

            <label className="form-field">
              <span>Precio de venta (S/) *</span>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.01"
                value={productForm.unit_price}
                onChange={(event) =>
                  setProductForm({
                    ...productForm,
                    unit_price: event.target.value,
                  })
                }
                required
                placeholder="0.00"
              />
            </label>

            <label className="form-field">
              <span>Costo (S/)</span>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.01"
                value={productForm.cost_price}
                onChange={(event) =>
                  setProductForm({
                    ...productForm,
                    cost_price: event.target.value,
                  })
                }
                placeholder="0.00"
              />
            </label>

            <label className="form-field form-field-full">
              <span>Descripción</span>
              <textarea
                className="form-input"
                rows={3}
                value={productForm.description}
                onChange={(event) =>
                  setProductForm({
                    ...productForm,
                    description: event.target.value,
                  })
                }
                placeholder="Opcional"
              />
            </label>

            <button type="submit" className="hidden-submit" aria-hidden="true" />
          </form>
        </Modal>
      )}

      {categoryModal && (
        <Modal
          title={editingCategory ? "Editar categoría" : "Nueva categoría"}
          onClose={() => setCategoryModal(false)}
          footer={
            <>
              <button
                className="button-secondary"
                onClick={() => setCategoryModal(false)}
                disabled={submitting}
              >
                Cancelar
              </button>
              <button
                className="button-primary"
                onClick={handleCategorySubmit}
                disabled={submitting}
              >
                {submitting ? "Guardando..." : "Guardar"}
              </button>
            </>
          }
        >
          <form className="form-grid" onSubmit={handleCategorySubmit}>
            {formError && (
              <div className="form-alert" role="alert">
                {formError}
              </div>
            )}

            <label className="form-field form-field-full">
              <span>Nombre *</span>
              <input
                className="form-input"
                value={categoryForm.name}
                onChange={(event) =>
                  setCategoryForm({ ...categoryForm, name: event.target.value })
                }
                maxLength={100}
                required
                placeholder="Ej. Electrónica"
              />
            </label>

            <label className="form-field form-field-full">
              <span>Descripción</span>
              <textarea
                className="form-input"
                rows={3}
                value={categoryForm.description}
                onChange={(event) =>
                  setCategoryForm({
                    ...categoryForm,
                    description: event.target.value,
                  })
                }
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
