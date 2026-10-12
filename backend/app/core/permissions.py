"""Matriz de permisos por rol – Fase 13 (Roles y permisos).

Cada permiso agrupa los endpoints de un módulo. El rol
Administrador concentra todos los permisos; los demás roles
reciben sólo las acciones propias de sus responsabilidades
(Plan, sección 6 "Actores y roles"):

  · Administrador  Configura el sistema, usuarios, roles y parámetros.
  · Gerente        Consulta indicadores, Analytics, reportes y
                   resultados comerciales.
  · Vendedor       Registra clientes, pedidos y ventas autorizadas.
  · Analista       Ejecuta análisis estadísticos y genera
                   insights/reportes.
  · Almacén        Gestiona stock y movimientos de inventario.

Un permiso desconocido se deniega siempre (falla por seguridad).
"""

PERMISSIONS: dict[str, frozenset[str]] = {
    # --- módulos comerciales ---
    "customers:view": frozenset(
        {"Administrador", "Gerente", "Vendedor"}
    ),
    "customers:write": frozenset({"Administrador", "Vendedor"}),
    "products:view": frozenset(
        {"Administrador", "Gerente", "Vendedor", "Almacén"}
    ),
    "products:write": frozenset({"Administrador", "Almacén"}),
    "inventory:view": frozenset(
        {"Administrador", "Gerente", "Vendedor", "Almacén"}
    ),
    "inventory:write": frozenset({"Administrador", "Almacén"}),
    "payments:view": frozenset(
        {"Administrador", "Gerente", "Vendedor"}
    ),
    "payments:write": frozenset({"Administrador", "Vendedor"}),
    "sales:write": frozenset({"Administrador", "Vendedor"}),
    # Lectura de ventas y analytics: todos los roles (el dashboard
    # ejecutivo es el punto de entrada de todos los módulos).
    # --- analítica e inteligencia ---
    "insights:view": frozenset(
        {"Administrador", "Gerente", "Analista"}
    ),
    "insights:generate": frozenset(
        {"Administrador", "Gerente", "Analista"}
    ),
    "reports:view": frozenset({"Administrador", "Gerente", "Analista"}),
    "reports:generate": frozenset(
        {"Administrador", "Gerente", "Analista"}
    ),
    "datasets:view": frozenset(
        {"Administrador", "Gerente", "Analista"}
    ),
    "datasets:write": frozenset(
        {"Administrador", "Gerente", "Analista"}
    ),
    "analyses:view": frozenset(
        {"Administrador", "Gerente", "Analista"}
    ),
    "analyses:run": frozenset({"Administrador", "Gerente", "Analista"}),
    # --- administración del sistema ---
    "audit:view": frozenset({"Administrador"}),
    "users:manage": frozenset({"Administrador"}),
    "settings:manage": frozenset({"Administrador"}),
}


def role_has_permission(role_name: str | None, permission: str) -> bool:
    """Indica si un rol posee un permiso de la matriz."""
    allowed = PERMISSIONS.get(permission)
    if not allowed:
        return False
    if not role_name:
        return False
    return role_name in allowed
