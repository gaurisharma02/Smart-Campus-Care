import sqlite3
from werkzeug.security import generate_password_hash

name = input("Enter admin name: ")
email = input("Enter admin email: ")
password = input("Create admin password: ")

conn = sqlite3.connect('campus.db')

existing_user = conn.execute(
    "SELECT id FROM users WHERE email = ?",
    (email,)
).fetchone()

if existing_user:
    print("This email is already registered. Please use another email.")

else:
    hashed_password = generate_password_hash(password)

    conn.execute(
        "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
        (name, email, hashed_password, 'admin')
    )

    conn.commit()
    print("Admin account created successfully!")

conn.close()