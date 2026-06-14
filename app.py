from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import csv
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secretkey123"


# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()

    # Volunteers table
    c.execute("""
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            message TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Admin table
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    # 🔥 LOGIN LOGS TABLE (NEW ADD)
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # default admin
    c.execute("SELECT * FROM admin")
    if not c.fetchall():
        hashed = generate_password_hash("admin123")
        c.execute("INSERT INTO admin (username, password) VALUES (?, ?)",
                  ("admin", hashed))

    conn.commit()
    conn.close()


init_db()


# ---------------- VOLUNTEER PAGE ----------------
@app.route("/")
def volunteer_register():
    return render_template("index.html")


# ---------------- VOLUNTEER SUBMIT ----------------
@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    message = request.form["message"]

    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()
    c.execute("INSERT INTO volunteers (name, email, phone, message) VALUES (?, ?, ?, ?)",
              (name, email, phone, message))
    conn.commit()
    conn.close()

    return render_template("success.html")


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("volunteers.db")
        c = conn.cursor()

        c.execute("SELECT * FROM admin WHERE username=?", (username,))
        admin = c.fetchone()

        # 🔥 LOGIN CHECK
        if admin and check_password_hash(admin[2], password):
            session["admin"] = username

            # 🔥 SAVE LOGIN LOG (NEW ADD)
            c.execute("INSERT INTO login_logs (username) VALUES (?)", (username,))
            conn.commit()

            conn.close()
            return redirect("/dashboard")

        conn.close()
        return "Invalid Credentials"

    return render_template("admin_login.html")


# ---------------- ADMIN REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect("volunteers.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO admin (username, password) VALUES (?, ?)",
                      (username, password))
            conn.commit()
        except:
            return "User already exists"
        finally:
            conn.close()

        return redirect("/admin")

    return render_template("admin_register.html")


# ---------------- FORGOT PASSWORD ----------------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        username = request.form["username"]
        new_password = generate_password_hash(request.form["new_password"])

        conn = sqlite3.connect("volunteers.db")
        c = conn.cursor()
        c.execute("UPDATE admin SET password=? WHERE username=?",
                  (new_password, username))
        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("forgot.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/admin")

    admin_user = session.get("admin")

    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()

    c.execute("SELECT * FROM volunteers")
    data = c.fetchall()

    c.execute("SELECT COUNT(*) FROM volunteers")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM volunteers WHERE status='Approved'")
    approved = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM volunteers WHERE status='Pending'")
    pending = c.fetchone()[0]

    conn.close()

    return render_template("dashboard.html",
                           volunteers=data,
                           total=total,
                           approved=approved,
                           pending=pending,
                           admin=admin_user)


# ---------------- LOGIN LOGS PAGE (NEW) ----------------
@app.route("/logs")
def logs():
    if "admin" not in session:
        return redirect("/admin")

    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()
    c.execute("SELECT * FROM login_logs ORDER BY id DESC")
    data = c.fetchall()
    conn.close()

    return render_template("logs.html", logs=data)


# ---------------- APPROVE ----------------
@app.route("/approve/<int:id>")
def approve(id):
    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()
    c.execute("UPDATE volunteers SET status='Approved' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()
    c.execute("DELETE FROM volunteers WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/dashboard")


# ---------------- DOWNLOAD CSV ----------------
@app.route("/download")
def download():
    if "admin" not in session:
        return redirect("/admin")

    conn = sqlite3.connect("volunteers.db")
    c = conn.cursor()
    c.execute("SELECT * FROM volunteers")
    data = c.fetchall()
    conn.close()

    file = "volunteers.csv"

    with open(file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Email", "Phone", "Message", "Status"])
        writer.writerows(data)

    return send_file(file, as_attachment=True)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)