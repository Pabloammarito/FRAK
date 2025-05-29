import sqlite3

DB_PATH = '_pyxashs_/frak.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.execute("ALTER TABLE clothing ADD COLUMN status TEXT DEFAULT 'klar'")
    print("Kolonnen 'status' tilføjet til clothing.")
except sqlite3.OperationalError as e:
    print("Kolonnen findes allerede eller anden fejl:", e)

conn.commit()
conn.close()