"""Sistema de Archivo · Protección Civil V. Carranza (PyQt6)."""
import hashlib
import hmac
import json
import math
import os
import re
import sys
from collections import Counter

from dotenv import load_dotenv
from PyQt6.QtCore import QDate, QPointF, QRectF, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from conexion import ConexionPostgres, ConexionSqlServer

# =====================================================================
# 1. SEGURIDAD (contraseñas)
# =====================================================================
ITERACIONES = 200_000


def generar_hash(clave):
    # [A1] Sal aleatoria de 16 bytes + PBKDF2-SHA256; se guarda "algoritmo$iteraciones$sal$hash".
    sal = os.urandom(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${resumen.hex()}"


def verificar_contrasena(clave, guardado):
    # [A2] Se recalcula el hash con la misma sal e iteraciones y se compara en tiempo constante.
    try:
        _, iteraciones, sal, resumen = guardado.split("$")
    except ValueError:
        return False
    calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), int(iteraciones))
    return hmac.compare_digest(calculado.hex(), resumen)


# =====================================================================
# 2. ACCESO A DATOS
# =====================================================================
def crear_conexion(motor, usuario=None, clave=None):
    # [A3] Lee las credenciales del archivo .env y crea la clase de conexión del motor elegido.
    # En PostgreSQL se puede pasar usuario y clave para entrar con un usuario de la base (operador1, consulta1).
    load_dotenv()
    if motor == "SQL Server":
        return ConexionSqlServer({
            "servidor": os.getenv("SQLSERVER_SERVIDOR", "localhost"),
            "base": os.getenv("SQLSERVER_BASE", "protcivil_db"),
            "usuario": os.getenv("SQLSERVER_USUARIO", ""),
            "contrasena": os.getenv("SQLSERVER_CONTRASENA", ""),
            "confiable": os.getenv("SQLSERVER_WINDOWS_AUTH", "no").lower() in ("si", "sí", "yes", "1"),
        })
    return ConexionPostgres({
        "servidor": os.getenv("PG_SERVIDOR", "localhost"),
        "puerto": int(os.getenv("PG_PUERTO", "5432")),
        "base": os.getenv("PG_BASE", "protcivil_db"),
        "usuario": usuario or os.getenv("PG_USUARIO", "postgres"),
        "contrasena": clave if usuario else os.getenv("PG_CONTRASENA", ""),
    })


class BaseDatos:
    def __init__(self, motor, usuario=None, clave=None):
        # [A4] Se abre la conexión una vez y se guarda el marcador del driver ("?" o "%s").
        self.motor = motor
        self.conexion = crear_conexion(motor, usuario, clave)
        self.conexion.Conectar()
        self.marcador = self.conexion.MARCADOR

    def ejecutar(self, sql, parametros=()):
        # [A5] Ejecutar_consulta devuelve texto JSON; aquí se convierte a diccionario de Python.
        return json.loads(self.conexion.Ejecutar_consulta(sql, tuple(parametros)))

    def cerrar(self):
        self.conexion.Cerrar()


def autenticar(bd, usuario, clave):
    # [A6] Búsqueda parametrizada del usuario; después se valida el hash de su contraseña.
    m = bd.marcador
    r = bd.ejecutar(f"SELECT id_usuario, usuario, contrasena, nombre FROM usuarios WHERE usuario = {m}", (usuario,))
    if not r["estado"]:
        raise RuntimeError(r["mensaje"])
    if r["registros"] and verificar_contrasena(clave, r["registros"][0]["contrasena"]):
        return r["registros"][0]
    return None


def es_error_llave_foranea(mensaje):
    # [A7] SQL Server dice "REFERENCE constraint"; PostgreSQL "foreign key" o "llave foránea".
    texto = mensaje.lower()
    return any(p in texto for p in ("reference constraint", "foreign key", "llave foránea", "clave foránea"))


# =====================================================================
# 3. CONFIGURACIÓN DE LOS CATÁLOGOS (tablas maestras)
# =====================================================================
# [A8] Cada campo: (columna, etiqueta, tipo, opciones). tipo = texto | fecha | lista.
CATALOGOS = [
    dict(titulo="Áreas", tabla="areas", pk="id_area", busqueda="nombre_area",
         campos=[("nombre_area", "Nombre del área", "texto", {"max": 100, "req": True}),
                 ("descripcion", "Descripción", "texto", {"max": 255})]),
    dict(titulo="Empleados", tabla="empleados", pk="id_empleado", busqueda="nombre",
         campos=[("nombre", "Nombre(s)", "texto", {"max": 50, "req": True}),
                 ("apellido_paterno", "Apellido paterno", "texto", {"max": 50, "req": True}),
                 ("apellido_materno", "Apellido materno", "texto", {"max": 50}),
                 ("cargo", "Cargo", "texto", {"max": 80, "req": True}),
                 ("telefono", "Teléfono", "texto", {"max": 20}),
                 ("fecha_ingreso", "Fecha de ingreso", "fecha", {"req": True})]),
    dict(titulo="Negocios", tabla="negocios", pk="id_negocio", busqueda="nombre_negocio",
         campos=[("nombre_negocio", "Nombre comercial", "texto", {"max": 120, "req": True}),
                 ("giro", "Giro", "texto", {"max": 80, "req": True}),
                 ("direccion", "Dirección", "texto", {"max": 150, "req": True}),
                 ("propietario", "Propietario", "texto", {"max": 100}),
                 ("telefono", "Teléfono", "texto", {"max": 20})]),
    dict(titulo="Eventos", tabla="eventos", pk="id_evento", busqueda="nombre_evento",
         campos=[("nombre_evento", "Nombre del evento", "texto", {"max": 120, "req": True}),
                 ("tipo_evento", "Tipo de evento", "texto", {"max": 60, "req": True}),
                 ("fecha_evento", "Fecha", "fecha", {"req": True}),
                 ("lugar", "Lugar", "texto", {"max": 150, "req": True}),
                 ("organizador", "Organizador", "texto", {"max": 100})]),
    dict(titulo="Normatividad", tabla="normatividad", pk="id_normatividad", busqueda="titulo",
         campos=[("titulo", "Título", "texto", {"max": 150, "req": True}),
                 ("numero_norma", "Número / clave", "texto", {"max": 50}),
                 ("ambito", "Ámbito", "lista", {"opciones": ["Federal", "Estatal", "Municipal"], "req": True}),
                 ("fecha_publicacion", "Fecha de publicación", "fecha", {"req": True}),
                 ("archivo_pdf", "Archivo PDF", "texto", {"max": 200}),
                 ("descripcion", "Descripción", "texto", {"max": 255})]),
]


# =====================================================================
# 4. CRUD DE LOS CATÁLOGOS (Consultar, Insertar, Actualizar, Eliminar)
# =====================================================================
# Cada función recibe "bd" (BaseDatos) y "cat" (un elemento de CATALOGOS) y devuelve
# la respuesta de la base: {"estado", "mensaje", "registros", "filas_afectadas"}.
def columnas(cat):
    # Orden de columnas para SELECT e INSERT: primero la llave primaria y luego los campos.
    return [cat["pk"]] + [c[0] for c in cat["campos"]]


def crud_consultar(bd, cat, texto=""):
    # [A10] CONSULTAR: SELECT de todas las columnas; filtro opcional por ID o por texto.
    m = bd.marcador
    sql = f"SELECT {', '.join(columnas(cat))} FROM {cat['tabla']}"
    parametros = ()
    if texto.isdigit():
        sql += f" WHERE {cat['pk']} = {m}"
        parametros = (int(texto),)
    elif texto:
        # [A11] UPPER en ambos lados hace la búsqueda sin distinguir mayúsculas; % = "contiene".
        sql += f" WHERE UPPER({cat['busqueda']}) LIKE UPPER({m})"
        parametros = (f"%{texto}%",)
    sql += f" ORDER BY {cat['pk']}"
    return bd.ejecutar(sql, parametros)


def crud_siguiente_id(bd, cat):
    # [A12] Las llaves no son autoincrementables: el nuevo ID es el máximo actual + 1.
    r = bd.ejecutar(f"SELECT MAX({cat['pk']}) AS maximo FROM {cat['tabla']}")
    maximo = r["registros"][0]["maximo"] if r["estado"] else None
    return (int(maximo) if maximo is not None else 0) + 1


def crud_buscar_por_id(bd, cat, id_buscado):
    # [A13] Trae un solo registro por su llave primaria (para Actualizar/Eliminar desde el menú).
    r = bd.ejecutar(f"SELECT {', '.join(columnas(cat))} FROM {cat['tabla']} "
                    f"WHERE {cat['pk']} = {bd.marcador}", (id_buscado,))
    return r["registros"][0] if r["estado"] and r["registros"] else None


def crud_insertar(bd, cat, valores):
    # [A14] INSERTAR: un marcador por columna; los valores viajan aparte en una tupla.
    # Devuelve la respuesta de la base y el ID que se le asignó al registro.
    nuevo_id = crud_siguiente_id(bd, cat)
    marcadores = ", ".join([bd.marcador] * len(columnas(cat)))
    sql = f"INSERT INTO {cat['tabla']} ({', '.join(columnas(cat))}) VALUES ({marcadores})"
    return bd.ejecutar(sql, [nuevo_id] + valores), nuevo_id


def crud_actualizar(bd, cat, id_registro, valores):
    # [A15] ACTUALIZAR: "col = marcador" por cada campo; el ID va al final para el WHERE.
    m = bd.marcador
    asignaciones = ", ".join(f"{c[0]} = {m}" for c in cat["campos"])
    sql = f"UPDATE {cat['tabla']} SET {asignaciones} WHERE {cat['pk']} = {m}"
    return bd.ejecutar(sql, valores + [id_registro])


def crud_eliminar(bd, cat, id_registro):
    # [A16] ELIMINAR: DELETE por llave primaria; si otra tabla lo usa, la BD lo rechaza (FK).
    return bd.ejecutar(f"DELETE FROM {cat['tabla']} WHERE {cat['pk']} = {bd.marcador}",
                       (id_registro,))


# =====================================================================
# 5. CONSULTAS DEL DASHBOARD (datos para las tarjetas y las gráficas)
# =====================================================================
def contar_registros(bd, cat):
    # [A9] Conteo de registros por catálogo para las tarjetas del inicio.
    return bd.ejecutar(f"SELECT COUNT(*) AS total FROM {cat['tabla']}")


def expedientes_por_estado(bd):
    # Expedientes agrupados por estado (gráfica de dona).
    return bd.ejecutar("SELECT estado, COUNT(*) AS total FROM expedientes GROUP BY estado")


def servicios_con_fecha(bd):
    # Tipo y fecha de cada servicio. El conteo por tipo y por mes se hace en Python
    # (PaginaInicio) para que la misma consulta sirva en SQL Server y PostgreSQL.
    return bd.ejecutar("SELECT tipo_servicio, fecha_hora FROM servicios")


# =====================================================================
# 5b. SEGURIDAD EN POSTGRESQL (Roles, Grupos, Usuarios y Permisos)
# =====================================================================
# Roles    = roles SIN inicio de sesión (rol_operador, rol_consulta de roles_permisos.sql).
# Usuarios = roles CON inicio de sesión (operador1, consulta1); son los que entran a pgAdmin.
# Grupos   = qué usuarios pertenecen a cada rol (GRANT rol TO usuario); heredan sus permisos.
# Permisos = GRANT / REVOKE de SELECT, INSERT, UPDATE y DELETE sobre cada tabla.
PRIVILEGIOS = ("SELECT", "INSERT", "UPDATE", "DELETE")
NOMBRE_VALIDO = re.compile(r"[a-z_][a-z0-9_]{0,62}")


def _rechazo(mensaje):
    return {"estado": False, "mensaje": mensaje, "registros": [], "filas_afectadas": 0}


def _validar(*nombres):
    # [S1] Los nombres de rol y de tabla NO pueden ir como parámetro (%s), así que antes de
    # meterlos al SQL se valida que solo tengan minúsculas, números y "_" (evita inyección SQL).
    for nombre in nombres:
        if not NOMBRE_VALIDO.fullmatch(nombre or ""):
            return _rechazo(f"Nombre no válido: «{nombre}». Usa solo minúsculas, números y _ "
                            "(ejemplo: rol_consulta).")
    return None


def seg_roles(bd):
    # [S2] pg_roles guarda roles y usuarios; los roles son los que NO pueden iniciar sesión.
    return bd.ejecutar("""
        SELECT r.rolname AS rol, COALESCE(string_agg(u.rolname, ', ' ORDER BY u.rolname), '') AS miembros
        FROM pg_roles r
        LEFT JOIN pg_auth_members m ON m.roleid = r.oid
        LEFT JOIN pg_roles u ON u.oid = m.member
        WHERE NOT r.rolcanlogin AND r.rolname !~ '^pg_'
        GROUP BY r.rolname ORDER BY r.rolname""")


def seg_usuarios(bd):
    # [S3] Usuarios = roles con LOGIN; se omite el superusuario (postgres).
    return bd.ejecutar("""
        SELECT u.rolname AS usuario, COALESCE(string_agg(r.rolname, ', ' ORDER BY r.rolname), '') AS roles
        FROM pg_roles u
        LEFT JOIN pg_auth_members m ON m.member = u.oid
        LEFT JOIN pg_roles r ON r.oid = m.roleid
        WHERE u.rolcanlogin AND NOT u.rolsuper
        GROUP BY u.rolname ORDER BY u.rolname""")


def seg_grupos(bd):
    # [S4] pg_auth_members guarda la pertenencia: qué usuario está dentro de qué rol.
    return bd.ejecutar("""
        SELECT r.rolname AS rol, u.rolname AS usuario
        FROM pg_auth_members m
        JOIN pg_roles r ON r.oid = m.roleid
        JOIN pg_roles u ON u.oid = m.member
        WHERE r.rolname !~ '^pg_'
        ORDER BY r.rolname, u.rolname""")


def seg_crear_rol(bd, rol):
    # [S5] CREATE ROLE + permiso para conectarse a la base y usar el esquema public.
    error = _validar(rol)
    if error:
        return error
    base = bd.conexion.datos["base"]
    return bd.ejecutar(f'CREATE ROLE {rol}; GRANT CONNECT ON DATABASE "{base}" TO {rol}; '
                       f"GRANT USAGE ON SCHEMA public TO {rol}")


def seg_crear_usuario(bd, usuario, clave):
    # [S6] CREATE USER = rol con LOGIN. La contraseña sí va como parámetro.
    error = _validar(usuario)
    if error:
        return error
    if len(clave) < 6:
        return _rechazo("La contraseña debe tener al menos 6 caracteres.")
    return bd.ejecutar(f"CREATE USER {usuario} WITH PASSWORD %s", (clave,))


def seg_cambiar_clave(bd, usuario, clave):
    error = _validar(usuario)
    if error:
        return error
    if len(clave) < 6:
        return _rechazo("La contraseña debe tener al menos 6 caracteres.")
    return bd.ejecutar(f"ALTER USER {usuario} WITH PASSWORD %s", (clave,))


def seg_eliminar(bd, nombre):
    # [S7] Sirve para roles y usuarios. DROP OWNED BY quita sus permisos (sin eso PostgreSQL
    # no deja borrarlo). Nunca se borra un superusuario: DROP OWNED BY postgres borraría las tablas.
    error = _validar(nombre)
    if error:
        return error
    r = bd.ejecutar("SELECT rolsuper FROM pg_roles WHERE rolname = %s", (nombre,))
    if not r["estado"] or not r["registros"] or r["registros"][0]["rolsuper"]:
        return _rechazo(f"No se puede eliminar «{nombre}».")
    return bd.ejecutar(f"DROP OWNED BY {nombre}; DROP ROLE {nombre}")


def seg_agregar_a_grupo(bd, rol, usuario):
    # [S8] GRANT rol TO usuario: el usuario entra al grupo y hereda los permisos del rol.
    return _validar(rol, usuario) or bd.ejecutar(f"GRANT {rol} TO {usuario}")


def seg_quitar_de_grupo(bd, rol, usuario):
    return _validar(rol, usuario) or bd.ejecutar(f"REVOKE {rol} FROM {usuario}")


def seg_tablas(bd):
    return bd.ejecutar("SELECT table_name AS tabla FROM information_schema.tables "
                       "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name")


def seg_permisos(bd, rol):
    # [S9] relacl es la lista de permisos de cada tabla; aclexplode la separa en una fila por permiso.
    return bd.ejecutar("""
        SELECT c.relname AS tabla, a.privilege_type AS privilegio
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        CROSS JOIN LATERAL aclexplode(c.relacl) a
        WHERE n.nspname = 'public' AND c.relkind = 'r' AND a.grantee = %s::regrole""", (rol,))


def seg_guardar_permisos(bd, rol, permisos):
    # [S10] permisos = {tabla: [privilegios marcados]}. Por cada tabla se quita todo (REVOKE ALL)
    # y se otorga lo marcado (GRANT); todo va en una sola transacción.
    error = _validar(rol, *permisos)
    if error:
        return error
    sentencias = []
    for tabla, privilegios in permisos.items():
        if any(p not in PRIVILEGIOS for p in privilegios):
            return _rechazo("Privilegio no válido.")
        sentencias.append(f"REVOKE ALL ON {tabla} FROM {rol}")
        if privilegios:
            sentencias.append(f"GRANT {', '.join(privilegios)} ON {tabla} TO {rol}")
    if not sentencias:
        return _rechazo("No hay tablas para asignar permisos.")
    return bd.ejecutar("; ".join(sentencias))


# #####################################################################
# #####################################################################
# ##                                                                 ##
# ##   FIN DE LA PARTE DE BASES DE DATOS                             ##
# ##                                                                 ##
# ##   De aquí hacia abajo solo está la INTERFAZ GRÁFICA (PyQt6):    ##
# ##   estilos, login, gráficas del dashboard, pantalla de           ##
# ##   catálogos y ventana principal. Fue generada con IA y no       ##
# ##   forma parte de lo que se evalúa. Aquí no se escribe SQL:      ##
# ##   solo se llaman las funciones de las secciones 1 a 5.          ##
# ##                                                                 ##
# #####################################################################
# #####################################################################

# =====================================================================
# 6. ESTILOS Y AVISOS
# =====================================================================
AZUL, NARANJA, FONDO = "#16324F", "#E8710A", "#F3F1EC"
VERDE, BORDE, PISTA = "#4C956C", "#DDD8CC", "#EFECE6"
GRIS_TEXTO, GRIS_SUAVE = "#4E4A43", "#8A8478"

ESTILO = f"""
QWidget {{ font-family: 'Segoe UI'; font-size: 10.5pt; color: #1E1E1E; }}
QMainWindow, QDialog, #pagina {{ background: {FONDO}; }}
QMenuBar {{ background: {AZUL}; color: white; padding: 4px; }}
QMenuBar::item {{ padding: 6px 14px; background: transparent; color: white; }}
QMenuBar::item:selected {{ background: {NARANJA}; }}
QMenu {{ background: white; border: 1px solid #C9C4B8; }}
QMenu::item {{ padding: 6px 26px; }}
QMenu::item:selected {{ background: {NARANJA}; color: white; }}
#encabezado {{ background: white; border-bottom: 4px solid {NARANJA}; }}
#tituloPagina {{ font-size: 18pt; font-weight: 600; color: {AZUL}; }}
#subtitulo {{ color: #6B6558; }}
#tarjeta {{ background: white; border: 1px solid #DDD8CC; border-left: 6px solid {AZUL}; }}
#tarjeta:hover {{ border-left: 6px solid {NARANJA}; }}
#numero {{ font-size: 26pt; font-weight: 700; color: {AZUL}; }}
#panel {{ background: white; border: 1px solid #DDD8CC; }}
#etiquetaId {{ background: {AZUL}; color: white; padding: 4px 10px; font-weight: 600; }}
QLineEdit, QComboBox, QDateEdit {{ background: #FBFAF7; border: 1px solid #C9C4B8; padding: 5px; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border: 1px solid {NARANJA}; }}
QPushButton {{ background: white; border: 1px solid {AZUL}; color: {AZUL}; padding: 7px 14px; font-weight: 600; }}
QPushButton:hover {{ background: #E9EEF4; }}
QPushButton#primario {{ background: {NARANJA}; border: 1px solid {NARANJA}; color: white; }}
QPushButton#primario:hover {{ background: #C95F05; }}
QPushButton#peligro {{ border: 1px solid #B3261E; color: #B3261E; }}
QTableWidget {{ background: white; border: 1px solid #DDD8CC; gridline-color: #ECE8DF;
               selection-background-color: #FCE3CC; selection-color: #1E1E1E; }}
QHeaderView::section {{ background: {AZUL}; color: white; padding: 6px; border: none; font-weight: 600; }}
QStatusBar {{ background: white; color: #6B6558; }}
QScrollArea {{ background: {FONDO}; border: none; }}
"""


def aviso(padre, texto, error=False):
    (QMessageBox.warning if error else QMessageBox.information)(padre, "Protección Civil", texto)


# =====================================================================
# 7. VENTANA DE LOGIN
# =====================================================================
class VentanaLogin(QDialog):
    def __init__(self):
        super().__init__()
        self.bd = None
        self.usuario = None
        self.setWindowTitle("Acceso · Protección Civil V. Carranza")
        self.setFixedSize(760, 420)

        franja = QFrame()
        franja.setStyleSheet(f"background: {AZUL};")
        izq = QVBoxLayout(franja)
        izq.setContentsMargins(36, 40, 36, 40)
        escudo = QLabel("▲")
        escudo.setStyleSheet(f"color: {NARANJA}; font-size: 54pt;")
        nombre = QLabel("Protección Civil\nVenustiano Carranza")
        nombre.setStyleSheet("color: white; font-size: 17pt; font-weight: 600;")
        lema = QLabel("Sistema de archivo y\ncatálogos internos")
        lema.setStyleSheet("color: #B8C7D9;")
        for w in (escudo, nombre, lema):
            izq.addWidget(w)
        izq.addStretch()

        derecha = QWidget()
        der = QVBoxLayout(derecha)
        der.setContentsMargins(40, 40, 40, 40)
        titulo = QLabel("Iniciar sesión")
        titulo.setObjectName("tituloPagina")
        self.motor = QComboBox()
        self.motor.addItems(["SQL Server", "PostgreSQL"])
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("Usuario")
        self.txt_clave = QLineEdit()
        self.txt_clave.setPlaceholderText("Contraseña")
        self.txt_clave.setEchoMode(QLineEdit.EchoMode.Password)
        boton = QPushButton("Entrar")
        boton.setObjectName("primario")
        boton.clicked.connect(self.entrar)
        self.txt_clave.returnPressed.connect(self.entrar)
        der.addWidget(titulo)
        der.addSpacing(14)
        for etiqueta, w in (("Motor de base de datos", self.motor), ("Usuario", self.txt_usuario),
                            ("Contraseña", self.txt_clave)):
            der.addWidget(QLabel(etiqueta))
            der.addWidget(w)
        der.addSpacing(10)
        der.addWidget(boton)
        der.addStretch()

        caja = QHBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        caja.addWidget(franja, 2)
        caja.addWidget(derecha, 3)

    def entrar(self):
        motor = self.motor.currentText()
        usuario, clave = self.txt_usuario.text().strip(), self.txt_clave.text()
        if motor == "PostgreSQL" and usuario and clave:
            # [A17] Primero se intenta entrar como usuario de PostgreSQL (operador1, consulta1, postgres):
            # la app trabaja con los permisos de su rol. Si no es usuario de la base, se sigue con la tabla usuarios.
            try:
                bd = BaseDatos(motor, usuario, clave)
            except Exception:
                bd = None
            if bd is not None:
                self.bd, self.usuario = bd, {"nombre": f"{usuario} (PostgreSQL)"}
                self.accept()
                return
        try:
            bd = BaseDatos(motor)
        except Exception as e:
            aviso(self, f"No se pudo conectar a {self.motor.currentText()}:\n{e}", True)
            return
        try:
            usuario = autenticar(bd, self.txt_usuario.text().strip(), self.txt_clave.text())
        except RuntimeError as e:
            bd.cerrar()
            aviso(self, f"Error al consultar usuarios (¿ejecutaste el script SQL?):\n{e}", True)
            return
        if usuario is None:
            bd.cerrar()
            aviso(self, "Usuario o contraseña incorrectos.", True)
            return
        self.bd, self.usuario = bd, usuario
        self.accept()


# =====================================================================
# 8. DASHBOARD Y GRÁFICAS (dona, barras y columnas dibujadas con QPainter)
# =====================================================================
class Grafica(QWidget):
    # Tarjeta blanca con título y subtítulo; cada gráfica dibuja su contenido en dibujar().
    def __init__(self, titulo):
        super().__init__()
        self.titulo = titulo
        self.subtitulo = ""
        self.datos = []
        self.setMinimumSize(260, 320)

    def actualizar(self, datos, subtitulo=""):
        self.datos = list(datos)
        self.subtitulo = subtitulo
        self.update()

    def hay_datos(self):
        return any(valor for _, valor, _ in self.datos)

    def fuente(self, painter, puntos, negrita=False):
        fuente = QFont(self.font())
        fuente.setPointSizeF(puntos)
        fuente.setBold(negrita)
        painter.setFont(fuente)

    def texto(self, painter, rect, alineacion, texto, color):
        painter.setPen(QColor(color))
        painter.drawText(rect, alineacion | Qt.AlignmentFlag.AlignVCenter,
                         painter.fontMetrics().elidedText(texto, Qt.TextElideMode.ElideRight,
                                                          int(rect.width())))

    def paintEvent(self, evento):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(BORDE), 1))
        painter.setBrush(QColor("white"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)

        izquierda = Qt.AlignmentFlag.AlignLeft
        self.fuente(painter, 11.5, True)
        self.texto(painter, QRectF(20, 14, self.width() - 40, 26), izquierda, self.titulo, AZUL)
        self.fuente(painter, 9)
        self.texto(painter, QRectF(20, 38, self.width() - 40, 18), izquierda, self.subtitulo, GRIS_SUAVE)

        area = QRectF(20, 72, self.width() - 40, self.height() - 92)
        if self.hay_datos():
            self.dibujar(painter, area)
        else:
            self.fuente(painter, 10)
            self.texto(painter, area, Qt.AlignmentFlag.AlignHCenter, "Sin datos disponibles", GRIS_SUAVE)


class GraficaDona(Grafica):
    # datos: [(etiqueta, valor, color)]. La leyenda va a la derecha o debajo según el espacio.
    def dibujar(self, painter, area):
        total = sum(valor for _, valor, _ in self.datos)
        fila = 30
        alto_leyenda = len(self.datos) * fila
        lateral = area.width() >= area.height() * 1.3
        if lateral:
            diametro = min(230, area.height(), area.width() * 0.48)
            anillo = QRectF(area.left(), area.center().y() - diametro / 2, diametro, diametro)
            leyenda = QRectF(anillo.right() + 28, area.center().y() - alto_leyenda / 2,
                             area.right() - anillo.right() - 28, alto_leyenda)
        else:
            diametro = min(230, area.width() * 0.8, area.height() - alto_leyenda - 18)
            alto = diametro + 18 + alto_leyenda
            anillo = QRectF(area.center().x() - diametro / 2, area.center().y() - alto / 2,
                            diametro, diametro)
            leyenda = QRectF(area.left(), anillo.bottom() + 18, area.width(), alto_leyenda)

        # Anillo: pista gris de fondo y un arco por categoría con una pequeña separación.
        grosor = max(14.0, diametro * 0.15)
        aro = anillo.adjusted(grosor / 2, grosor / 2, -grosor / 2, -grosor / 2)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(PISTA), grosor))
        painter.drawEllipse(aro)
        visibles = [(valor, color) for _, valor, color in self.datos if valor > 0]
        hueco = 2.0 if len(visibles) > 1 else 0.0
        inicio = 90.0
        for valor, color in visibles:
            amplitud = valor / total * 360
            painter.setPen(QPen(QColor(color), grosor, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            painter.drawArc(aro, int((inicio - hueco / 2) * 16), -int((amplitud - hueco) * 16))
            inicio -= amplitud

        centro = Qt.AlignmentFlag.AlignHCenter
        self.fuente(painter, max(14.0, diametro / 9), True)
        self.texto(painter, QRectF(anillo.left(), anillo.center().y() - 26, diametro, 34),
                   centro, str(total), AZUL)
        self.fuente(painter, 8.5)
        self.texto(painter, QRectF(anillo.left(), anillo.center().y() + 8, diametro, 18),
                   centro, "en total", GRIS_SUAVE)

        derecha = Qt.AlignmentFlag.AlignRight
        for indice, (etiqueta, valor, color) in enumerate(self.datos):
            renglon = QRectF(leyenda.left(), leyenda.top() + indice * fila, leyenda.width(), fila)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color if valor else PISTA))
            painter.drawRoundedRect(QRectF(renglon.left(), renglon.center().y() - 5, 10, 10), 3, 3)
            self.fuente(painter, 9)
            self.texto(painter, renglon, derecha, f"{valor / total:.0%}", GRIS_SUAVE)
            self.fuente(painter, 9.5, True)
            self.texto(painter, renglon.adjusted(0, 0, -46, 0), derecha, str(valor), AZUL)
            self.fuente(painter, 9.5)
            self.texto(painter, renglon.adjusted(18, 0, -84, 0), Qt.AlignmentFlag.AlignLeft,
                       etiqueta, GRIS_TEXTO)


class GraficaBarras(Grafica):
    # datos: [(etiqueta, valor, color)]. Una barra horizontal por categoría.
    def dibujar(self, painter, area):
        total = sum(valor for _, valor, _ in self.datos)
        maximo = max(valor for _, valor, _ in self.datos)
        fila = min(72.0, area.height() / len(self.datos))
        y = area.top() + (area.height() - fila * len(self.datos)) / 2
        for etiqueta, valor, color in self.datos:
            renglon = QRectF(area.left(), y + fila / 2 - 22, area.width(), 22)
            self.fuente(painter, 9)
            self.texto(painter, renglon, Qt.AlignmentFlag.AlignRight, f"{valor / total:.0%}", GRIS_SUAVE)
            self.fuente(painter, 9.5, True)
            self.texto(painter, renglon.adjusted(0, 0, -44, 0), Qt.AlignmentFlag.AlignRight,
                       str(valor), AZUL)
            self.fuente(painter, 9.5)
            self.texto(painter, renglon.adjusted(0, 0, -80, 0), Qt.AlignmentFlag.AlignLeft,
                       etiqueta, GRIS_TEXTO)

            pista = QRectF(area.left(), y + fila / 2 + 4, area.width(), 12)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(PISTA))
            painter.drawRoundedRect(pista, 6, 6)
            if valor:
                pista.setWidth(max(12.0, pista.width() * valor / maximo))
                painter.setBrush(QColor(color))
                painter.drawRoundedRect(pista, 6, 6)
            y += fila


class GraficaColumnas(Grafica):
    # datos: [(etiqueta, [valor por serie])]; series: [(nombre, color)]. Columnas apiladas.
    def __init__(self, titulo, series):
        super().__init__(titulo)
        self.series = series

    def hay_datos(self):
        return any(sum(valores) for _, valores in self.datos)

    def dibujar(self, painter, area):
        # Leyenda de las series en la parte superior.
        self.fuente(painter, 9)
        x = area.left()
        for nombre, color in self.series:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(x, area.top() + 5, 10, 10), 3, 3)
            ancho = painter.fontMetrics().horizontalAdvance(nombre)
            self.texto(painter, QRectF(x + 16, area.top(), ancho + 4, 20),
                       Qt.AlignmentFlag.AlignLeft, nombre, GRIS_TEXTO)
            x += ancho + 36

        # Escala del eje Y en 4 divisiones con números enteros.
        maximo = max(sum(valores) for _, valores in self.datos)
        paso = max(1, math.ceil(maximo / 4))
        tope = paso * 4
        plano = QRectF(area.left() + 28, area.top() + 40, area.width() - 28, area.height() - 66)
        self.fuente(painter, 8.5)
        for i in range(5):
            y = plano.bottom() - plano.height() * i / 4
            painter.setPen(QPen(QColor(PISTA), 1, Qt.PenStyle.SolidLine if i == 0 else Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(plano.left(), y), QPointF(plano.right(), y))
            self.texto(painter, QRectF(area.left(), y - 9, 20, 18), Qt.AlignmentFlag.AlignRight,
                       str(paso * i), GRIS_SUAVE)

        ancho_columna = plano.width() / len(self.datos)
        ancho_barra = min(36.0, ancho_columna * 0.58)
        for indice, (etiqueta, valores) in enumerate(self.datos):
            centro_x = plano.left() + ancho_columna * (indice + 0.5)
            base = plano.bottom()
            segmentos = [(valor, color) for valor, (_, color) in zip(valores, self.series) if valor]
            painter.setPen(Qt.PenStyle.NoPen)
            for n, (valor, color) in enumerate(segmentos):
                alto = plano.height() * valor / tope
                barra = QRectF(centro_x - ancho_barra / 2, base - alto, ancho_barra, alto)
                painter.setBrush(QColor(color))
                if n == len(segmentos) - 1:
                    # Solo la parte superior de la columna lleva esquinas redondeadas.
                    painter.drawRoundedRect(barra, 4, 4)
                    painter.drawRect(barra.adjusted(0, min(4.0, alto / 2), 0, 0))
                else:
                    painter.drawRect(barra.adjusted(0, 1, 0, 0))
                base -= alto

            centro = Qt.AlignmentFlag.AlignHCenter
            suma = sum(valores)
            if suma:
                self.fuente(painter, 8.5, True)
                self.texto(painter, QRectF(centro_x - 20, base - 20, 40, 18), centro, str(suma), AZUL)
            self.fuente(painter, 8.5)
            self.texto(painter, QRectF(centro_x - ancho_columna / 2, plano.bottom() + 6,
                                       ancho_columna, 18), centro, etiqueta, GRIS_TEXTO)


class PaginaInicio(QWidget):
    ESTADOS = (("Abierto", "Abiertos", AZUL), ("En revisión", "En revisión", NARANJA),
               ("Cerrado", "Cerrados", VERDE))
    TIPOS = (("Emergencia", "Emergencias", NARANJA), ("Traslado", "Traslados", AZUL),
             ("Cobertura_Evento", "Coberturas de evento", VERDE))
    MESES = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")

    def __init__(self, ventana):
        super().__init__()
        self.ventana = ventana
        self.numeros = {}
        contenido = QWidget()
        contenido.setObjectName("pagina")
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QFrame.Shape.NoFrame)
        desplazable.setWidget(contenido)
        exterior = QVBoxLayout(self)
        exterior.setContentsMargins(0, 0, 0, 0)
        exterior.addWidget(desplazable)

        caja = QVBoxLayout(contenido)
        caja.setContentsMargins(30, 20, 30, 24)
        titulo = QLabel("Dashboard")
        titulo.setObjectName("tituloPagina")
        sub = QLabel("Resumen de registros, expedientes y servicios.")
        sub.setObjectName("subtitulo")
        caja.addWidget(titulo)
        caja.addWidget(sub)
        caja.addSpacing(12)
        rejilla = QGridLayout()
        rejilla.setSpacing(16)
        for i, cat in enumerate(CATALOGOS):
            tarjeta = QPushButton()
            tarjeta.setObjectName("tarjeta")
            tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
            tarjeta.setMinimumHeight(96)
            interior = QVBoxLayout(tarjeta)
            n = QLabel("–")
            n.setObjectName("numero")
            interior.addWidget(n)
            interior.addWidget(QLabel(f"{cat['titulo']} registrados"))
            tarjeta.clicked.connect(lambda _, k=i: ventana.abrir(k, "consultar"))
            self.numeros[cat["tabla"]] = n
            rejilla.addWidget(tarjeta, 0, i)
        caja.addLayout(rejilla)
        caja.addSpacing(16)

        graficas = QHBoxLayout()
        graficas.setSpacing(16)
        self.grafica_expedientes = GraficaDona("Expedientes por estado")
        self.grafica_servicios = GraficaBarras("Servicios por tipo")
        self.grafica_meses = GraficaColumnas(
            "Servicios por mes", [(nombre, color) for _, nombre, color in self.TIPOS])
        graficas.addWidget(self.grafica_expedientes, 4)
        graficas.addWidget(self.grafica_servicios, 4)
        graficas.addWidget(self.grafica_meses, 7)
        caja.addLayout(graficas, 1)

    def actualizar(self):
        errores = []
        for cat in CATALOGOS:
            r = contar_registros(self.ventana.bd, cat)
            if r["estado"] and r["registros"]:
                self.numeros[cat["tabla"]].setText(str(r["registros"][0]["total"]))
            else:
                self.numeros[cat["tabla"]].setText("?")
                errores.append(f"{cat['titulo']}: {r['mensaje']}")

        r = expedientes_por_estado(self.ventana.bd)
        if r["estado"]:
            totales = {reg["estado"]: reg["total"] for reg in r["registros"]}
            datos = [(nombre, totales.get(clave, 0), color) for clave, nombre, color in self.ESTADOS]
            self.grafica_expedientes.actualizar(
                datos, f"{sum(valor for _, valor, _ in datos)} expedientes en el archivo")
        else:
            self.grafica_expedientes.actualizar([])
            errores.append(f"Expedientes: {r['mensaje']}")

        # Servicios por tipo y por mes (el mes sale del texto de la fecha, AAAA-MM-...).
        r = servicios_con_fecha(self.ventana.bd)
        if r["estado"] and r["registros"]:
            por_tipo = Counter(reg["tipo_servicio"] for reg in r["registros"])
            por_mes = Counter((str(reg["fecha_hora"])[:7], reg["tipo_servicio"]) for reg in r["registros"])
            anio = max(mes[:4] for mes, _ in por_mes)
            ultimo_mes = max(int(mes[5:7]) for mes, _ in por_mes if mes.startswith(anio))
            self.grafica_servicios.actualizar(
                [(nombre, por_tipo[clave], color) for clave, nombre, color in self.TIPOS],
                f"{len(r['registros'])} servicios atendidos")
            self.grafica_meses.actualizar(
                [(self.MESES[mes - 1], [por_mes[f"{anio}-{mes:02d}", clave] for clave, _, _ in self.TIPOS])
                 for mes in range(1, ultimo_mes + 1)],
                f"Año {anio} · por tipo de servicio")
        else:
            self.grafica_servicios.actualizar([])
            self.grafica_meses.actualizar([])
            if not r["estado"]:
                errores.append(f"Servicios: {r['mensaje']}")

        if errores:
            aviso(self, "No se pudo actualizar completamente el dashboard:\n"
                        + "\n".join(errores), True)


# =====================================================================
# 9. PANTALLA DE CATÁLOGOS (formulario + tabla; llama a las funciones crud_*)
# =====================================================================
class PaginaCatalogo(QWidget):
    def __init__(self, ventana, cat):
        super().__init__()
        self.setObjectName("pagina")
        self.ventana, self.cat, self.bd = ventana, cat, ventana.bd
        self.id_actual = None
        self.registros = []
        self.columnas = columnas(cat)

        caja = QVBoxLayout(self)
        caja.setContentsMargins(30, 24, 30, 24)
        titulo = QLabel(cat["titulo"])
        titulo.setObjectName("tituloPagina")
        caja.addWidget(titulo)
        caja.addSpacing(10)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(18)

        # Panel izquierdo: formulario
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(360)
        pf = QVBoxLayout(panel)
        pf.setContentsMargins(18, 18, 18, 18)
        self.lbl_id = QLabel()
        self.lbl_id.setObjectName("etiquetaId")
        pf.addWidget(self.lbl_id, alignment=Qt.AlignmentFlag.AlignLeft)
        formulario = QFormLayout()
        formulario.setVerticalSpacing(10)
        self.widgets = {}
        for col, etiqueta, tipo, op in cat["campos"]:
            if tipo == "fecha":
                w = QDateEdit(QDate.currentDate())
                w.setCalendarPopup(True)
                w.setDisplayFormat("dd/MM/yyyy")
            elif tipo == "lista":
                w = QComboBox()
                w.addItems(op["opciones"])
            else:
                w = QLineEdit()
                w.setMaxLength(op["max"])
            self.widgets[col] = w
            formulario.addRow(etiqueta + (" *" if op.get("req") else ""), w)
        pf.addLayout(formulario)
        pf.addSpacing(12)
        self.btn_insertar = QPushButton("Insertar nuevo")
        self.btn_insertar.setObjectName("primario")
        self.btn_actualizar = QPushButton("Guardar cambios")
        self.btn_eliminar = QPushButton("Eliminar")
        self.btn_eliminar.setObjectName("peligro")
        btn_limpiar = QPushButton("Limpiar formulario")
        self.btn_insertar.clicked.connect(self.insertar)
        self.btn_actualizar.clicked.connect(self.actualizar)
        self.btn_eliminar.clicked.connect(self.eliminar)
        btn_limpiar.clicked.connect(self.limpiar)
        for b in (self.btn_insertar, self.btn_actualizar, self.btn_eliminar, btn_limpiar):
            pf.addWidget(b)
        pf.addStretch()
        nota = QLabel("* obligatorio · Haz clic en una fila para editarla")
        nota.setObjectName("subtitulo")
        nota.setWordWrap(True)
        pf.addWidget(nota)

        # Panel derecho: búsqueda + tabla
        derecha = QVBoxLayout()
        barra = QHBoxLayout()
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText(f"Consultar por ID o por {cat['busqueda'].replace('_', ' ')}…")
        self.txt_buscar.returnPressed.connect(self.cargar)
        btn_buscar = QPushButton("Consultar")
        btn_buscar.clicked.connect(self.cargar)
        btn_todo = QPushButton("Ver todo")
        btn_todo.clicked.connect(lambda: (self.txt_buscar.clear(), self.cargar()))
        barra.addWidget(self.txt_buscar)
        barra.addWidget(btn_buscar)
        barra.addWidget(btn_todo)
        self.tabla = QTableWidget(0, len(self.columnas))
        self.tabla.setHorizontalHeaderLabels(["ID"] + [c[1] for c in cat["campos"]])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabla.cellClicked.connect(lambda fila, _: self.mostrar(self.registros[fila]))
        derecha.addLayout(barra)
        derecha.addWidget(self.tabla)

        cuerpo.addWidget(panel)
        cuerpo.addLayout(derecha, 1)
        caja.addLayout(cuerpo)
        self.limpiar()

    # ---------- utilidades del formulario ----------
    def limpiar(self):
        self.id_actual = None
        self.lbl_id.setText("Registro nuevo")
        for w in self.widgets.values():
            if isinstance(w, QDateEdit):
                w.setDate(QDate.currentDate())
            elif isinstance(w, QComboBox):
                w.setCurrentIndex(0)
            else:
                w.clear()
        self.tabla.clearSelection()
        self.btn_actualizar.setEnabled(False)
        self.btn_eliminar.setEnabled(False)

    def mostrar(self, registro):
        self.id_actual = registro[self.cat["pk"]]
        self.lbl_id.setText(f"ID {self.id_actual}")
        for col, w in self.widgets.items():
            valor = registro[col]
            if isinstance(w, QDateEdit):
                w.setDate(QDate.fromString(str(valor)[:10], "yyyy-MM-dd"))
            elif isinstance(w, QComboBox):
                w.setCurrentText(str(valor))
            else:
                w.setText("" if valor is None else str(valor))
        self.btn_actualizar.setEnabled(True)
        self.btn_eliminar.setEnabled(True)

    def leer_formulario(self):
        # Devuelve la lista de valores en el orden de "campos"; None si falta un obligatorio.
        valores = []
        for col, etiqueta, tipo, op in self.cat["campos"]:
            w = self.widgets[col]
            if tipo == "fecha":
                valor = w.date().toString("yyyy-MM-dd")
            elif tipo == "lista":
                valor = w.currentText()
            else:
                valor = w.text().strip() or None
            if op.get("req") and valor is None:
                aviso(self, f"El campo «{etiqueta}» es obligatorio.", True)
                w.setFocus()
                return None
            valores.append(valor)
        return valores

    # ---------- CRUD (el SQL está arriba, en la sección 4) ----------
    def cargar(self, seleccionar=None):
        r = crud_consultar(self.bd, self.cat, self.txt_buscar.text().strip())
        if not r["estado"]:
            aviso(self, r["mensaje"], True)
            return
        self.registros = r["registros"]
        self.tabla.setRowCount(len(self.registros))
        for fila, reg in enumerate(self.registros):
            for c, col in enumerate(self.columnas):
                valor = reg[col]
                self.tabla.setItem(fila, c, QTableWidgetItem("" if valor is None else str(valor)))
            if seleccionar is not None and reg[self.cat["pk"]] == seleccionar:
                self.tabla.selectRow(fila)
        self.ventana.statusBar().showMessage(f"{self.cat['titulo']}: {len(self.registros)} registro(s)")

    def insertar(self):
        valores = self.leer_formulario()
        if valores is None:
            return
        r, nuevo_id = crud_insertar(self.bd, self.cat, valores)
        if not r["estado"]:
            aviso(self, f"No se pudo insertar:\n{r['mensaje']}", True)
            return
        aviso(self, f"Registro insertado con ID {nuevo_id}.")
        self.txt_buscar.clear()
        self.cargar(seleccionar=nuevo_id)
        self.mostrar(crud_buscar_por_id(self.bd, self.cat, nuevo_id))

    def actualizar(self):
        if self.id_actual is None:
            return
        valores = self.leer_formulario()
        if valores is None:
            return
        r = crud_actualizar(self.bd, self.cat, self.id_actual, valores)
        if not r["estado"]:
            aviso(self, f"No se pudo actualizar:\n{r['mensaje']}", True)
            return
        aviso(self, f"Registro {self.id_actual} actualizado.")
        self.cargar(seleccionar=self.id_actual)

    def eliminar(self):
        if self.id_actual is None:
            return
        if QMessageBox.question(self, "Eliminar", f"¿Eliminar el registro con ID {self.id_actual}?") \
                != QMessageBox.StandardButton.Yes:
            return
        r = crud_eliminar(self.bd, self.cat, self.id_actual)
        if not r["estado"]:
            if es_error_llave_foranea(r["mensaje"]):
                aviso(self, "No se puede eliminar: otros registros (por ejemplo expedientes, "
                            "servicios o asignaciones) hacen referencia a este.", True)
            else:
                aviso(self, f"No se pudo eliminar:\n{r['mensaje']}", True)
            return
        aviso(self, f"Registro {self.id_actual} eliminado.")
        self.limpiar()
        self.cargar()


# =====================================================================
# 9b. PANTALLAS DE SEGURIDAD (llaman a las funciones seg_* de la sección 5b; solo PostgreSQL)
# =====================================================================
class PaginaSeguridad(QWidget):
    # Base común: título, subtítulo, una fila de controles y una tabla.
    def __init__(self, ventana, titulo, subtitulo, encabezados):
        super().__init__()
        self.setObjectName("pagina")
        self.ventana, self.bd = ventana, ventana.bd
        self.registros = []
        caja = QVBoxLayout(self)
        caja.setContentsMargins(30, 24, 30, 24)
        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("tituloPagina")
        lbl_sub = QLabel(subtitulo)
        lbl_sub.setObjectName("subtitulo")
        lbl_sub.setWordWrap(True)
        caja.addWidget(lbl_titulo)
        caja.addWidget(lbl_sub)
        caja.addSpacing(10)
        self.controles = QHBoxLayout()
        caja.addLayout(self.controles)
        self.tabla = QTableWidget(0, len(encabezados))
        self.tabla.setHorizontalHeaderLabels(encabezados)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        caja.addWidget(self.tabla)

    def boton(self, texto, funcion, estilo=None):
        b = QPushButton(texto)
        if estilo:
            b.setObjectName(estilo)
        b.clicked.connect(funcion)
        self.controles.addWidget(b)

    def llenar(self, r, columnas_reg):
        if not r["estado"]:
            aviso(self, r["mensaje"], True)
            return []
        self.tabla.setRowCount(len(r["registros"]))
        for fila, reg in enumerate(r["registros"]):
            for c, col in enumerate(columnas_reg):
                self.tabla.setItem(fila, c, QTableWidgetItem(str(reg[col] or "")))
        self.ventana.statusBar().showMessage(f"{len(r['registros'])} registro(s)")
        return r["registros"]

    def seleccion(self):
        fila = self.tabla.currentRow()
        if fila < 0 or fila >= len(self.registros):
            aviso(self, "Selecciona una fila de la tabla.", True)
            return None
        return self.registros[fila]

    def confirmar(self, texto):
        return QMessageBox.question(self, "Seguridad", texto) == QMessageBox.StandardButton.Yes

    def resultado(self, r, exito):
        if not r["estado"]:
            aviso(self, f"No se pudo completar:\n{r['mensaje']}", True)
            return False
        aviso(self, exito)
        self.cargar()
        return True


class PaginaRoles(PaginaSeguridad):
    def __init__(self, ventana):
        super().__init__(ventana, "Roles", "Roles de PostgreSQL (no inician sesión). "
                         "Sus permisos se asignan en Seguridad › Permisos.", ["Rol", "Usuarios en el rol"])
        self.txt_rol = QLineEdit()
        self.txt_rol.setPlaceholderText("nombre_del_rol")
        self.controles.addWidget(self.txt_rol)
        self.boton("Crear rol", self.crear, "primario")
        self.boton("Eliminar seleccionado", self.eliminar, "peligro")
        self.controles.addStretch()

    def cargar(self):
        self.registros = self.llenar(seg_roles(self.bd), ["rol", "miembros"])

    def crear(self):
        rol = self.txt_rol.text().strip().lower()
        if self.resultado(seg_crear_rol(self.bd, rol), f"Rol {rol} creado. Asígnale permisos en Seguridad › Permisos."):
            self.txt_rol.clear()

    def eliminar(self):
        reg = self.seleccion()
        if reg and self.confirmar(f"¿Eliminar el rol {reg['rol']}? Se quitarán sus permisos."):
            self.resultado(seg_eliminar(self.bd, reg["rol"]), f"Rol {reg['rol']} eliminado.")


class PaginaUsuarios(PaginaSeguridad):
    def __init__(self, ventana):
        super().__init__(ventana, "Usuarios", "Usuarios de PostgreSQL (con ellos se entra a pgAdmin). "
                         "Sus permisos vienen de los grupos (roles) a los que pertenecen.",
                         ["Usuario", "Grupos (roles)"])
        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText("nombre_usuario")
        self.txt_clave = QLineEdit()
        self.txt_clave.setPlaceholderText("Contraseña")
        self.txt_clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.controles.addWidget(self.txt_usuario)
        self.controles.addWidget(self.txt_clave)
        self.boton("Crear usuario", self.crear, "primario")
        self.boton("Cambiar contraseña", self.cambiar_clave)
        self.boton("Eliminar seleccionado", self.eliminar, "peligro")

    def cargar(self):
        self.registros = self.llenar(seg_usuarios(self.bd), ["usuario", "roles"])

    def crear(self):
        usuario = self.txt_usuario.text().strip().lower()
        if self.resultado(seg_crear_usuario(self.bd, usuario, self.txt_clave.text()),
                          f"Usuario {usuario} creado. Agrégalo a un grupo en Seguridad › Grupos."):
            self.txt_usuario.clear()
            self.txt_clave.clear()

    def cambiar_clave(self):
        reg = self.seleccion()
        if reg and self.resultado(seg_cambiar_clave(self.bd, reg["usuario"], self.txt_clave.text()),
                                  f"Contraseña de {reg['usuario']} cambiada."):
            self.txt_clave.clear()

    def eliminar(self):
        reg = self.seleccion()
        if reg and self.confirmar(f"¿Eliminar el usuario {reg['usuario']}?"):
            self.resultado(seg_eliminar(self.bd, reg["usuario"]), f"Usuario {reg['usuario']} eliminado.")


class PaginaGrupos(PaginaSeguridad):
    def __init__(self, ventana):
        super().__init__(ventana, "Grupos", "Cada rol funciona como grupo: el usuario que agregues "
                         "hereda los permisos del rol.", ["Grupo (rol)", "Usuario"])
        self.cmb_rol, self.cmb_usuario = QComboBox(), QComboBox()
        for etiqueta, combo in (("Grupo:", self.cmb_rol), ("Usuario:", self.cmb_usuario)):
            combo.setMinimumWidth(170)
            self.controles.addWidget(QLabel(etiqueta))
            self.controles.addWidget(combo)
        self.boton("Agregar al grupo", self.agregar, "primario")
        self.boton("Quitar seleccionado", self.quitar, "peligro")
        self.controles.addStretch()

    def cargar(self):
        for combo, r, col in ((self.cmb_rol, seg_roles(self.bd), "rol"),
                              (self.cmb_usuario, seg_usuarios(self.bd), "usuario")):
            combo.clear()
            combo.addItems([reg[col] for reg in r["registros"]])
        self.registros = self.llenar(seg_grupos(self.bd), ["rol", "usuario"])

    def agregar(self):
        rol, usuario = self.cmb_rol.currentText(), self.cmb_usuario.currentText()
        if rol and usuario:
            self.resultado(seg_agregar_a_grupo(self.bd, rol, usuario), f"{usuario} agregado al grupo {rol}.")

    def quitar(self):
        reg = self.seleccion()
        if reg and self.confirmar(f"¿Quitar a {reg['usuario']} del grupo {reg['rol']}?"):
            self.resultado(seg_quitar_de_grupo(self.bd, reg["rol"], reg["usuario"]),
                           f"{reg['usuario']} quitado del grupo {reg['rol']}.")


class PaginaPermisos(PaginaSeguridad):
    NOMBRES = ("Consultar", "Insertar", "Actualizar", "Eliminar")  # mismo orden que PRIVILEGIOS

    def __init__(self, ventana):
        super().__init__(ventana, "Permisos", "Marca lo que puede hacer el rol en cada tabla y pulsa "
                         "«Guardar permisos». Los usuarios heredan los permisos de sus grupos.",
                         ["Tabla", *self.NOMBRES])
        self.cmb_rol = QComboBox()
        self.cmb_rol.setMinimumWidth(220)
        self.cmb_rol.currentTextChanged.connect(self.cargar_permisos)
        self.controles.addWidget(QLabel("Rol o usuario:"))
        self.controles.addWidget(self.cmb_rol)
        self.boton("Guardar permisos", self.guardar, "primario")
        self.controles.addStretch()

    def cargar(self):
        actual = self.cmb_rol.currentText()
        nombres = ([reg["rol"] for reg in seg_roles(self.bd)["registros"]]
                   + [reg["usuario"] for reg in seg_usuarios(self.bd)["registros"]])
        self.cmb_rol.blockSignals(True)
        self.cmb_rol.clear()
        self.cmb_rol.addItems(nombres)
        if actual in nombres:
            self.cmb_rol.setCurrentText(actual)
        self.cmb_rol.blockSignals(False)
        self.cargar_permisos()

    def cargar_permisos(self):
        rol = self.cmb_rol.currentText()
        tablas = seg_tablas(self.bd)
        actuales = seg_permisos(self.bd, rol) if rol else {"estado": True, "registros": []}
        if not tablas["estado"] or not actuales["estado"]:
            aviso(self, tablas["mensaje"] if not tablas["estado"] else actuales["mensaje"], True)
            return
        tiene = {(reg["tabla"], reg["privilegio"]) for reg in actuales["registros"]}
        self.tabla.setRowCount(len(tablas["registros"]))
        for fila, reg in enumerate(tablas["registros"]):
            self.tabla.setItem(fila, 0, QTableWidgetItem(reg["tabla"]))
            for c, privilegio in enumerate(PRIVILEGIOS, start=1):
                casilla = QTableWidgetItem()
                casilla.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                casilla.setCheckState(Qt.CheckState.Checked if (reg["tabla"], privilegio) in tiene
                                      else Qt.CheckState.Unchecked)
                self.tabla.setItem(fila, c, casilla)
        self.ventana.statusBar().showMessage(f"Permisos de {rol}" if rol else "No hay roles")

    def guardar(self):
        rol = self.cmb_rol.currentText()
        if not rol:
            return
        permisos = {self.tabla.item(fila, 0).text():
                    [p for c, p in enumerate(PRIVILEGIOS, start=1)
                     if self.tabla.item(fila, c).checkState() == Qt.CheckState.Checked]
                    for fila in range(self.tabla.rowCount())}
        self.resultado(seg_guardar_permisos(self.bd, rol, permisos), f"Permisos de {rol} guardados.")


# =====================================================================
# 10. VENTANA PRINCIPAL Y ARRANQUE
# =====================================================================
class VentanaPrincipal(QMainWindow):
    def __init__(self, bd, usuario):
        super().__init__()
        self.bd, self.usuario = bd, usuario
        self.cerrando_sesion = False
        self.setWindowTitle("Protección Civil V. Carranza · Sistema de archivo")
        self.resize(1200, 720)

        central = QWidget()
        caja = QVBoxLayout(central)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(0)
        encabezado = QFrame()
        encabezado.setObjectName("encabezado")
        fila = QHBoxLayout(encabezado)
        fila.setContentsMargins(24, 10, 24, 10)
        marca = QLabel("▲  Protección Civil · Venustiano Carranza")
        marca.setStyleSheet(f"color: {AZUL}; font-size: 13pt; font-weight: 700;")
        info = QLabel(f"{usuario['nombre']}  ·  {bd.motor}")
        info.setObjectName("subtitulo")
        fila.addWidget(marca)
        fila.addStretch()
        fila.addWidget(info)
        caja.addWidget(encabezado)

        self.paginas = QStackedWidget()
        self.inicio = PaginaInicio(self)
        self.paginas.addWidget(self.inicio)
        self.catalogos = [PaginaCatalogo(self, cat) for cat in CATALOGOS]
        for p in self.catalogos:
            self.paginas.addWidget(p)
        self.seguridad = {"Roles": PaginaRoles(self), "Grupos": PaginaGrupos(self),
                          "Usuarios": PaginaUsuarios(self), "Permisos": PaginaPermisos(self)}
        for p in self.seguridad.values():
            self.paginas.addWidget(p)
        caja.addWidget(self.paginas)
        self.setCentralWidget(central)
        self.crear_menu()
        self.ir_inicio()

    def crear_menu(self):
        barra = self.menuBar()
        archivo = barra.addMenu("Archivo")
        for texto, funcion in (("Inicio", self.ir_inicio), ("Cerrar sesión", self.cerrar_sesion),
                               ("Salir", self.close)):
            accion = QAction(texto, self)
            accion.triggered.connect(funcion)
            archivo.addAction(accion)

        dashboard = barra.addMenu("Dashboard")
        for texto in ("Ver dashboard", "Actualizar datos"):
            dashboard.addAction(texto, self.ir_inicio)

        catalogos = barra.addMenu("Catálogos")
        for i, cat in enumerate(CATALOGOS):
            sub = catalogos.addMenu(cat["titulo"])
            for texto, operacion in (("Insertar", "insertar"), ("Actualizar", "actualizar"),
                                     ("Eliminar", "eliminar"), ("Consultar", "consultar")):
                accion = QAction(texto, self)
                accion.triggered.connect(lambda _, k=i, o=operacion: self.abrir(k, o))
                sub.addAction(accion)

        seguridad = barra.addMenu("Seguridad")
        for nombre in self.seguridad:
            accion = QAction(nombre, self)
            accion.triggered.connect(lambda _, n=nombre: self.abrir_seguridad(n))
            seguridad.addAction(accion)

        ayuda = barra.addMenu("Ayuda")
        acerca = QAction("Acerca de", self)
        acerca.triggered.connect(lambda: aviso(self, "Sistema de archivo de Protección Civil V. Carranza\n"
                                                     "Yeicatl Jiménez Ramírez · TecNM Campus Jiquilpan"))
        ayuda.addAction(acerca)

    def ir_inicio(self):
        self.inicio.actualizar()
        self.paginas.setCurrentWidget(self.inicio)
        self.statusBar().showMessage("Dashboard")

    def abrir(self, indice, operacion):
        pagina = self.catalogos[indice]
        self.paginas.setCurrentWidget(pagina)
        pagina.txt_buscar.clear()
        pagina.cargar()
        pagina.limpiar()
        if operacion == "insertar":
            next(iter(pagina.widgets.values())).setFocus()
        elif operacion == "consultar":
            pagina.txt_buscar.setFocus()
        else:
            id_buscado, ok = QInputDialog.getInt(self, operacion.capitalize(),
                                                 f"ID del registro en {pagina.cat['titulo']}:", 1, 1)
            if not ok:
                return
            registro = crud_buscar_por_id(self.bd, pagina.cat, id_buscado)
            if registro is None:
                aviso(self, f"No existe el ID {id_buscado} en {pagina.cat['titulo']}.", True)
                return
            pagina.mostrar(registro)
            if operacion == "eliminar":
                pagina.eliminar()
            else:
                self.statusBar().showMessage("Modifica los campos y pulsa «Guardar cambios».")

    def abrir_seguridad(self, nombre):
        if self.bd.motor != "PostgreSQL":
            aviso(self, "El módulo de Seguridad trabaja con roles de PostgreSQL.\n"
                        "Cierra sesión y entra eligiendo PostgreSQL.", True)
            return
        pagina = self.seguridad[nombre]
        pagina.cargar()
        self.paginas.setCurrentWidget(pagina)

    def cerrar_sesion(self):
        self.cerrando_sesion = True
        self.close()

    def closeEvent(self, evento):
        self.bd.cerrar()
        evento.accept()


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--hash":
        print(generar_hash(sys.argv[2]))
        return
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(ESTILO)
    while True:
        login = VentanaLogin()
        if login.exec() != QDialog.DialogCode.Accepted:
            break
        ventana = VentanaPrincipal(login.bd, login.usuario)
        ventana.show()
        app.exec()
        if not ventana.cerrando_sesion:
            break


if __name__ == "__main__":
    main()
