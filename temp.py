import sqlite3

# Create a new SQLite3 database file
conn = sqlite3.connect('newDB.db')

# Create a table
cursor = conn.cursor()
cursor.execute('''CREATE TABLE prescriptions
                 (id INTEGER PRIMARY KEY, billno INTEGER, ptid INTEGER , prname TEXT, prno INTEGER, dosage INTEGER)''')

# Commit the changes and close the connection
conn.commit()
conn.close()
