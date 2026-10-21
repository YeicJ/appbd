# [C1] Clases de conexión a SQL Server y PostgreSQL.
#
# Secciones de este archivo:
#   1. Clase base: lo que comparten los dos motores
#        - abrir y cerrar la conexión
#        - ejecutar consultas (SELECT / INSERT / UPDATE / DELETE), commit y rollback
#   2. Conexión a SQL Server
#   3. Conexión a PostgreSQL
import json


# =====================================================================
# 1. CLASE BASE (común a SQL Server y PostgreSQL)
# =====================================================================
class _ConexionBase:
    # [C2] Marcador de parámetros del driver ("?" en SQL Server, "%s" en PostgreSQL).
    MARCADOR = "?"

    def __init__(self, datos):
        # [C3] "datos" trae servidor, base de datos, usuario y contraseña (vienen del .env).
        self.datos = datos
        self.conexion = None

    # ---------- Abrir y cerrar la conexión ----------
    def _conectar(self):
        # [C4] Cada motor implementa su propia forma de conectarse.
        raise NotImplementedError

    def Conectar(self):
        self.conexion = self._conectar()

    def Cerrar(self):
        if self.conexion is not None:
            self.conexion.close()
            self.conexion = None

    # ---------- Ejecutar consultas (SELECT / INSERT / UPDATE / DELETE) ----------
    def Ejecutar_consulta(self, sql, parametros=()):
        # [C5] Se abre un cursor; los valores van separados del SQL (evita inyección SQL).
        cursor = self.conexion.cursor()
        try:
            if parametros:
                cursor.execute(sql, parametros)
            else:
                cursor.execute(sql)

            # [C6] Si cursor.description no es None, la consulta devolvió columnas: fue un SELECT.
            if cursor.description is not None:
                columnas = [col[0] for col in cursor.description]
                registros = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]
                respuesta = {"estado": True, "mensaje": "Consulta realizada",
                             "registros": registros, "filas_afectadas": len(registros)}
            # [C7] Si es None fue INSERT/UPDATE/DELETE: se confirma la transacción con commit().
            else:
                self.conexion.commit()
                respuesta = {"estado": True, "mensaje": "Operación realizada",
                             "registros": [], "filas_afectadas": cursor.rowcount}
        except Exception as error:
            # [C8] Si algo falla se deshace lo que quedó a medias con rollback().
            self.conexion.rollback()
            respuesta = {"estado": False, "mensaje": str(error),
                         "registros": [], "filas_afectadas": 0}
        finally:
            # [C9] El cursor se cierra siempre, haya error o no.
            cursor.close()

        # [C10] Se devuelve texto JSON; default=str convierte fechas y decimales.
        return json.dumps(respuesta, default=str)


# =====================================================================
# 2. CONEXIÓN A SQL SERVER (librería mssql_python)
# =====================================================================
class ConexionSqlServer(_ConexionBase):
    MARCADOR = "?"

    def _conectar(self):
        import mssql_python
        # [C11] SQL Server usa una cadena de conexión "clave=valor;".
        cadena = f"Server={self.datos['servidor']};Database={self.datos['base']};"
        if self.datos.get("confiable"):
            cadena += "Trusted_Connection=yes;"
        else:
            cadena += f"Uid={self.datos['usuario']};Pwd={self.datos['contrasena']};"
        cadena += "Encrypt=no;TrustServerCertificate=yes;"
        return mssql_python.connect(cadena)


# =====================================================================
# 3. CONEXIÓN A POSTGRESQL (librería psycopg2)
# =====================================================================
class ConexionPostgres(_ConexionBase):
    MARCADOR = "%s"

    def _conectar(self):
        import psycopg2
        # [C12] PostgreSQL recibe los datos de conexión como parámetros con nombre.
        return psycopg2.connect(host=self.datos["servidor"], port=self.datos.get("puerto", 5432),
                                dbname=self.datos["base"], user=self.datos["usuario"],
                                password=self.datos["contrasena"])
