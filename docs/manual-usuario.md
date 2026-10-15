# Manual de usuario — SalesIA Enterprise

> Guía práctica de uso del sistema. Versión 1.0 · Fase 16.
> Dirigida a los usuarios del sistema: administradores, gerentes, vendedores,
> analistas y personal de almacén.

## 1. Introducción

SalesIA Enterprise es su sistema de gestión comercial y análisis estadístico.
Desde aquí puede registrar clientes y productos, **documentar ventas y pagos**,
controlar el inventario y, sobre todo, **convertir esa operación diaria en
información**: KPIs, gráficos de evolución, insights automáticos y reportes
exportables.

**Dirección de la aplicación:** <https://salesia-enterprise-nine.vercel.app>

No requiere instalación: se usa desde el navegador (Chrome, Firefox, Edge o
Safari actualizados) en computadora o tablet.

## 2. Acceso al sistema

1. Abra la dirección anterior. Aparecerá la pantalla de inicio de sesión.
2. Introduzca su **correo electrónico** y su **contraseña**.
3. Pulse **Iniciar sesión**.

Si los datos son correctos, accede al **Dashboard**. En caso contrario verá un
mensaje de credenciales inválidas.

> **Su cuenta la crea el administrador del sistema** con el rol que le
> corresponde. Cada usuario ve sólo los módulos autorizados.

### Cierre de sesión

Pulse su nombre en la esquina superior derecha y elija **Salir**. La sesión se
cierra y queda registrada en la auditoría. El acceso caduca automáticamente a
las **60 minutos** por seguridad: si deja el sistema inactivo, deberá volver a
iniciar sesión.

## 3. La pantalla principal

Al entrar ve el **Dashboard ejecutivo** con:

- **KPIs**: ingresos, número de ventas, ticket promedio y más.
- **Gráficos**: evolución temporal y composición por categoría o producto.
- **Filtros superiores**: periodo, vendedor y categoría. Los filtros afectan a
  todos los indicadores de la página.

El menú lateral agrupa los módulos en tres bloques: **General** (Dashboard,
Analytics, Insights), **Gestión comercial** (Ventas, Pedidos, Clientes,
Productos, Inventario, Pagos) y **Reportes**. Los módulos que su rol no tiene
permitido **no aparecen** en el menú.

## 4. Módulos

### 4.1 Clientes

Alta, edición y consulta de clientes con búsqueda por nombre o documento.

- **Nuevo cliente**: botón *Nuevo cliente*. Documento (DNI u otro), nombre,
  correo, teléfono y dirección.
- **Buscar**: escriba en el cuadro de búsqueda; los resultados se actualizan solos.
- **Editar / desactivar**: en la fila de cada cliente. Desactivar conserva el
  histórico sin permitir nuevas ventas a ese cliente.

### 4.2 Productos y categorías

Catálogo con **SKU**, nombre, categoría, precio de venta y costo.

- **Nuevo producto**: requiere SKU único, nombre y precio. La categoría es
  opcional pero recomendada, porque alimenta los análisis de concentración.
- **Buscar** por nombre o SKU; **filtrar** por categoría.
- Las categorías se administran desde el propio módulo.

### 4.3 Inventario

Muestra el **stock actual** de cada producto con su cantidad mínima.

- Las **entradas** y **salidas** se registran como movimientos, con motivo.
- Un producto por debajo de su cantidad mínima se marca como **stock bajo**.
- **Las ventas actualizan el inventario automáticamente**: no necesita anotarlo
  a mano.

### 4.4 Ventas

El módulo central.

1. Pulse **Nueva venta**.
2. Elija el **cliente** (opcional, pero recomendado).
3. Añada **productos** con su cantidad.
4. El sistema calcula automáticamente subtotal, impuesto (18 %) y **total**.
5. Confirme. La venta queda registrada, se genera su número y el inventario
   se descuenta.

En la tabla *Ventas registradas* puede **filtrar por estado**: completadas,
pendientes, canceladas o reembolsadas. El detalle de cada venta muestra sus
líneas, sus pagos y su estado.

### 4.5 Pagos

Registre el pago de una venta: importe, **método de pago** (efectivo, Yape,
transferencia…) y referencia. Varias ventas pueden pagarse en partes; el
sistema controla el saldo pendiente de cada una.

### 4.6 Pedidos

Consulta y gestión de los pedidos con sus estados, para seguir el proceso
comercial desde el pedido hasta la venta completada.

## 5. Análisis estadístico

### 5.1 Analytics

Panel con la **evolución temporal** de ingresos y ventas, desglose por
categoría, producto o vendedor, y frecuencias. Use los filtros de periodo,
vendedor y categoría para comparar. Los datos numéricos exactos de cada gráfico
se muestran también en tabla, junto a la media y la mediana.

### 5.2 Insights

El sistema analiza sus datos y **detecta automáticamente** situaciones
relevantes. Cada insight incluye:

- **Título y descripción** en lenguaje natural.
- **La evidencia**: el dato numérico concreto que lo origina (por ejemplo,
  «una categoría concentra el 62 % de los ingresos»).
- **Severidad**: informativo o de aviso.

Puede regenerar los insights para el periodo que desee. Entre las situaciones
que detecta: tendencia de ingresos, concentración por categoría o producto,
vendedor destacado, sesgo del ticket promedio, alta dispersión de importes,
ventas pendientes y tasa de cancelación.

### 5.3 Análisis estadísticos (datasets)

Permite definir **datasets** con sus variables (numéricas o de texto), cargar
observaciones y ejecutar cálculos que quedan **almacenados** para consultarlos
después:

- **Media y mediana** de una variable.
- **Variables aleatorias**: distribución, parámetros y valor esperado.
- **Probabilidad** de eventos.
- **Teorema de Bayes**: calcula la probabilidad posterior a partir de las
  probabilaciones introducidas y explica el resultado.

## 6. Reportes

Pulse **Generar reporte**, elija el **tipo** y el **periodo**:

| Tipo | Contenido |
|---|---|
| **Ventas** | Detalle de ventas del periodo con totales, impuestos y estados |
| **Estadístico** | KPIs, estadística descriptiva, comparación con el periodo anterior e interpretación |
| **Productos** | Ranking de productos por ingresos y unidades |
| **Clientes** | Comportamiento de compra por cliente |
| **Vendedores** | Rendimiento comparado del equipo de ventas |

El listado inferior guarda el **histórico de reportes generados**, con su tipo,
título y fecha, para volver a consultarlos. Cada reporte puede **exportarse**.

## 7. Qué puede hacer cada rol

Su rol define los módulos y las acciones disponibles. El sistema oculta lo que
no le corresponde y, además, **vuelve a validarlo en el servidor**.

| Módulo | Administrador | Gerente | Vendedor | Analista | Almacén |
|---|:--:|:--:|:--:|:--:|:--:|
| Dashboard, Analytics | ✔ | ✔ | ✔ | ✔ | ✔ |
| Clientes — ver | ✔ | ✔ | ✔ | — | — |
| Clientes — crear/editar | ✔ | — | ✔ | — | — |
| Productos — ver | ✔ | ✔ | ✔ | — | ✔ |
| Productos — crear/editar | ✔ | — | — | — | ✔ |
| Inventario — ver | ✔ | ✔ | ✔ | — | ✔ |
| Inventario — movimientos | ✔ | — | — | — | ✔ |
| Ventas — ver | ✔ | ✔ | ✔ | ✔ | ✔ |
| Ventas — registrar | ✔ | — | ✔ | — | — |
| Pagos — ver | ✔ | ✔ | ✔ | — | — |
| Insights, Reportes, Análisis | ✔ | ✔ | — | ✔ | — |
| Auditoría | ✔ | — | — | — | — |

## 8. Preguntas frecuentes

**No ve un módulo en el menú.** Su rol no lo tiene habilitado. Contacte al
administrador si necesita acceso.

**«Credenciales inválidas».** Verifique correo y contraseña. Si olvidó su
contraseña, el administrador puede restablecerla.

**La sesión se cerró sola.** Por seguridad caduca a los 60 minutos. Vuelva a
iniciar sesión.

**Una venta no se puede registrar.** Revise que el producto tenga stock
disponible y que el formulario no tenga campos pendientes.

**Los datos de Analytics no coinciden con lo esperado.** Compruebe los filtros
de periodo, vendedor y categoría activos en la parte superior.

**Aparece un error 403.** Significa que su rol no está autorizado para esa
acción, aunque el botón fuera visible.

## 9. Atención y soporte

Ante cualquier incidencia, indique: su **usuario y rol**, el **módulo**, la
**hora** aproximada y el **mensaje** mostrado. Esa información permite
rastrear el suceso en los registros de auditoría.
