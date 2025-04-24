import sqlite3

def get_db_connection():
    conn = sqlite3.connect("orders.db")
    conn.row_factory = sqlite3.Row
    return conn

def add_missing_columns():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(orders)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    # Add contact_number column if missing
    if "contact_number" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN contact_number TEXT")

    # Add payment_terms column if missing
    if "payment_terms" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_terms TEXT")

    # Add downpayment column if missing
    if "downpayment" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN downpayment REAL DEFAULT 0.0")

    # Add print_date column if missing
    if "print_date" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN print_date TEXT")

    # Add sew_date column if missing
    if "sew_date" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN sew_date TEXT")

    # Add delivery_date column if missing
    if "delivery_date" not in existing_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN delivery_date TEXT")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_missing_columns()
