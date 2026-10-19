# Sistema de archivo · Protección Civil V. Carranza

App de escritorio (PyQt6) con menú **Catálogos** y CRUD (Insertar, Actualizar, Eliminar, Consultar)
de las tablas maestras: Áreas, Empleados, Negocios, Eventos y Normatividad. Funciona con SQL Server y PostgreSQL.

## Ejecutar

1. Crear la base `protcivil_db` y ejecutar `protcivil_sqlserver.sql` o `protcivil_postgres.sql`.
2. Copiar `.env.example` como `.env` y poner las credenciales.
3. Instalar y correr:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Usuario inicial: `admin` · Contraseña: `admin123`
Para generar el hash de otra contraseña: `python app.py --hash NuevaClave`
