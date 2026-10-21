-- 1.- Crear la base de datos
CREATE DATABASE protcivil_db;
GO
USE protcivil_db;
GO

-- 2.- Tablas maestras
CREATE TABLE areas (
    id_area      INT          NOT NULL PRIMARY KEY,
    nombre_area  VARCHAR(100) NOT NULL,
    descripcion  VARCHAR(255) NULL
);

CREATE TABLE empleados (
    id_empleado      INT         NOT NULL PRIMARY KEY,
    nombre           VARCHAR(50) NOT NULL,
    apellido_paterno VARCHAR(50) NOT NULL,
    apellido_materno VARCHAR(50) NULL,
    cargo            VARCHAR(80) NOT NULL,
    telefono         VARCHAR(20) NULL,
    fecha_ingreso    DATE        NOT NULL
);

CREATE TABLE negocios (
    id_negocio     INT          NOT NULL PRIMARY KEY,
    nombre_negocio VARCHAR(120) NOT NULL,
    giro           VARCHAR(80)  NOT NULL,
    direccion      VARCHAR(150) NOT NULL,
    propietario    VARCHAR(100) NULL,
    telefono       VARCHAR(20)  NULL
);

-- 3.- ENUM se cambia por VARCHAR + CHECK
CREATE TABLE normatividad (
    id_normatividad   INT          NOT NULL PRIMARY KEY,
    titulo            VARCHAR(150) NOT NULL,
    numero_norma      VARCHAR(50)  NULL,
    ambito            VARCHAR(10)  NOT NULL CHECK (ambito IN ('Federal', 'Estatal', 'Municipal')),
    fecha_publicacion DATE         NOT NULL,
    archivo_pdf       VARCHAR(200) NULL,
    descripcion       VARCHAR(255) NULL
);

CREATE TABLE eventos (
    id_evento     INT          NOT NULL PRIMARY KEY,
    nombre_evento VARCHAR(120) NOT NULL,
    tipo_evento   VARCHAR(60)  NOT NULL,
    fecha_evento  DATE         NOT NULL,
    lugar         VARCHAR(150) NOT NULL,
    organizador   VARCHAR(100) NULL
);

-- 4.- Tablas de movimientos
CREATE TABLE empleado_area (
    id_empleado_area INT         NOT NULL PRIMARY KEY,
    id_empleado      INT         NOT NULL,
    id_area          INT         NOT NULL,
    fecha_asignacion DATE        NOT NULL,
    fecha_baja       DATE        NULL,
    rol              VARCHAR(60) NULL,
    CONSTRAINT fk_empleado_area_empleado FOREIGN KEY (id_empleado) REFERENCES empleados (id_empleado),
    CONSTRAINT fk_empleado_area_area     FOREIGN KEY (id_area)     REFERENCES areas (id_area)
);

CREATE TABLE expedientes (
    id_expediente   INT          NOT NULL PRIMARY KEY,
    folio           VARCHAR(30)  NOT NULL UNIQUE,
    tipo_expediente VARCHAR(20)  NOT NULL CHECK (tipo_expediente IN ('Negocio', 'Servicios_Generales')),
    id_negocio      INT          NULL,
    fecha_apertura  DATE         NOT NULL,
    estado          VARCHAR(15)  NOT NULL CHECK (estado IN ('Abierto', 'En revisión', 'Cerrado')),
    descripcion     VARCHAR(255) NULL,
    CONSTRAINT fk_expedientes_negocio FOREIGN KEY (id_negocio) REFERENCES negocios (id_negocio)
);

CREATE TABLE servicios (
    id_servicio   INT          NOT NULL PRIMARY KEY,
    id_expediente INT          NOT NULL,
    id_evento     INT          NULL,
    id_empleado   INT          NOT NULL,
    tipo_servicio VARCHAR(20)  NOT NULL CHECK (tipo_servicio IN ('Emergencia', 'Traslado', 'Cobertura_Evento')),
    fecha_hora    DATETIME     NOT NULL,
    ubicacion     VARCHAR(150) NOT NULL,
    descripcion   VARCHAR(255) NULL,
    CONSTRAINT fk_servicios_expediente FOREIGN KEY (id_expediente) REFERENCES expedientes (id_expediente),
    CONSTRAINT fk_servicios_evento     FOREIGN KEY (id_evento)     REFERENCES eventos (id_evento),
    CONSTRAINT fk_servicios_empleado   FOREIGN KEY (id_empleado)   REFERENCES empleados (id_empleado)
);

CREATE TABLE documentos (
    id_documento   INT          NOT NULL PRIMARY KEY,
    id_expediente  INT          NOT NULL,
    id_servicio    INT          NULL,
    id_empleado    INT          NULL,
    tipo_documento VARCHAR(60)  NOT NULL,
    nombre_archivo VARCHAR(150) NOT NULL,
    fecha_carga    DATE         NOT NULL,
    ruta_archivo   VARCHAR(200) NULL,
    CONSTRAINT fk_documentos_expediente FOREIGN KEY (id_expediente) REFERENCES expedientes (id_expediente),
    CONSTRAINT fk_documentos_servicio   FOREIGN KEY (id_servicio)   REFERENCES servicios (id_servicio),
    CONSTRAINT fk_documentos_empleado   FOREIGN KEY (id_empleado)   REFERENCES empleados (id_empleado)
);

-- 5.- Usuarios del login (admin / admin123)
CREATE TABLE usuarios (
    id_usuario INT          NOT NULL PRIMARY KEY,
    usuario    VARCHAR(50)  NOT NULL UNIQUE,
    contrasena VARCHAR(200) NOT NULL,
    nombre     VARCHAR(100) NOT NULL
);

-- 6.- Datos de ejemplo
INSERT INTO usuarios VALUES (1, 'admin', 'pbkdf2_sha256$200000$ed3bfad7b951aeb6e2a9111c109497c3$8ce79daadd1fe941241d0bce327b7fc5a4ef328c0dc5f284c5c0b121d99c4fc6', 'Administrador');

INSERT INTO areas VALUES
(1, 'Inspección y Riesgos', 'Dictámenes y visitas a negocios'),
(2, 'Atención a Emergencias', 'Emergencias, traslados y coberturas'),
(3, 'Capacitación', 'Cursos y constancias de capacitación');

INSERT INTO empleados VALUES
(1, 'Luis', 'Torres', 'Méndez', 'Director', '3535551001', '2022-01-10'),
(2, 'Ana', 'García', NULL, 'Paramédico', '3535551002', '2023-03-15'),
(3, 'Jorge', 'Ruiz', 'Pérez', 'Inspector', NULL, '2024-06-01');

INSERT INTO negocios VALUES
(1, 'Farmacia San José', 'Farmacia', 'Av. Hidalgo 12', 'José Ramos', '3535552001'),
(2, 'Restaurante El Lago', 'Restaurante', 'Calle Morelos 45', NULL, NULL);

INSERT INTO normatividad VALUES
(1, 'Ley General de Protección Civil', NULL, 'Federal', '2012-06-06', 'ley_general_pc.pdf', 'Marco nacional de protección civil'),
(2, 'Prevención y protección contra incendios', 'NOM-002-STPS-2010', 'Federal', '2010-12-09', 'nom_002_stps.pdf', NULL),
(3, 'Reglamento Municipal de Protección Civil', 'RM-PC-01', 'Municipal', '2021-03-01', NULL, NULL);

INSERT INTO eventos VALUES
(1, 'Feria del Pueblo 2026', 'Feria', '2026-02-02', 'Plaza principal', 'Ayuntamiento'),
(2, 'Desfile 16 de Septiembre', 'Desfile', '2026-09-16', 'Calle principal', NULL);

INSERT INTO empleado_area VALUES
(1, 1, 1, '2022-01-10', NULL, 'Coordinador'),
(2, 2, 2, '2023-03-15', NULL, NULL),
(3, 3, 1, '2024-06-01', NULL, 'Inspector');

INSERT INTO expedientes VALUES
(1, 'NEG-0001', 'Negocio', 1, '2026-01-20', 'Abierto', 'Dictamen de Farmacia San José'),
(2, 'SERV-2026', 'Servicios_Generales', NULL, '2026-01-01', 'Abierto', 'Servicios del año 2026');

INSERT INTO servicios VALUES
(1, 2, 1, 2, 'Cobertura_Evento', '2026-02-02 18:00:00', 'Plaza principal', 'Cobertura sin incidentes'),
(2, 2, NULL, 2, 'Traslado', '2026-03-10 09:30:00', 'Col. Centro', 'Traslado al hospital regional');

INSERT INTO documentos VALUES
(1, 1, NULL, 3, 'Dictamen', 'dictamen_neg0001.pdf', '2026-01-25', NULL),
(2, 2, 2, 2, 'FRAP', 'frap_servicio2.pdf', '2026-03-10', NULL);

-- 7.- Más datos de ejemplo para las gráficas del dashboard
INSERT INTO empleados VALUES
(4, 'María', 'Hernández', 'Soto', 'Paramédico', '3535551004', '2024-09-01'),
(5, 'Carlos', 'Mendoza', NULL, 'Bombero', '3535551005', '2025-02-10'),
(6, 'Sofía', 'Navarro', 'Ríos', 'Instructora', NULL, '2025-08-18');

INSERT INTO empleado_area VALUES
(4, 4, 2, '2024-09-01', NULL, NULL),
(5, 5, 2, '2025-02-10', NULL, 'Bombero'),
(6, 6, 3, '2025-08-18', NULL, 'Instructora');

INSERT INTO negocios VALUES
(3, 'Abarrotes Doña Mary', 'Abarrotes', 'Calle Juárez 8', 'María López', '3535552003'),
(4, 'Gasolinera El Puente', 'Gasolinera', 'Carretera Jiquilpan km 2', 'Grupo Energéticos', '3535552004'),
(5, 'Escuela Primaria Benito Juárez', 'Educación', 'Av. Revolución 100', NULL, '3535552005'),
(6, 'Salón de Eventos Las Palmas', 'Salón de eventos', 'Calle Allende 33', 'Raúl Chávez', NULL),
(7, 'Ferretería La Llave', 'Ferretería', 'Calle Zaragoza 21', 'Pedro Núñez', '3535552007'),
(8, 'Hotel Plaza', 'Hotel', 'Portal Hidalgo 2', 'Laura Vega', '3535552008');

INSERT INTO eventos VALUES
(3, 'Carrera Atlética 10K', 'Deportivo', '2026-05-17', 'Unidad deportiva', 'Club de corredores'),
(4, 'Fiestas Patronales', 'Religioso', '2026-07-25', 'Parroquia de Santiago', 'Parroquia'),
(5, 'Simulacro Nacional 2026', 'Simulacro', '2026-09-19', 'Escuelas y oficinas', 'Coordinación Nacional de PC');

INSERT INTO expedientes VALUES
(3, 'NEG-0002', 'Negocio', 2, '2026-02-05', 'En revisión', 'Inspección de Restaurante El Lago'),
(4, 'NEG-0003', 'Negocio', 3, '2026-02-18', 'Cerrado', 'Dictamen de Abarrotes Doña Mary'),
(5, 'NEG-0004', 'Negocio', 4, '2026-03-02', 'Cerrado', 'Dictamen de Gasolinera El Puente'),
(6, 'NEG-0005', 'Negocio', 5, '2026-03-20', 'Cerrado', 'Programa interno de la escuela'),
(7, 'NEG-0006', 'Negocio', 6, '2026-04-08', 'En revisión', 'Aforo y salidas de emergencia del salón'),
(8, 'NEG-0007', 'Negocio', 7, '2026-04-22', 'Cerrado', 'Dictamen de Ferretería La Llave'),
(9, 'NEG-0008', 'Negocio', 8, '2026-05-12', 'Abierto', 'Dictamen de Hotel Plaza'),
(10, 'NEG-0009', 'Negocio', 1, '2026-06-03', 'Cerrado', 'Renovación de dictamen de Farmacia San José'),
(11, 'NEG-0010', 'Negocio', 4, '2026-06-25', 'En revisión', 'Revisión de tanques de almacenamiento'),
(12, 'NEG-0011', 'Negocio', 6, '2026-07-14', 'Abierto', 'Seguimiento de observaciones del salón'),
(13, 'NEG-0012', 'Negocio', 5, '2026-08-05', 'Cerrado', 'Simulacro de evacuación escolar'),
(14, 'NEG-0013', 'Negocio', 2, '2026-08-27', 'En revisión', 'Revisión de instalación de gas'),
(15, 'NEG-0014', 'Negocio', 3, '2026-09-15', 'Abierto', 'Renovación de dictamen de abarrotes'),
(16, 'NEG-0015', 'Negocio', 8, '2026-10-02', 'En revisión', 'Revisión de señalización del hotel'),
(17, 'NEG-0016', 'Negocio', 7, '2026-10-09', 'Abierto', 'Verificación de extintores'),
(18, 'NEG-0017', 'Negocio', 1, '2026-01-28', 'Cerrado', 'Visita de verificación a farmacia');

INSERT INTO servicios VALUES
(3, 2, NULL, 5, 'Emergencia', '2026-01-06 22:40:00', 'Col. Centro', 'Fuga de gas en vivienda'),
(4, 2, NULL, 2, 'Traslado', '2026-01-14 07:20:00', 'Comunidad La Palma', 'Traslado de paciente a hospital regional'),
(5, 2, NULL, 4, 'Emergencia', '2026-01-27 15:05:00', 'Carretera Jiquilpan', 'Choque entre dos vehículos'),
(6, 2, NULL, 4, 'Emergencia', '2026-02-02 21:30:00', 'Plaza principal', 'Persona lesionada durante la feria'),
(7, 2, NULL, 2, 'Traslado', '2026-02-11 10:10:00', 'Col. La Esperanza', 'Traslado de adulto mayor'),
(8, 2, NULL, 5, 'Emergencia', '2026-02-19 13:45:00', 'Calle Morelos', 'Cortocircuito en local comercial'),
(9, 2, NULL, 5, 'Emergencia', '2026-03-04 18:25:00', 'Av. Hidalgo', 'Incendio de pastizal'),
(10, 2, NULL, 4, 'Emergencia', '2026-03-15 09:50:00', 'Col. Centro', 'Persona con crisis hipertensiva'),
(11, 2, NULL, 2, 'Traslado', '2026-03-22 16:30:00', 'Comunidad San Pedro', 'Traslado de mujer embarazada'),
(12, 2, NULL, 5, 'Emergencia', '2026-03-29 12:15:00', 'Carretera municipal', 'Volcadura de camioneta'),
(13, 2, NULL, 5, 'Emergencia', '2026-04-03 14:00:00', 'Cerro de San Francisco', 'Incendio forestal'),
(14, 2, NULL, 5, 'Emergencia', '2026-04-09 11:20:00', 'Col. Lázaro Cárdenas', 'Enjambre de abejas en casa habitación'),
(15, 2, NULL, 2, 'Traslado', '2026-04-18 08:40:00', 'Col. Centro', 'Traslado programado a hemodiálisis'),
(16, 2, NULL, 1, 'Emergencia', '2026-04-26 17:35:00', 'Calle Zaragoza', 'Caída de árbol sobre vía pública'),
(17, 2, 3, 4, 'Cobertura_Evento', '2026-05-17 07:00:00', 'Unidad deportiva', 'Cobertura de carrera atlética'),
(18, 2, NULL, 4, 'Emergencia', '2026-05-17 08:10:00', 'Unidad deportiva', 'Corredor con deshidratación'),
(19, 2, NULL, 5, 'Emergencia', '2026-05-05 19:45:00', 'Col. La Esperanza', 'Fuga de gas LP'),
(20, 2, NULL, 2, 'Traslado', '2026-05-21 06:30:00', 'Comunidad La Palma', 'Traslado de paciente pediátrico'),
(21, 2, NULL, 4, 'Emergencia', '2026-05-30 23:10:00', 'Av. Revolución', 'Atropellamiento de motociclista'),
(22, 2, NULL, 5, 'Emergencia', '2026-06-08 16:20:00', 'Col. Centro', 'Inundación de calles por lluvia'),
(23, 2, NULL, 5, 'Emergencia', '2026-06-19 20:05:00', 'Arroyo El Salto', 'Rescate de persona arrastrada por la corriente'),
(24, 2, NULL, 2, 'Traslado', '2026-06-27 09:15:00', 'Col. San Miguel', 'Traslado de adulto mayor'),
(25, 2, 4, 1, 'Cobertura_Evento', '2026-07-25 18:00:00', 'Parroquia de Santiago', 'Cobertura de fiestas patronales'),
(26, 2, 4, 4, 'Cobertura_Evento', '2026-07-26 12:00:00', 'Parroquia de Santiago', 'Cobertura de procesión'),
(27, 2, NULL, 4, 'Emergencia', '2026-07-25 22:30:00', 'Calle principal', 'Quemadura por pirotecnia'),
(28, 2, NULL, 5, 'Emergencia', '2026-07-10 15:40:00', 'Col. Lázaro Cárdenas', 'Árbol caído por tormenta'),
(29, 2, NULL, 2, 'Traslado', '2026-07-16 11:00:00', 'Comunidad San Pedro', 'Traslado de paciente a clínica'),
(30, 2, NULL, 4, 'Emergencia', '2026-08-03 13:25:00', 'Carretera Jiquilpan', 'Choque por alcance'),
(31, 2, NULL, 2, 'Traslado', '2026-08-12 07:45:00', 'Col. Centro', 'Traslado programado a hemodiálisis'),
(32, 2, NULL, 5, 'Emergencia', '2026-08-20 17:50:00', 'Col. La Esperanza', 'Inundación de vivienda'),
(33, 2, NULL, 2, 'Traslado', '2026-08-29 10:30:00', 'Comunidad La Palma', 'Traslado de mujer embarazada'),
(34, 2, 2, 1, 'Cobertura_Evento', '2026-09-16 08:00:00', 'Calle principal', 'Cobertura del desfile cívico'),
(35, 2, NULL, 4, 'Emergencia', '2026-09-16 10:20:00', 'Calle principal', 'Desmayo de estudiante en el desfile'),
(36, 2, 5, 6, 'Cobertura_Evento', '2026-09-19 12:00:00', 'Escuelas y oficinas', 'Apoyo en simulacro nacional'),
(37, 2, NULL, 5, 'Emergencia', '2026-09-07 19:30:00', 'Calle Juárez', 'Incendio en cocina de vivienda'),
(38, 2, NULL, 2, 'Traslado', '2026-09-24 09:40:00', 'Col. San Miguel', 'Traslado de paciente a hospital regional'),
(39, 2, NULL, 4, 'Emergencia', '2026-09-28 21:15:00', 'Av. Hidalgo', 'Riña con persona lesionada'),
(40, 2, NULL, 5, 'Emergencia', '2026-10-04 14:35:00', 'Col. Centro', 'Fuga de gas en restaurante'),
(41, 2, NULL, 2, 'Traslado', '2026-10-11 08:20:00', 'Comunidad San Pedro', 'Traslado de adulto mayor'),
(42, 2, NULL, 4, 'Emergencia', '2026-10-17 18:05:00', 'Carretera municipal', 'Choque de motocicleta');

INSERT INTO documentos VALUES
(3, 4, NULL, 3, 'Dictamen', 'dictamen_neg0003.pdf', '2026-02-25', NULL),
(4, 5, NULL, 3, 'Dictamen', 'dictamen_neg0004.pdf', '2026-03-10', NULL),
(5, 2, 5, 4, 'FRAP', 'frap_servicio5.pdf', '2026-01-27', NULL),
(6, 2, 13, 5, 'Informe', 'informe_servicio13.pdf', '2026-04-04', NULL),
(7, 6, NULL, 3, 'Dictamen', 'dictamen_neg0005.pdf', '2026-03-28', NULL),
(8, 2, 34, 1, 'Informe', 'informe_desfile.pdf', '2026-09-17', NULL),
(9, 8, NULL, 3, 'Dictamen', 'dictamen_neg0007.pdf', '2026-04-30', NULL),
(10, 2, 36, 6, 'Constancia', 'constancia_simulacro.pdf', '2026-09-20', NULL);
