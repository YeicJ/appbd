"""Sistema de Archivo · Protección Civil V. Carranza (PyQt6)."""
import hashlib
import hmac
import json
import os
import sys

from dotenv import load_dotenv
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDateEdit, QDialog, QFormLayout, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
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
def crear_conexion(motor):
    # [A3] Lee las credenciales del archivo .env y crea la clase de conexión del motor elegido.
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
        "usuario": os.getenv("PG_USUARIO", "postgres"),
        "contrasena": os.getenv("PG_CONTRASENA", ""),
    })


class BaseDatos:
    def __init__(self, motor):
        # [A4] Se abre la conexión una vez y se guarda el marcador del driver ("?" o "%s").
        self.motor = motor
        self.conexion = crear_conexion(motor)
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
# 4. INTERFAZ (generada con IA, no forma parte de lo que se evalúa)
# =====================================================================
AZUL, NARANJA, FONDO = "#16324F", "#E8710A", "#F3F1EC"

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
"""


def aviso(padre, texto, error=False):
    (QMessageBox.warning if error else QMessageBox.information)(padre, "Protección Civil", texto)


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
        try:
            bd = BaseDatos(self.motor.currentText())
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


class PaginaInicio(QWidget):
    def __init__(self, ventana):
        super().__init__()
        self.setObjectName("pagina")
        self.ventana = ventana
        self.numeros = {}
        caja = QVBoxLayout(self)
        caja.setContentsMargins(30, 24, 30, 24)
        titulo = QLabel("Panel general")
        titulo.setObjectName("tituloPagina")
        sub = QLabel("Selecciona un catálogo o usa el menú «Catálogos».")
        sub.setObjectName("subtitulo")
        caja.addWidget(titulo)
        caja.addWidget(sub)
        caja.addSpacing(16)
        rejilla = QGridLayout()
        rejilla.setSpacing(16)
        for i, cat in enumerate(CATALOGOS):
            tarjeta = QPushButton()
            tarjeta.setObjectName("tarjeta")
            tarjeta.setCursor(Qt.CursorShape.PointingHandCursor)
            tarjeta.setMinimumHeight(120)
            interior = QVBoxLayout(tarjeta)
            n = QLabel("–")
            n.setObjectName("numero")
            interior.addWidget(n)
            interior.addWidget(QLabel(f"{cat['titulo']} registrados"))
            tarjeta.clicked.connect(lambda _, k=i: ventana.abrir(k, "consultar"))
            self.numeros[cat["tabla"]] = n
            rejilla.addWidget(tarjeta, i // 3, i % 3)
        caja.addLayout(rejilla)
        caja.addStretch()

    def actualizar(self):
        for cat in CATALOGOS:
            # [A9] Conteo de registros por catálogo para las tarjetas del inicio.
            r = self.ventana.bd.ejecutar(f"SELECT COUNT(*) AS total FROM {cat['tabla']}")
            self.numeros[cat["tabla"]].setText(str(r["registros"][0]["total"]) if r["estado"] else "?")


class PaginaCatalogo(QWidget):
    def __init__(self, ventana, cat):
        super().__init__()
        self.setObjectName("pagina")
        self.ventana, self.cat, self.bd = ventana, cat, ventana.bd
        self.id_actual = None
        self.registros = []
        self.columnas = [cat["pk"]] + [c[0] for c in cat["campos"]]

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

    # ---------- CRUD ----------
    def cargar(self, seleccionar=None):
        # [A10] CONSULTAR: SELECT de todas las columnas; filtro opcional por ID o por texto.
        m, cat = self.bd.marcador, self.cat
        sql = f"SELECT {', '.join(self.columnas)} FROM {cat['tabla']}"
        texto = self.txt_buscar.text().strip()
        parametros = ()
        if texto.isdigit():
            sql += f" WHERE {cat['pk']} = {m}"
            parametros = (int(texto),)
        elif texto:
            # [A11] UPPER en ambos lados hace la búsqueda sin distinguir mayúsculas; % = "contiene".
            sql += f" WHERE UPPER({cat['busqueda']}) LIKE UPPER({m})"
            parametros = (f"%{texto}%",)
        sql += f" ORDER BY {cat['pk']}"
        r = self.bd.ejecutar(sql, parametros)
        if not r["estado"]:
            aviso(self, r["mensaje"], True)
            return
        self.registros = r["registros"]
        self.tabla.setRowCount(len(self.registros))
        for fila, reg in enumerate(self.registros):
            for c, col in enumerate(self.columnas):
                valor = reg[col]
                self.tabla.setItem(fila, c, QTableWidgetItem("" if valor is None else str(valor)))
            if seleccionar is not None and reg[cat["pk"]] == seleccionar:
                self.tabla.selectRow(fila)
        self.ventana.statusBar().showMessage(f"{cat['titulo']}: {len(self.registros)} registro(s)")

    def siguiente_id(self):
        # [A12] Las llaves no son autoincrementables: el nuevo ID es el máximo actual + 1.
        r = self.bd.ejecutar(f"SELECT MAX({self.cat['pk']}) AS maximo FROM {self.cat['tabla']}")
        maximo = r["registros"][0]["maximo"] if r["estado"] else None
        return (int(maximo) if maximo is not None else 0) + 1

    def buscar_por_id(self, id_buscado):
        # [A13] Trae un solo registro por su llave primaria (para Actualizar/Eliminar desde el menú).
        m = self.bd.marcador
        r = self.bd.ejecutar(f"SELECT {', '.join(self.columnas)} FROM {self.cat['tabla']} "
                             f"WHERE {self.cat['pk']} = {m}", (id_buscado,))
        return r["registros"][0] if r["estado"] and r["registros"] else None

    def insertar(self):
        valores = self.leer_formulario()
        if valores is None:
            return
        nuevo_id = self.siguiente_id()
        # [A14] INSERTAR: un marcador por columna; los valores viajan aparte en una tupla.
        marcadores = ", ".join([self.bd.marcador] * len(self.columnas))
        sql = f"INSERT INTO {self.cat['tabla']} ({', '.join(self.columnas)}) VALUES ({marcadores})"
        r = self.bd.ejecutar(sql, [nuevo_id] + valores)
        if not r["estado"]:
            aviso(self, f"No se pudo insertar:\n{r['mensaje']}", True)
            return
        aviso(self, f"Registro insertado con ID {nuevo_id}.")
        self.txt_buscar.clear()
        self.cargar(seleccionar=nuevo_id)
        self.mostrar(self.buscar_por_id(nuevo_id))

    def actualizar(self):
        if self.id_actual is None:
            return
        valores = self.leer_formulario()
        if valores is None:
            return
        m = self.bd.marcador
        # [A15] ACTUALIZAR: "col = marcador" por cada campo; el ID va al final para el WHERE.
        asignaciones = ", ".join(f"{c[0]} = {m}" for c in self.cat["campos"])
        sql = f"UPDATE {self.cat['tabla']} SET {asignaciones} WHERE {self.cat['pk']} = {m}"
        r = self.bd.ejecutar(sql, valores + [self.id_actual])
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
        # [A16] ELIMINAR: DELETE por llave primaria; si otra tabla lo usa, la BD lo rechaza (FK).
        m = self.bd.marcador
        r = self.bd.ejecutar(f"DELETE FROM {self.cat['tabla']} WHERE {self.cat['pk']} = {m}", (self.id_actual,))
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

        catalogos = barra.addMenu("Catálogos")
        for i, cat in enumerate(CATALOGOS):
            sub = catalogos.addMenu(cat["titulo"])
            for texto, operacion in (("Insertar", "insertar"), ("Actualizar", "actualizar"),
                                     ("Eliminar", "eliminar"), ("Consultar", "consultar")):
                accion = QAction(texto, self)
                accion.triggered.connect(lambda _, k=i, o=operacion: self.abrir(k, o))
                sub.addAction(accion)

        ayuda = barra.addMenu("Ayuda")
        acerca = QAction("Acerca de", self)
        acerca.triggered.connect(lambda: aviso(self, "Sistema de archivo de Protección Civil V. Carranza\n"
                                                     "Yeicatl Jiménez Ramírez · TecNM Campus Jiquilpan"))
        ayuda.addAction(acerca)

    def ir_inicio(self):
        self.inicio.actualizar()
        self.paginas.setCurrentWidget(self.inicio)
        self.statusBar().showMessage("Inicio")

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
            registro = pagina.buscar_por_id(id_buscado)
            if registro is None:
                aviso(self, f"No existe el ID {id_buscado} en {pagina.cat['titulo']}.", True)
                return
            pagina.mostrar(registro)
            if operacion == "eliminar":
                pagina.eliminar()
            else:
                self.statusBar().showMessage("Modifica los campos y pulsa «Guardar cambios».")

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
