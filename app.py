from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from flask import flash

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = 'your_secret_key_here'  # Set a unique and secret key for session management

UPLOAD_FOLDER = os.path.join("static", "uploads", "design_layouts")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.context_processor
def inject_dashboard_metrics():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM orders")
        total_orders = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders WHERE is_new = 1")
        new_orders_count = cur.fetchone()[0]

        cur.execute("SELECT SUM(price) FROM orders")
        total_revenue = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(balance) FROM orders WHERE status = 'Pending'")
        pending_payments = cur.fetchone()[0] or 0

        conn.close()

        return dict(
            total_orders=total_orders,
            new_orders_count=new_orders_count,
            total_revenue=total_revenue,
            pending_payments=pending_payments
        )
    except Exception:
        return dict(
            total_orders=0,
            new_orders_count=0,
            total_revenue=0,
            pending_payments=0
        )

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def root():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Total orders count
        cur.execute("SELECT COUNT(*) FROM orders")
        total_orders = cur.fetchone()[0]

        # New orders count (assuming is_new column exists)
        cur.execute("SELECT COUNT(*) FROM orders WHERE is_new = 1")
        new_orders_count = cur.fetchone()[0]

        # Total revenue (sum of price)
        cur.execute("SELECT SUM(price) FROM orders")
        total_revenue = cur.fetchone()[0] or 0

        # Pending payments (sum of balance where status is pending)
        cur.execute("SELECT SUM(balance) FROM orders WHERE status = 'Pending'")
        pending_payments = cur.fetchone()[0] or 0

        # Product count
        cur.execute("SELECT COUNT(*) FROM products")
        product_count = cur.fetchone()[0]

        # Total product orders (sum of quantity in jersey_orders)
        cur.execute("SELECT COUNT(*) FROM jersey_orders")
        total_product_orders = cur.fetchone()[0]

        # Product summary (product name and count)
        cur.execute("""
            SELECT product, COUNT(*) as count
            FROM orders
            GROUP BY product
            ORDER BY count DESC
        """)
        product_summary = cur.fetchall()

        # Order status counts for chart
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """)
        order_status_counts = cur.fetchall()
        order_status_data = {row['status']: row['count'] for row in order_status_counts}

        conn.close()

        return render_template('dashboard.html',
                               new_orders_count=new_orders_count,
                               total_orders=total_orders,
                               total_revenue=total_revenue,
                               pending_payments=pending_payments,
                               product_count=product_count,
                               total_product_orders=total_product_orders,
                               product_summary=product_summary,
                               order_status=order_status_data)
    except Exception as e:
        import traceback
        error_message = str(e)
        traceback.print_exc()
        from flask import flash
        flash(f"An error occurred: {error_message}", "danger")
        return render_template('dashboard.html', new_orders_count=0, total_orders=0, total_revenue=0, pending_payments=0, product_count=0, total_product_orders=0, product_summary=[], order_status={})

@app.route('/dashboard')
def dashboard():
    return root()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/jersey_form')
def jersey_form():
    return render_template('jersey_form.html')

@app.route("/upload_design_layout", methods=["POST"])
def upload_design_layout():
    return redirect(url_for("orders_list"))

def number_to_text(n):
    # Simple number to text conversion for dollars and cents
    units = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two_digit_number_to_text(num):
        if num < 10:
            return units[num]
        elif 10 <= num < 20:
            return teens[num - 10]
        else:
            ten_part = tens[num // 10]
            unit_part = units[num % 10] if num % 10 != 0 else ""
            return ten_part + (" " + unit_part if unit_part else "")

    if n is None:
        return "Zero dollars"

    try:
        n = float(n)
    except:
        return "Invalid amount"

    dollars = int(n)
    cents = int(round((n - dollars) * 100))

    dollar_text = ""
    if dollars == 0:
        dollar_text = "Zero dollars"
    elif dollars < 100:
        dollar_text = two_digit_number_to_text(dollars) + " dollars"
    else:
        # For simplicity, just show the number if >= 100
        dollar_text = f"{dollars} dollars"

    cent_text = ""
    if cents == 0:
        cent_text = "zero cents"
    elif cents < 10:
        cent_text = units[cents] + " cents"
    else:
        cent_text = two_digit_number_to_text(cents) + " cents"

    return dollar_text + " and " + cent_text

@app.route('/jersey_form/<int:order_id>')
def jersey_form_edit(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    order = cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()

    if order is None:
        flash("Order not found!", "danger")
        return redirect(url_for('orders_list'))

    balance_text = number_to_text(order['balance'])
    return render_template('jersey_form_edit.html', order=order, balance_text=balance_text)

@app.route('/jersey_form/view/<int:order_id>')
def view_jersey_form(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    jersey_details = cursor.execute("SELECT * FROM jersey_orders WHERE order_id = ?", (order_id,)).fetchall()
    order = cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()

    if not jersey_details:
        flash("Jersey details not found for this order.", "danger")
        return redirect(url_for('orders_list'))

    if order is None:
        flash("Order not found!", "danger")
        return redirect(url_for('orders_list'))

    return render_template('jersey_form_display.html', jersey_details=jersey_details, order=order)

@app.route("/test_jquery")
def test_jquery():
    return app.send_static_file("js/jquery.min.js")

@app.route("/test_static_path")
def test_static_path():
    root_path = app.root_path
    static_path = os.path.join(root_path, "static")
    static_exists = os.path.exists(static_path)
    return f"App root path: {root_path}<br>Static folder exists: {static_exists}<br>Static folder path: {static_path}"

from flask import request

@app.route('/orders_list')
def orders_list():
    selected_date = request.args.get('date', None)
    search_query = request.args.get('search', None)
    conn = get_db_connection()
    cur = conn.cursor()

    if selected_date and search_query:
        cur.execute("""
            SELECT id as reference_id, customer as customer_name, status as order_status,
                   order_date as date_ordered, date_needed as date_needed
            FROM orders
            WHERE date(order_date) = ? AND customer LIKE ?
            ORDER BY order_date DESC
        """, (selected_date, f'%{search_query}%'))
    elif selected_date:
        cur.execute("""
            SELECT id as reference_id, customer as customer_name, status as order_status,
                   order_date as date_ordered, date_needed as date_needed
            FROM orders
            WHERE date(order_date) = ?
            ORDER BY order_date DESC
        """, (selected_date,))
    elif search_query:
        cur.execute("""
            SELECT id as reference_id, customer as customer_name, status as order_status,
                   order_date as date_ordered, date_needed as date_needed
            FROM orders
            WHERE customer LIKE ?
            ORDER BY order_date DESC
        """, (f'%{search_query}%',))
    else:
        cur.execute("""
            SELECT id as reference_id, customer as customer_name, status as order_status,
                   order_date as date_ordered, date_needed as date_needed
            FROM orders
            ORDER BY order_date DESC
        """)
    orders = cur.fetchall()
    conn.close()

    # Generate continuous reference numbers starting from 1
    orders_with_ref = []
    total_orders = len(orders)
    for idx, order in enumerate(orders, start=1):
        order_dict = dict(order)
        order_dict['ref_number'] = total_orders - idx + 1
        orders_with_ref.append(order_dict)

    return render_template('orders_list.html', orders=orders_with_ref, selected_date=selected_date)

@app.route('/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        flash(f"Order {order_id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting order {order_id}: {str(e)}", "danger")
    return redirect(url_for('orders_list'))

@app.route('/products')
def products():
    conn = get_db_connection()
    cur = conn.cursor()

    # Get product types
    cur.execute("SELECT id, name FROM product_types")
    product_types = cur.fetchall()

    # Get products with product type name
    cur.execute("""
        SELECT p.id, p.product_type_id, pt.name as product_type_name, p.name, p.description, p.price, p.stock
        FROM products p
        LEFT JOIN product_types pt ON p.product_type_id = pt.id
    """)
    products = cur.fetchall()

    # For each product, get associated designs
    products_with_designs = []
    for product in products:
        cur.execute("SELECT id, name, mockup_image_path FROM designs WHERE product_type_id = ?", (product['product_type_id'],))
        designs = cur.fetchall()
        product_dict = dict(product)
        product_dict['designs'] = designs
        products_with_designs.append(product_dict)

    conn.close()
    return render_template('products_list.html', products=products_with_designs, product_types=product_types)

@app.route('/invoices')
def invoices():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT invoices.id, invoices.order_id, orders.customer, orders.product, invoices.invoice_date,
               COALESCE(invoices.amount, 0.0) as amount,
               COALESCE(invoices.payment_status, 'Pending') as payment_status
        FROM invoices
        JOIN orders ON invoices.order_id = orders.id
        ORDER BY invoices.invoice_date DESC
    """)
    invoices = cur.fetchall()
    conn.close()
    return render_template('invoices.html', invoices=invoices)

@app.route('/export_bulk_invoices', methods=['POST'])
def export_bulk_invoices():
    # Placeholder stub for export bulk invoices functionality
    return redirect(url_for('invoices'))

@app.route('/reports')
def reports():
    conn = get_db_connection()
    cur = conn.cursor()

    # Daily sales for last 30 days
    cur.execute("""
        SELECT date(order_date) as day, SUM(price) as total_sales
        FROM orders
        WHERE order_date >= date('now', '-30 days')
        GROUP BY day
        ORDER BY day DESC
    """)
    daily_sales = cur.fetchall()

    # Monthly sales for last 12 months
    cur.execute("""
        SELECT strftime('%Y-%m', order_date) as month, SUM(price) as total_sales
        FROM orders
        WHERE order_date >= date('now', '-12 months')
        GROUP BY month
        ORDER BY month DESC
    """)
    monthly_sales = cur.fetchall()

    conn.close()
    return render_template('reports.html', daily_sales=daily_sales, monthly_sales=monthly_sales)

def get_db_connection():
    conn = sqlite3.connect("orders.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if "is_new" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN is_new INTEGER DEFAULT 1")
        conn.commit()
    conn.close()

@app.before_request
def initialize():
    init_db()

@app.route('/submit_jersey_form', methods=['POST'])
def submit_jersey_form():
    try:
        edit_mode = request.form.get("edit_mode") == "True"
        order_id = request.form.get("order_id")

        customer = request.form.get("team_name")
        product = request.form.get("product")
        contact_person = request.form.get("contact_person")
        contact_number = request.form.get("contact_number")
        order_date = request.form.get("date_ordered")
        completion_date = request.form.get("completion_date")
        total_amount = request.form.get("total_amount")
        payment_terms = request.form.get("payment_terms")
        downpayment = request.form.get("downpayment")
        balance = request.form.get("balance")
        print_date = request.form.get("print_date")
        sew_date = request.form.get("sew_date")
        delivery_date = request.form.get("delivery_date")

        jersey_types = request.form.getlist("jersey_type[]")
        service_types = request.form.getlist("service_type[]")
        print_names = request.form.getlist("print_name[]")
        jersey_numbers = request.form.getlist("jersey_number[]")
        up_sizes = request.form.getlist("up_size[]")
        down_sizes = request.form.getlist("down_size[]")

        # Removed product field validation since product field was removed from form
        # if not product or product.strip() == "":
        #     flash("Product field is required.", "danger")
        #     if edit_mode and order_id:
        #         return redirect(url_for('jersey_form_edit', order_id=order_id))
        #     else:
        #         return redirect(url_for('jersey_form'))

        conn = get_db_connection()
        cursor = conn.cursor()

        if edit_mode and order_id:
            cursor.execute('''
                UPDATE orders SET customer = ?, product = ?, contact_person = ?, contact_number = ?, price = ?, payment_terms = ?, downpayment = ?, balance = ?, print_date = ?, sew_date = ?, delivery_date = ?, order_date = ?, date_needed = ?
                WHERE id = ?
            ''', (customer, product, contact_person, contact_number, total_amount or 0, payment_terms, downpayment, balance, print_date, sew_date, delivery_date, order_date, completion_date, order_id))

            cursor.execute("DELETE FROM jersey_orders WHERE order_id = ?", (order_id,))

            for i in range(len(jersey_types)):
                if jersey_types[i].strip() == "":
                    continue
                cursor.execute('''
                    INSERT INTO jersey_orders (order_id, jersey_type, service_type, print_name, jersey_number, up_size, down_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (order_id, jersey_types[i], service_types[i], print_names[i], jersey_numbers[i], up_sizes[i], down_sizes[i]))

            conn.commit()
            conn.close()
            flash("Order updated successfully.")
            return redirect(url_for("orders_list"))

        else:
            cursor.execute('''
                INSERT INTO orders (customer, product, contact_person, contact_number, price, payment_terms, downpayment, balance, print_date, sew_date, delivery_date, order_date, date_needed, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (customer, product, contact_person, contact_number, total_amount or 0, payment_terms, downpayment, balance, print_date, sew_date, delivery_date, order_date, completion_date, "Pending"))
            new_order_id = cursor.lastrowid

            for i in range(len(jersey_types)):
                if jersey_types[i].strip() == "":
                    continue
                cursor.execute('''
                    INSERT INTO jersey_orders (order_id, jersey_type, service_type, print_name, jersey_number, up_size, down_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (new_order_id, jersey_types[i], service_types[i], print_names[i], jersey_numbers[i], up_sizes[i], down_sizes[i]))

            conn.commit()
            # Fetch the inserted order and jersey orders to display
            cursor.execute("SELECT * FROM orders WHERE id = ?", (new_order_id,))
            order = cursor.fetchone()
            cursor.execute("SELECT * FROM jersey_orders WHERE order_id = ?", (new_order_id,))
            jersey_orders = cursor.fetchall()
            conn.close()
            flash("Submitted successfully")
            return redirect(url_for('orders_list'))
    except Exception as e:
        import traceback
        traceback.print_exc()
        with open("error.log", "a") as f:
            f.write("Exception in /submit_jersey_form:\n")
            traceback.print_exc(file=f)
            f.write("\n")
        flash(f"An error occurred: {str(e)}", "danger")
        if edit_mode and order_id:
            return redirect(url_for('jersey_form_edit', order_id=order_id))
        else:
            return redirect(url_for('jersey_form'))

@app.route('/jersey_form')
def jersey_form_redirect():
    return redirect(url_for('jersey_form'))

from flask import flash, redirect, url_for

@app.route('/jersey_form/new', methods=['GET', 'POST'])
def jersey_form_new():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        contact_person = request.form['contact_person']
        date_ordered = request.form['date_ordered']
        date_needed = request.form['date_needed']
        order_status = "Pending"

        jersey_types = request.form.getlist("jersey_type[]")
        service_types = request.form.getlist("service_type[]")
        print_names = request.form.getlist("print_name[]")
        jersey_numbers = request.form.getlist("jersey_number[]")
        up_sizes = request.form.getlist("up_size[]")
        down_sizes = request.form.getlist("down_size[]")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO orders (customer, contact_person, order_date, date_needed, status)
            VALUES (?, ?, ?, ?, ?)
        """, (customer_name, contact_person, date_ordered, date_needed, order_status))
        new_order_id = cursor.lastrowid

        for i in range(len(jersey_types)):
            if jersey_types[i].strip() == "":
                continue
            cursor.execute("""
                INSERT INTO jersey_orders (order_id, jersey_type, service_type, print_name, jersey_number, up_size, down_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (new_order_id, jersey_types[i], service_types[i], print_names[i], jersey_numbers[i], up_sizes[i], down_sizes[i]))

        conn.commit()
        conn.close()

        flash("Submitted successfully!", "success")
        return redirect(url_for('orders_list'))
    else:
        return render_template('jersey_form.html')

@app.route('/test_jersey_form_new')
def test_jersey_form_new():
    return "Test Jersey Form New Route is working"

def migrate_orders_table():
    pass

def init_products_table():
    pass

def init_product_types_table():
    pass

def init_designs_table():
    pass

# Removed init functions for customers and employees as they are not needed
# def init_customers_table():
#     pass

# def init_employees_table():
#     pass

def init_invoices_table():
    pass

def init_settings_table():
    pass

def init_jersey_orders_table():
    pass



if __name__ == "__main__":
    migrate_orders_table()
    init_products_table()
    init_product_types_table()
    init_designs_table()
    # Removed init calls for customers and employees
    # init_customers_table()
    # init_employees_table()
    init_invoices_table()
    init_settings_table()
    init_jersey_orders_table()

@app.route('/order_status')
def order_status_overview():
    order_status_data = {
        'Processing': 30,
        'For Layout': 20,
        'For Printing': 25,
        'For Tailoring': 15,
        'Done / Ready to Pickup': 10,
    }
    return render_template('order_status.html', order_status=order_status_data)

    app.run(debug=True)
