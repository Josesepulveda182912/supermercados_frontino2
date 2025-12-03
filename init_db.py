import sqlite3
from werkzeug.security import generate_password_hash

DB = 'database.db'

schema = '''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    usuario TEXT UNIQUE,
    password TEXT,
    rol TEXT
);

CREATE TABLE IF NOT EXISTS supermercados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    direccion TEXT,
    telefono TEXT,
    horario_apertura TEXT,
    horario_cierre TEXT,
    descripcion TEXT,
    categoria TEXT,
    imagen TEXT
);
'''

conn = sqlite3.connect(DB)
c = conn.cursor()
c.executescript(schema)

# crear admin por defecto
admin_user = 'admin'
admin_pwd = '1234'
hashed = generate_password_hash(admin_pwd)
try:
    c.execute("INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
              ('Administrador', admin_user, hashed, 'admin'))
except Exception:
    pass

conn.commit()
conn.close()
print("Base creada. Usuario admin:", admin_user, "contraseña:", admin_pwd)
