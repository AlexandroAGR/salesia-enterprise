/**
 * Control de acceso por rol en el navegador – Fase 13.
 *
 * Reflejo de la matriz del backend (app/core/permissions.py): decide
 * qué módulos se muestran en la navegación y qué botones de creación
 * se habilitan. El backend vuelve a validar todo en cada petición;
 * esta capa sólo evita mostrar acciones que terminarían en 403.
 */

export type ModuleKey =
  | "dashboard"
  | "analytics"
  | "insights"
  | "ventas"
  | "pedidos"
  | "clientes"
  | "productos"
  | "inventario"
  | "pagos"
  | "reportes"
  | "configuracion"
  | "ayuda";

const ALL_MODULES: ModuleKey[] = [
  "dashboard",
  "analytics",
  "insights",
  "ventas",
  "pedidos",
  "clientes",
  "productos",
  "inventario",
  "pagos",
  "reportes",
  "configuracion",
  "ayuda",
];

const MODULE_ACCESS: Record<string, ModuleKey[]> = {
  Administrador: ALL_MODULES,
  Gerente: [
    "dashboard",
    "analytics",
    "insights",
    "ventas",
    "pedidos",
    "clientes",
    "productos",
    "pagos",
    "reportes",
    "ayuda",
  ],
  Vendedor: [
    "dashboard",
    "ventas",
    "pedidos",
    "clientes",
    "productos",
    "pagos",
    "ayuda",
  ],
  Analista: ["dashboard", "analytics", "insights", "reportes", "ayuda"],
  Almacén: ["dashboard", "productos", "inventario", "ayuda"],
};

const ACTION_ACCESS: Record<string, string[]> = {
  "customers:create": ["Administrador", "Vendedor"],
  "products:create": ["Administrador", "Almacén"],
  "categories:create": ["Administrador", "Almacén"],
  "sales:create": ["Administrador", "Vendedor"],
  "inventory:create": ["Administrador", "Almacén"],
  "payments:create": ["Administrador", "Vendedor"],
};

/** ¿Puede el rol abrir este módulo? Rol desconocido → sin acceso. */
export function canAccess(
  role: string | null | undefined,
  module: ModuleKey,
): boolean {
  if (!role) {
    return false;
  }

  const modules = MODULE_ACCESS[role];
  return modules !== undefined && modules.includes(module);
}

/** ¿Puede el rol ejecutar esta acción de escritura? */
export function can(
  role: string | null | undefined,
  action: keyof typeof ACTION_ACCESS,
): boolean {
  if (!role) {
    return false;
  }

  const roles = ACTION_ACCESS[action];
  return roles !== undefined && roles.includes(role);
}

/** Módulo dueño de una ruta de navegación ("/ventas" → "ventas"). */
export function moduleForPath(path: string): ModuleKey | null {
  if (path === "/") {
    return "dashboard";
  }

  const key = path.replace(/^\//, "");
  return (ALL_MODULES as string[]).includes(key)
    ? (key as ModuleKey)
    : null;
}
