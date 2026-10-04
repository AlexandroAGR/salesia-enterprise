BEGIN;

-- ============================================
-- ROLES DEL SISTEMA
-- ============================================

INSERT INTO roles (name, description)
VALUES
    ('Administrador', 'Acceso completo al sistema'),
    ('Gerente', 'Gestión empresarial, ventas y reportes'),
    ('Vendedor', 'Gestión de clientes y ventas'),
    ('Analista', 'Acceso a análisis estadístico y dashboards'),
    ('Almacén', 'Gestión de productos e inventario')
ON CONFLICT (name) DO NOTHING;


-- ============================================
-- EMPRESA INICIAL
-- ============================================

INSERT INTO companies (
    name,
    tax_id,
    email,
    phone,
    address
)
VALUES (
    'SalesIA Enterprise',
    '00000000000',
    'admin@salesia.com',
    '+51 000 000 000',
    'Lima, Perú'
)
ON CONFLICT (tax_id) DO NOTHING;


-- ============================================
-- CATEGORÍAS INICIALES
-- ============================================

INSERT INTO categories (
    company_id,
    name,
    description
)
SELECT
    c.id,
    v.name,
    v.description
FROM companies c
CROSS JOIN (
    VALUES
        ('Electrónica', 'Productos electrónicos y dispositivos'),
        ('Oficina', 'Productos y suministros de oficina'),
        ('Accesorios', 'Accesorios y complementos'),
        ('Servicios', 'Servicios comercializados por la empresa')
) AS v(name, description)
WHERE c.tax_id = '00000000000'
ON CONFLICT (company_id, name) DO NOTHING;


-- ============================================
-- MÉTODOS DE PAGO
-- ============================================

INSERT INTO payment_methods (
    company_id,
    name,
    code
)
SELECT
    c.id,
    v.name,
    v.code
FROM companies c
CROSS JOIN (
    VALUES
        ('Efectivo', 'CASH'),
        ('Tarjeta', 'CARD'),
        ('Transferencia bancaria', 'BANK_TRANSFER'),
        ('Yape / Plin', 'DIGITAL_WALLET')
) AS v(name, code)
WHERE c.tax_id = '00000000000'
ON CONFLICT (company_id, name) DO NOTHING;


COMMIT;