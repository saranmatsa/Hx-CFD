import sqlite3

conn = sqlite3.connect('data/cfd.db')
cursor = conn.cursor()
cursor.execute("SELECT username, email, hashed_password, status FROM users WHERE username = 'testuser'")
user = cursor.fetchone()
print('User:', user)
conn.close()