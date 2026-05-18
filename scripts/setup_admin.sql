-- Centinel Engine — Configuración de roles en upnfm_members
-- Ejecutar en Supabase SQL Editor después de que el usuario ya esté en la tabla.
-- Sustituir <USER_UUID> con el UUID del usuario (Auth > Users > copiar id).

-- 1. Ver miembros actuales y sus roles
SELECT u.email, m.name, m.org, m.access_level, m.added_at
FROM upnfm_members m
JOIN auth.users u ON u.id = m.user_id
ORDER BY m.added_at;

-- 2. Asignar rol admin al operador principal
UPDATE upnfm_members
SET access_level = 'admin', org = 'upnfm'
WHERE user_id = '<USER_UUID>';

-- 3. Insertar un nuevo miembro si no existe aún
-- INSERT INTO upnfm_members (user_id, name, org, access_level)
-- VALUES ('<USER_UUID>', 'Nombre Operador', 'upnfm', 'admin');

-- Valores válidos:
--   org:          upnfm | unah | admin | external
--   access_level: admin | researcher | readonly
