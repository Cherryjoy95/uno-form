import sqlite3

def add_contact_person_column():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()

    # Check if contact_person column exists
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if "contact_person" not in columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN contact_person TEXT")
        print("Added 'contact_person' column to 'orders' table.")
    else:
        print("'contact_person' column already exists in 'orders' table.")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    add_contact_person_column()
