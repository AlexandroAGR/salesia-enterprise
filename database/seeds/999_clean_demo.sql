-- ============================================================
-- LIMPIEZA: elimina la empresa demo (9001) y todos sus datos.
-- Ejecutar sobre salesia_enterprise.
-- Backup previo: C:\Users\alexandro\Desktop\AlexandroVSC\Semana7\backup_antes_borrar_demo.sql
-- Orden inverso a las claves foráneas.
-- ============================================================

BEGIN;

-- 1. Tablas hijas de datasets / análisis (sin company_id)
DELETE FROM audit_logs            WHERE company_id = 9001;
DELETE FROM reports               WHERE company_id = 9001;
DELETE FROM insights              WHERE company_id = 9001;
DELETE FROM bayes_analyses        WHERE analysis_id IN (9971, 9972);
DELETE FROM statistical_results   WHERE analysis_id IN (9971, 9972);
DELETE FROM random_variables      WHERE dataset_id IN (9941, 9942);
DELETE FROM observations          WHERE dataset_id IN (9941, 9942);
DELETE FROM dataset_variables     WHERE dataset_id IN (9941, 9942);
DELETE FROM statistical_analyses  WHERE company_id = 9001;
DELETE FROM datasets              WHERE company_id = 9001;

-- 2. Operación comercial
DELETE FROM inventory_movements   WHERE company_id = 9001;
DELETE FROM inventory             WHERE company_id = 9001;
DELETE FROM payments              WHERE sale_id BETWEEN 9701 AND 9708;
DELETE FROM sale_details          WHERE sale_id BETWEEN 9701 AND 9708;
DELETE FROM sales                 WHERE company_id = 9001;

-- 3. Catálogos
DELETE FROM payment_methods       WHERE company_id = 9001;
DELETE FROM products              WHERE company_id = 9001;
DELETE FROM categories            WHERE company_id = 9001;
DELETE FROM customers             WHERE company_id = 9001;

-- 4. Personal y usuarios
DELETE FROM employees             WHERE company_id = 9001;
DELETE FROM users                 WHERE company_id = 9001;

-- 5. Roles demo (globales, sin company_id) solo si nadie más los usa
DELETE FROM roles r
WHERE r.id IN (9101, 9102, 9103, 9104)
  AND NOT EXISTS (SELECT 1 FROM users u WHERE u.role_id = r.id);

-- 6. La empresa
DELETE FROM companies             WHERE id = 9001;

COMMIT;

-- ------------------------------------------------------------
-- Verificación: todo debe devolver 0
-- ------------------------------------------------------------
SELECT 'companies'   AS tabla, COUNT(*) AS restantes FROM companies   WHERE id >= 9001
UNION ALL SELECT 'users',          COUNT(*) FROM users          WHERE id >= 9201
UNION ALL SELECT 'customers',      COUNT(*) FROM customers      WHERE company_id = 9001
UNION ALL SELECT 'products',       COUNT(*) FROM products       WHERE company_id = 9001
UNION ALL SELECT 'sales',          COUNT(*) FROM sales          WHERE company_id = 9001
UNION ALL SELECT 'sale_details',   COUNT(*) FROM sale_details   WHERE id >= 9801
UNION ALL SELECT 'payments',       COUNT(*) FROM payments       WHERE id >= 9911
UNION ALL SELECT 'inventory',      COUNT(*) FROM inventory      WHERE company_id = 9001
UNION ALL SELECT 'movements',      COUNT(*) FROM inventory_movements WHERE company_id = 9001
UNION ALL SELECT 'datasets',       COUNT(*) FROM datasets       WHERE company_id = 9001
UNION ALL SELECT 'roles_demo',     COUNT(*) FROM roles          WHERE id >= 9101
ORDER BY 1;
