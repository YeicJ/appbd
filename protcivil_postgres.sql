-- 1.- Crear la base de datos
CREATE DATABASE protcivil_db;
\c protcivil_db

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
    fecha_hora    TIMESTAMP    NOT NULL,
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
