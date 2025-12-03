import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'images')

app = Flask(__name__)
app.secret_key = 'frontino_secret_simple'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---- Home: login ----
@app.route('/')
def home():
    # if logged redirect
    if session.get('usuario'):
        if session.get('rol') == 'admin':
            return redirect(url_for('admin_panel'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario'].strip()
        password = request.form['password'].strip()

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
        u = cur.fetchone()
        db.close()
        if u and check_password_hash(u['password'], password):
            session['usuario'] = u['usuario']
            session['rol'] = u['rol']
            session['nombre'] = u['nombre']
            flash('Bienvenido ' + u['nombre'], 'success')
            if u['rol'] == 'admin':
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')

    return render_template('login.html')

# ---- Register (public creates usuario role) ----
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        usuario = request.form['usuario'].strip()
        password = request.form['password'].strip()
        if not (nombre and usuario and password):
            flash('Completa todos los campos', 'warning')
            return redirect(url_for('register'))

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("INSERT INTO usuarios (nombre, usuario, password, rol) VALUES (?, ?, ?, ?)",
                        (nombre, usuario, generate_password_hash(password), 'usuario'))
            db.commit()
            flash('Cuenta creada. Ya puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya existe', 'danger')
        finally:
            db.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---- Admin panel ----
def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*a, **k):
        if session.get('rol') != 'admin':
            flash('Acceso denegado. Inicia sesión como admin.', 'danger')
            return redirect(url_for('login'))
        return fn(*a, **k)
    return wrapper

@app.route('/admin')
@admin_required
def admin_panel():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM supermercados ORDER BY nombre")
    rows = cur.fetchall()
    db.close()
    return render_template('admin_panel.html', supermercados=rows)

@app.route('/admin/add', methods=['GET','POST'])
@admin_required
def admin_add():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        direccion = request.form['direccion'].strip()
        telefono = request.form['telefono'].strip()
        apertura = request.form['apertura'].strip()
        cierre = request.form['cierre'].strip()
        descripcion = request.form['descripcion'].strip()
        imagen_filename = request.form.get('imagen', '').strip() or None

        db = get_db()
        cur = db.cursor()
        cur.execute("""INSERT INTO supermercados
            (nombre, direccion, telefono, horario_apertura, horario_cierre, descripcion, imagen)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (nombre, direccion, telefono, apertura, cierre, descripcion, imagen_filename))
        db.commit()
        db.close()
        flash('Supermercado agregado', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('admin_add.html')

@app.route('/admin/edit/<int:id>', methods=['GET','POST'])
@admin_required
def admin_edit(id):
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        direccion = request.form['direccion'].strip()
        telefono = request.form['telefono'].strip()
        apertura = request.form['apertura'].strip()
        cierre = request.form['cierre'].strip()
        descripcion = request.form['descripcion'].strip()

        imagen_filename = request.form.get('imagen', '').strip()
        
        # Si el campo de imagen está vacío, mantener la actual
        if not imagen_filename:
            cur.execute("SELECT imagen FROM supermercados WHERE id=?", (id,))
            r = cur.fetchone()
            if r:
                imagen_filename = r['imagen']

        cur.execute("""UPDATE supermercados SET
            nombre=?, direccion=?, telefono=?, horario_apertura=?, horario_cierre=?, descripcion=?, imagen=?
            WHERE id=?""", (nombre, direccion, telefono, apertura, cierre, descripcion, imagen_filename, id))
        db.commit()
        db.close()
        flash('Supermercado actualizado', 'success')
        return redirect(url_for('admin_panel'))

    cur.execute("SELECT * FROM supermercados WHERE id=?", (id,))
    row = cur.fetchone()
    db.close()
    if not row:
        flash('No encontrado', 'danger')
        return redirect(url_for('admin_panel'))
    return render_template('admin_edit.html', s=row)

@app.route('/admin/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT imagen FROM supermercados WHERE id=?", (id,))
    r = cur.fetchone()
    if r and r['imagen']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], r['imagen']))
        except:
            pass
    cur.execute("DELETE FROM supermercados WHERE id=?", (id,))
    db.commit()
    db.close()
    flash('Eliminado', 'success')
    return redirect(url_for('admin_panel'))

# ---- User dashboard & search ----
@app.route('/dashboard')
def user_dashboard():
    if not session.get('usuario'):
        return redirect(url_for('login'))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM supermercados ORDER BY nombre")
    rows = cur.fetchall()
    # collect categories
    cur.execute("SELECT DISTINCT categoria FROM supermercados WHERE categoria IS NOT NULL AND categoria<>''")
    cats = [r['categoria'] for r in cur.fetchall()]
    db.close()
    return render_template('user_dashboard.html', supermercados=rows, categorias=cats)

@app.route('/search', methods=['GET','POST'])
def search():
    if not session.get('usuario'):
        return redirect(url_for('login'))
    q = request.values.get('q','').strip()
    cat = request.values.get('categoria','').strip()

    sql = "SELECT * FROM supermercados WHERE 1=1"
    params = []
    if q:
        sql += " AND (nombre LIKE ? OR direccion LIKE ? OR descripcion LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like]
    if cat:
        sql += " AND categoria = ?"
        params.append(cat)

    db = get_db()
    cur = db.cursor()
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    # categories for filter
    cur.execute("SELECT DISTINCT categoria FROM supermercados WHERE categoria IS NOT NULL AND categoria<>''")
    cats = [r['categoria'] for r in cur.fetchall()]
    db.close()
    return render_template('user_dashboard.html', supermercados=rows, categorias=cats, q=q, selected_cat=cat)

@app.route('/detail/<int:id>')
def detail(id):
    if not session.get('usuario'):
        return redirect(url_for('login'))
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM supermercados WHERE id=?", (id,))
    s = cur.fetchone()
    db.close()
    if not s:
        flash('No encontrado', 'danger')
        return redirect(url_for('user_dashboard'))
    return render_template('detail.html', s=s)

@app.route('/images/<path:filename>')
def images(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # ensure DB exists
    if not os.path.exists(DB_PATH):
        print('Database not found. Ejecuta init_db.py primero.')
    app.run(debug=True)
