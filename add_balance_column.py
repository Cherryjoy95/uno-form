import sqlite3

def add_balance_column():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    # Check if balance column exists
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if "balance" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN balance REAL DEFAULT 0.0")
        print("Added 'balance' column to orders table.")
    else:
        print("'balance' column already exists.")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_balance_column()
