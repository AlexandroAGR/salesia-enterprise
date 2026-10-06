-- ============================================================
-- Reajusta las secuencias de IDENTITY al MAX(id) real,
-- después de eliminar el seed demo (que las había subido a ~10000).
-- ============================================================

DO $$
DECLARE
    t TEXT;
    seq TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'companies','roles','users','employees','customers','categories',
        'products','sales','sale_details','payment_methods','payments',
        'inventory','inventory_movements','datasets','dataset_variables',
        'observations','statistical_analyses','statistical_results',
        'bayes_analyses','random_variables','insights','reports','audit_logs'
    ]
    LOOP
        seq := pg_get_serial_sequence('public.' || t, 'id');
        IF seq IS NOT NULL THEN
            EXECUTE format(
                'SELECT setval(%L, GREATEST(COALESCE((SELECT MAX(id) FROM public.%I), 1), 1), true)',
                seq, t
            );
            RAISE NOTICE '% -> %', t, seq;
        END IF;
    END LOOP;
END $$;

-- Verificación
SELECT 'sales' AS tabla, last_value FROM sales_id_seq
UNION ALL SELECT 'products', last_value FROM products_id_seq
UNION ALL SELECT 'customers', last_value FROM customers_id_seq;
