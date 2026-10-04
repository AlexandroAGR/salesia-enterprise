import {
  Boxes,
  ChartNoAxesCombined,
  CreditCard,
  FileBarChart,
  LayoutDashboard,
  Lightbulb,
  Package,
  Settings,
  ShoppingCart,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  label: string;
  path: string;
  icon: LucideIcon;
};

export const navigation: { title: string; items: NavItem[] }[] = [
  {
    title: "GENERAL",
    items: [
      { label: "Dashboard", path: "/", icon: LayoutDashboard },
      { label: "Analytics", path: "/analytics", icon: ChartNoAxesCombined },
      { label: "Insights", path: "/insights", icon: Lightbulb },
    ],
  },
  {
    title: "GESTIÓN COMERCIAL",
    items: [
      { label: "Ventas", path: "/ventas", icon: ShoppingCart },
      { label: "Pedidos", path: "/pedidos", icon: FileBarChart },
      { label: "Clientes", path: "/clientes", icon: Users },
      { label: "Productos", path: "/productos", icon: Package },
      { label: "Inventario", path: "/inventario", icon: Boxes },
      { label: "Pagos", path: "/pagos", icon: CreditCard },
    ],
  },
  {
    title: "SISTEMA",
    items: [
      { label: "Reportes", path: "/reportes", icon: FileBarChart },
      { label: "Configuración", path: "/configuracion", icon: Settings },
    ],
  },
];

const pathTitles: Record<string, string> = {
  "/": "Dashboard",
  "/ayuda": "Centro de ayuda",
};

navigation.forEach((group) => {
  group.items.forEach((item) => {
    pathTitles[item.path] = item.label;
  });
});

export function titleForPath(pathname: string): string {
  return pathTitles[pathname] ?? "SalesIA Enterprise";
}
