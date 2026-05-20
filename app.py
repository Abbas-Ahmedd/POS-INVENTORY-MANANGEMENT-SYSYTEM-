from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'pos_secret_key_change_in_production')

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
#app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
#app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_PASSWORD'] = 'root123'
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'pos_db')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND is_active=1", (username,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    today = datetime.now().date()
    cur.execute("SELECT COUNT(*) as cnt, IFNULL(SUM(total),0) as revenue FROM sales WHERE DATE(created_at)=%s AND status='completed'", (today,))
    today_stats = cur.fetchone()
    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE is_active=1")
    product_count = cur.fetchone()
    cur.execute("SELECT COUNT(*) as cnt FROM products WHERE stock_quantity <= low_stock_threshold AND is_active=1")
    low_stock = cur.fetchone()
    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_active=1")
    user_count = cur.fetchone()
    cur.execute("""SELECT s.*, u.full_name as cashier_name FROM sales s
                   JOIN users u ON s.cashier_id=u.id
                   ORDER BY s.created_at DESC LIMIT 8""")
    recent_sales = cur.fetchall()
    weekly = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        cur.execute("SELECT IFNULL(SUM(total),0) as rev FROM sales WHERE DATE(created_at)=%s AND status='completed'", (d,))
        r = cur.fetchone()
        weekly.append({'date': d.strftime('%a'), 'revenue': float(r['rev'])})
    cur.execute("""SELECT p.name, SUM(si.quantity) as sold FROM sale_items si
                   JOIN products p ON si.product_id=p.id JOIN sales s ON si.sale_id=s.id
                   WHERE s.status='completed' GROUP BY si.product_id ORDER BY sold DESC LIMIT 5""")
    top_products = cur.fetchall()
    cur.close()
    return render_template('dashboard.html', today_stats=today_stats, product_count=product_count,
        low_stock=low_stock, user_count=user_count, recent_sales=recent_sales,
        weekly=weekly, top_products=top_products)

@app.route('/pos')
@login_required
def pos():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    return render_template('pos.html', categories=categories)

@app.route('/api/products')
@login_required
def api_products():
    cat_id = request.args.get('category', '')
    search = request.args.get('search', '')
    cur = mysql.connection.cursor()
    query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.is_active=1 AND p.stock_quantity > 0"
    params = []
    if cat_id:
        query += " AND p.category_id=%s"
        params.append(cat_id)
    if search:
        query += " AND (p.name LIKE %s OR p.sku LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    query += " ORDER BY p.name LIMIT 50"
    cur.execute(query, params)
    products = cur.fetchall()
    cur.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    data = request.get_json()
    items = data.get('items', [])
    payment_method = data.get('payment_method', 'cash')
    discount = float(data.get('discount', 0))
    tax_rate = float(data.get('tax_rate', 0))
    amount_paid = float(data.get('amount_paid', 0))
    notes = data.get('notes', '')
    if not items:
        return jsonify({'success': False, 'message': 'No items in cart'})
    cur = mysql.connection.cursor()
    try:
        for item in items:
            cur.execute("SELECT stock_quantity, name FROM products WHERE id=%s AND is_active=1", (item['id'],))
            p = cur.fetchone()
            if not p:
                return jsonify({'success': False, 'message': 'Product not found'})
            if p['stock_quantity'] < item['qty']:
                return jsonify({'success': False, 'message': f'Insufficient stock for {p["name"]}'})
        subtotal = sum(float(i['price']) * int(i['qty']) for i in items)
        tax_amt = round(subtotal * tax_rate / 100, 2)
        total = round(subtotal - discount + tax_amt, 2)
        change = round(amount_paid - total, 2) if amount_paid >= total else 0
        invoice_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{session['user_id']}"
        cur.execute("""INSERT INTO sales (invoice_number, cashier_id, subtotal, discount, tax, total,
                       payment_method, amount_paid, change_given, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (invoice_no, session['user_id'], subtotal, discount, tax_amt, total,
                     payment_method, amount_paid, change, notes))
        sale_id = cur.lastrowid
        for item in items:
            item_total = float(item['price']) * int(item['qty'])
            cur.execute("""INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, total)
                           VALUES (%s,%s,%s,%s,%s,%s)""",
                        (sale_id, item['id'], item['name'], item['qty'], item['price'], item_total))
            cur.execute("UPDATE products SET stock_quantity = stock_quantity - %s WHERE id=%s", (item['qty'], item['id']))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'invoice_number': invoice_no, 'total': total, 'change': change, 'sale_id': sale_id})
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/invoice/<int:sale_id>')
@login_required
def invoice(sale_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT s.*, u.full_name as cashier_name FROM sales s JOIN users u ON s.cashier_id=u.id WHERE s.id=%s", (sale_id,))
    sale = cur.fetchone()
    if not sale:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('pos'))
    cur.execute("SELECT * FROM sale_items WHERE sale_id=%s", (sale_id,))
    items = cur.fetchall()
    cur.close()
    return render_template('invoice.html', sale=sale, items=items)

@app.route('/inventory')
@login_required
def inventory():
    cat_id = request.args.get('category', '')
    search = request.args.get('search', '')
    cur = mysql.connection.cursor()
    query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.is_active=1"
    params = []
    if cat_id:
        query += " AND p.category_id=%s"
        params.append(cat_id)
    if search:
        query += " AND (p.name LIKE %s OR p.sku LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    query += " ORDER BY p.name"
    cur.execute(query, params)
    products = cur.fetchall()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    return render_template('inventory.html', products=products, categories=categories, selected_cat=cat_id, search=search)

@app.route('/inventory/add', methods=['GET', 'POST'])
@admin_required
def add_product():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name'].strip()
        sku = request.form['sku'].strip()
        category_id = request.form.get('category_id') or None
        description = request.form.get('description', '')
        price = float(request.form['price'])
        cost_price = float(request.form.get('cost_price', 0))
        stock = int(request.form['stock_quantity'])
        threshold = int(request.form.get('low_stock_threshold', 10))
        unit = request.form.get('unit', 'pcs')
        try:
            cur.execute("""INSERT INTO products (name, sku, category_id, description, price, cost_price,
                           stock_quantity, low_stock_threshold, unit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (name, sku, category_id, description, price, cost_price, stock, threshold, unit))
            mysql.connection.commit()
            flash('Product added successfully!', 'success')
            return redirect(url_for('inventory'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    return render_template('product_form.html', product=None, categories=categories, action='Add')

@app.route('/inventory/edit/<int:pid>', methods=['GET', 'POST'])
@admin_required
def edit_product(pid):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name'].strip()
        sku = request.form['sku'].strip()
        category_id = request.form.get('category_id') or None
        description = request.form.get('description', '')
        price = float(request.form['price'])
        cost_price = float(request.form.get('cost_price', 0))
        stock = int(request.form['stock_quantity'])
        threshold = int(request.form.get('low_stock_threshold', 10))
        unit = request.form.get('unit', 'pcs')
        try:
            cur.execute("""UPDATE products SET name=%s, sku=%s, category_id=%s, description=%s,
                           price=%s, cost_price=%s, stock_quantity=%s, low_stock_threshold=%s, unit=%s WHERE id=%s""",
                        (name, sku, category_id, description, price, cost_price, stock, threshold, unit, pid))
            mysql.connection.commit()
            flash('Product updated!', 'success')
            return redirect(url_for('inventory'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
    cur.execute("SELECT * FROM products WHERE id=%s", (pid,))
    product = cur.fetchone()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    if not product:
        flash('Product not found.', 'danger')
        return redirect(url_for('inventory'))
    return render_template('product_form.html', product=product, categories=categories, action='Edit')

@app.route('/inventory/delete/<int:pid>', methods=['POST'])
@admin_required
def delete_product(pid):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE products SET is_active=0 WHERE id=%s", (pid,))
    mysql.connection.commit()
    cur.close()
    flash('Product removed.', 'success')
    return redirect(url_for('inventory'))

@app.route('/inventory/adjust/<int:pid>', methods=['POST'])
@admin_required
def adjust_stock(pid):
    adjustment_type = request.form['adjustment_type']
    qty_change = int(request.form['quantity_change'])
    notes = request.form.get('notes', '')
    cur = mysql.connection.cursor()
    cur.execute("SELECT stock_quantity FROM products WHERE id=%s", (pid,))
    p = cur.fetchone()
    if p:
        prev_qty = p['stock_quantity']
        new_qty = max(0, prev_qty + qty_change)
        cur.execute("UPDATE products SET stock_quantity=%s WHERE id=%s", (new_qty, pid))
        cur.execute("""INSERT INTO inventory_adjustments (product_id, user_id, adjustment_type,
                       quantity_change, previous_quantity, new_quantity, notes) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (pid, session['user_id'], adjustment_type, qty_change, prev_qty, new_qty, notes))
        mysql.connection.commit()
        flash('Stock adjusted!', 'success')
    cur.close()
    return redirect(url_for('inventory'))

@app.route('/categories')
@admin_required
def categories():
    cur = mysql.connection.cursor()
    cur.execute("SELECT c.*, COUNT(p.id) as product_count FROM categories c LEFT JOIN products p ON c.id=p.category_id AND p.is_active=1 GROUP BY c.id ORDER BY c.name")
    cats = cur.fetchall()
    cur.close()
    return render_template('categories.html', categories=cats)

@app.route('/categories/add', methods=['POST'])
@admin_required
def add_category():
    name = request.form['name'].strip()
    description = request.form.get('description', '')
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO categories (name, description) VALUES (%s,%s)", (name, description))
        mysql.connection.commit()
        flash('Category added!', 'success')
    except:
        flash('Category name already exists.', 'danger')
    cur.close()
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:cid>', methods=['POST'])
@admin_required
def delete_category(cid):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM categories WHERE id=%s", (cid,))
    mysql.connection.commit()
    cur.close()
    flash('Category deleted.', 'success')
    return redirect(url_for('categories'))

@app.route('/sales')
@login_required
def sales():
    from_date = request.args.get('from_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    to_date = request.args.get('to_date', datetime.now().strftime('%Y-%m-%d'))
    payment = request.args.get('payment', '')
    cur = mysql.connection.cursor()
    query = "SELECT s.*, u.full_name as cashier_name FROM sales s JOIN users u ON s.cashier_id=u.id WHERE DATE(s.created_at) BETWEEN %s AND %s"
    params = [from_date, to_date]
    if payment:
        query += " AND s.payment_method=%s"
        params.append(payment)
    query += " ORDER BY s.created_at DESC"
    cur.execute(query, params)
    all_sales = cur.fetchall()
    cur.execute("SELECT IFNULL(SUM(total),0) as total FROM sales WHERE DATE(created_at) BETWEEN %s AND %s AND status='completed'", (from_date, to_date))
    total_rev = cur.fetchone()
    cur.close()
    return render_template('sales.html', sales=all_sales, total_rev=total_rev, from_date=from_date, to_date=to_date, payment=payment)

@app.route('/reports')
@login_required
def reports():
    cur = mysql.connection.cursor()
    today = datetime.now().date()
    first_of_month = today.replace(day=1)
    cur.execute("SELECT DATE(created_at) as day, IFNULL(SUM(total),0) as revenue FROM sales WHERE DATE(created_at) >= %s AND status='completed' GROUP BY day ORDER BY day", (first_of_month,))
    monthly_data = cur.fetchall()
    cur.execute("""SELECT p.name, p.sku, SUM(si.quantity) as units_sold, SUM(si.total) as revenue
                   FROM sale_items si JOIN products p ON si.product_id=p.id JOIN sales s ON si.sale_id=s.id
                   WHERE s.status='completed' GROUP BY si.product_id ORDER BY units_sold DESC LIMIT 10""")
    top_products = cur.fetchall()
    cur.execute("SELECT payment_method, COUNT(*) as cnt, SUM(total) as revenue FROM sales WHERE status='completed' GROUP BY payment_method")
    payment_breakdown = cur.fetchall()
    cur.execute("""SELECT p.name, p.sku, p.stock_quantity, p.low_stock_threshold, c.name as category_name,
                   CASE WHEN p.stock_quantity = 0 THEN 'out_of_stock'
                        WHEN p.stock_quantity <= p.low_stock_threshold THEN 'low' ELSE 'ok' END as stock_status
                   FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.is_active=1 ORDER BY p.stock_quantity ASC""")
    inventory_status = cur.fetchall()
    cur.execute("SELECT IFNULL(SUM(total),0) as total FROM sales WHERE MONTH(created_at)=MONTH(NOW()) AND YEAR(created_at)=YEAR(NOW()) AND status='completed'")
    monthly_total = cur.fetchone()
    cur.execute("SELECT IFNULL(SUM(total),0) as total FROM sales WHERE DATE(created_at)=%s AND status='completed'", (today,))
    today_total = cur.fetchone()
    cur.execute("SELECT COUNT(*) as cnt FROM sales WHERE status='completed'")
    total_txns = cur.fetchone()
    cur.close()
    return render_template('reports.html', monthly_data=monthly_data, top_products=top_products,
        payment_breakdown=payment_breakdown, inventory_status=inventory_status,
        monthly_total=monthly_total, today_total=today_total, total_txns=total_txns)

@app.route('/users')
@admin_required
def users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users ORDER BY role, full_name")
    all_users = cur.fetchall()
    cur.close()
    return render_template('users.html', users=all_users)

@app.route('/users/add', methods=['POST'])
@admin_required
def add_user():
    username = request.form['username'].strip()
    full_name = request.form['full_name'].strip()
    password = request.form['password']
    role = request.form['role']
    cur = mysql.connection.cursor()
    try:
        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
                    (username, hashed, full_name, role))
        mysql.connection.commit()
        flash('User created!', 'success')
    except:
        flash('Username already exists.', 'danger')
    cur.close()
    return redirect(url_for('users'))

@app.route('/users/toggle/<int:uid>', methods=['POST'])
@admin_required
def toggle_user(uid):
    if uid == session['user_id']:
        flash("You can't deactivate yourself.", 'warning')
        return redirect(url_for('users'))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id=%s", (uid,))
    mysql.connection.commit()
    cur.close()
    flash('User status updated.', 'success')
    return redirect(url_for('users'))

@app.route('/users/reset_password/<int:uid>', methods=['POST'])
@admin_required
def reset_password(uid):
    new_password = request.form['new_password']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (generate_password_hash(new_password), uid))
    mysql.connection.commit()
    cur.close()
    flash('Password reset successfully.', 'success')
    return redirect(url_for('users'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        current_pw = request.form.get('current_password', '')
        new_pw = request.form.get('new_password', '')
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (session['user_id'],))
        u = cur.fetchone()
        if new_pw:
            if not check_password_hash(u['password_hash'], current_pw):
                flash('Current password is incorrect.', 'danger')
                cur.close()
                return redirect(url_for('profile'))
            cur.execute("UPDATE users SET full_name=%s, password_hash=%s WHERE id=%s",
                        (full_name, generate_password_hash(new_pw), session['user_id']))
        else:
            cur.execute("UPDATE users SET full_name=%s WHERE id=%s", (full_name, session['user_id']))
        mysql.connection.commit()
        session['full_name'] = full_name
        flash('Profile updated!', 'success')
    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()
    cur.close()
    return render_template('profile.html', user=user)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    count = cur.fetchone()
    if count['cnt'] > 0:
        flash('Setup already completed.', 'info')
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        full_name = request.form['full_name'].strip()
        password = request.form['password']
        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,'admin')",
                    (username, hashed, full_name))
        mysql.connection.commit()
        cur.close()
        flash('Admin account created! Please login.', 'success')
        return redirect(url_for('login'))
    cur.close()
    return render_template('setup.html')

# Make enumerate available in Jinja2 templates
app.jinja_env.globals.update(enumerate=enumerate)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
