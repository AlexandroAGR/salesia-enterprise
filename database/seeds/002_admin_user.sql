BEGIN;

-- ============================================
-- USUARIO ADMINISTRADOR INICIAL
-- Credenciales: admin@salesia.local / Admin123*
-- Cambiar en entornos que no sean de desarrollo.
-- ============================================

INSERT INTO users (
    company_id,
    role_id,
    full_name,
    email,
    password_hash,
    is_active
)
SELECT
    c.id,
    r.id,
    'Administrador General',
    'admin@salesia.local',
    '$argon2id$v=19$m=65536,t=3,p=4$6i+rBV0eHhGol2tGeiwDvg$OfHwDVIQmM+n8qJxOgc1DIDwxnA2oh5JNmIR0WDoz4g',
    TRUE
FROM companies c
CROSS JOIN roles r
WHERE c.tax_id = '00000000000'
  AND r.name = 'Administrador'
ON CONFLICT (company_id, email) DO NOTHING;

COMMIT;
