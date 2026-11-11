-- Rol, permisos y usuario para protcivil_db (ejecutar conectado a protcivil_db como postgres)

-- 1. Crear el rol
CREATE ROLE rol_operador;

-- 2. Dar permisos al rol (puede consultar, insertar y actualizar, pero NO eliminar)
GRANT CONNECT ON DATABASE protcivil_db TO rol_operador;
GRANT USAGE ON SCHEMA public TO rol_operador;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO rol_operador;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rol_operador;

-- 3. Crear el usuario
CREATE USER operador1 WITH PASSWORD 'Operador123';

-- 4. Agregar el usuario al rol
GRANT rol_operador TO operador1;
