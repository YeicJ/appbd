-- 2 roles, permisos y usuarios para protcivil_db (ejecutar conectado a protcivil_db como postgres)

-- ===== ROL 1: operador (consulta, inserta y actualiza; NO elimina) =====
-- 1. Crear el rol
CREATE ROLE rol_operador;

-- 2. Dar permisos al rol
GRANT CONNECT ON DATABASE protcivil_db TO rol_operador;
GRANT USAGE ON SCHEMA public TO rol_operador;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO rol_operador;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rol_operador;

-- 3. Crear el usuario
CREATE USER operador1 WITH PASSWORD 'Operador123';

-- 4. Agregar el usuario al rol
GRANT rol_operador TO operador1;

-- ===== ROL 2: consulta (solo consulta) =====
-- 1. Crear el rol
CREATE ROLE rol_consulta;

-- 2. Dar permisos al rol
GRANT CONNECT ON DATABASE protcivil_db TO rol_consulta;
GRANT USAGE ON SCHEMA public TO rol_consulta;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rol_consulta;

-- 3. Crear el usuario
CREATE USER consulta1 WITH PASSWORD 'Consulta123';

-- 4. Agregar el usuario al rol
GRANT rol_consulta TO consulta1;

-- 5. Pruebas en pgAdmin (conectarse con cada usuario y ejecutar):
--   operador1: SELECT * FROM areas;  -> funciona
--              DELETE FROM areas;    -> permiso denegado
--   consulta1: SELECT * FROM areas;  -> funciona
--              UPDATE / INSERT / DELETE en areas -> permiso denegado
