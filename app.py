from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'campuscare_secret_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect('campus.db')
    conn.row_factory = sqlite3.Row
    return conn


def update_complaints_table():
    conn = get_db_connection()

    columns = [
        row['name']
        for row in conn.execute("PRAGMA table_info(complaints)").fetchall()
    ]

    new_columns = {
        'title': 'TEXT',
        'location': 'TEXT',
        'image': 'TEXT'
    }

    for column, data_type in new_columns.items():
        if column not in columns:
            conn.execute(
                f"ALTER TABLE complaints ADD COLUMN {column} {data_type}"
            )

    conn.commit()
    conn.close()


update_complaints_table()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            message = "Passwords do not match!"

        else:
            conn = get_db_connection()
            hashed_password = generate_password_hash(password)

            try:
                conn.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                    (name, email, hashed_password, 'student')
                )
                conn.commit()
                message = "Registration successful! Please login."

            except sqlite3.IntegrityError:
                message = "Email already registered!"

            finally:
                conn.close()

    return render_template('register.html', message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ""

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('student'))

        else:
            message = "Invalid email or password!"
    return render_template('login.html', message=message)


@app.route('/student')
def student():
    if 'user_id' not in session:
                                 return redirect(url_for('login'))

    return render_template('student.html', name=session['user_name'])


@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    message = ""

    if request.method == 'POST':
        category = request.form['category']
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']

        image = request.files.get('image')
        image_name = None

        if image and image.filename:
            filename = secure_filename(image.filename)
            extension = os.path.splitext(filename)[1].lower()

            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            if extension not in allowed_extensions:
                message = "Please upload a valid image file!"
                return render_template('complaint.html', message=message)

            image_name = str(uuid.uuid4()) + extension
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))

        conn = get_db_connection()

        conn.execute(
            """INSERT INTO complaints
            (user_id, category, title, description, location, image, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session['user_id'],
                category,
                title,
                description,
                location,
                image_name,
                'Pending'
            )
        )

        conn.commit()
        conn.close()

        message = "Complaint submitted successfully!"

    return render_template('complaint.html', message=message)
@app.route('/my_complaints')
def my_complaints():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    complaints = conn.execute(
        """SELECT * FROM complaints
        WHERE user_id = ?
        ORDER BY date DESC""",
        (session['user_id'],)
    ).fetchall()

    conn.close()

    return render_template('my_complaints.html', complaints=complaints)
@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM complaints"
    ).fetchone()[0]

    pending = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE status = 'Pending'"
    ).fetchone()[0]

    resolved = conn.execute(
        "SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'"
    ).fetchone()[0]

    complaints = conn.execute(
        "SELECT * FROM complaints ORDER BY date DESC"
    ).fetchall()

    conn.close()

    return render_template(
        'admin.html',
        total=total,
        pending=pending,
        resolved=resolved,
        complaints=complaints
    )


@app.route('/update_status', methods=['POST'])
def update_status():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    complaint_id = request.form['complaint_id']
    status = request.form['status']

    conn = get_db_connection()

    conn.execute(
        "UPDATE complaints SET status = ? WHERE id = ?",
        (status, complaint_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for('admin'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)