from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import pickle
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "your_secret_key"  # 🔒 Change in production

# ------------------ USERS ------------------
# Structure: users[phone] = {"name": ..., "password": ...}
users = {}

# ------------------ DOCTORS ------------------
# Structure: doctors[doctor_id] = {"name": ..., "phone": ..., "password": ...}
doctors = {}

# ------------------ ADMIN ------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# ------------------ PATIENT HISTORY ------------------
# Each entry: {"date":..., "phone":..., "name":..., "features": [...], "prediction": 0/1}
patients_history = []

# ------------------ LOAD MODEL ------------------
MODEL_PATH = os.path.join("models", "Liver2.pkl")
model = None
try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
except Exception as e:
    print("⚠️ Error loading model:", e)

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return render_template("home.html")

# ------------------ PATIENT REGISTER ------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not phone or not password:
            flash("All fields are required", "danger")
            return redirect(url_for("register"))

        if phone in users:
            flash("Phone number already registered", "warning")
            return redirect(url_for("register"))

        users[phone] = {"name": name, "password": generate_password_hash(password)}
        flash("✅ Registered successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# ------------------ PATIENT LOGIN ------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        user = users.get(phone)
        if user and check_password_hash(user["password"], password):
            session["user_phone"] = phone
            session["user_name"] = user["name"]
            flash("✅ Logged in successfully!", "success")
            return redirect(url_for("form"))

        flash("❌ Invalid credentials", "danger")

    return render_template("login.html")

# ------------------ PATIENT LOGOUT ------------------
@app.route("/logout")
def logout():
    session.pop("user_phone", None)
    session.pop("user_name", None)
    flash("👋 Logged out", "info")
    return redirect(url_for("home"))

# ------------------ LIVER FORM ------------------
@app.route("/form", methods=["GET", "POST"])
def form():
    if "user_phone" not in session:
        flash("Please login first", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            features = [
                float(request.form.get("Age", 0)),
                float(request.form.get("Total_Bilirubin", 0)),
                float(request.form.get("Direct_Bilirubin", 0)),
                float(request.form.get("Alkaline_Phosphotase", 0)),
                float(request.form.get("Alanine_Aminotransferase", 0)),
                float(request.form.get("Aspartate_Aminotransferase", 0)),
                float(request.form.get("Total_Protiens", 0)),
                float(request.form.get("Albumin", 0)),
                float(request.form.get("Albumin_and_Globulin_Ratio", 0))
            ]
        except ValueError:
            flash("⚠️ Please enter valid numbers!", "danger")
            return redirect(url_for("form"))

        if model is None:
            flash("⚠️ Model not loaded.", "danger")
            return redirect(url_for("form"))

        arr = np.array(features).reshape(1, -1)
        prediction = model.predict(arr)[0]
        result_text = "You have liver disease. Consult a doctor! ⚠️" if prediction else "No liver disease detected. Stay healthy 😊"

        patients_history.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "phone": session["user_phone"],
            "name": session["user_name"],
            "features": features,
            "prediction": prediction
        })

        return render_template("result.html", prediction=result_text, features=features)

    return render_template("form.html")

# ------------------ ADMIN LOGIN ------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = username
            flash("✅ Admin logged in successfully!", "success")
            return redirect(url_for("admin_dashboard"))

        flash("❌ Invalid admin credentials", "danger")
    return render_template("admin_login.html")

# ------------------ ADMIN DASHBOARD ------------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin" not in session:
        flash("⚠️ Please login as admin first", "warning")
        return redirect(url_for("admin_login"))

    total_patients = len(patients_history)
    total_doctors = len(doctors)

    patients_by_date = defaultdict(list)
    for entry in patients_history:
        patients_by_date[entry["date"]].append(entry)

    sorted_dates = sorted(patients_by_date.keys(), reverse=True)

    return render_template(
        "admin_dashboard.html",
        total_patients=total_patients,
        total_doctors=total_doctors,
        doctors=doctors,
        patients_by_date=patients_by_date,
        sorted_dates=sorted_dates
    )

# ------------------ ADMIN LOGOUT ------------------
@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)
    flash("👋 Admin logged out", "info")
    return redirect(url_for("home"))

# ------------------ ADD DOCTOR ------------------
@app.route("/admin/add_doctor", methods=["GET", "POST"])
def add_doctor():
    if "admin" not in session:
        flash("⚠️ Admin access required", "danger")
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", "").strip()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        if not doctor_id or not name or not phone or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for("add_doctor"))

        if doctor_id in doctors:
            flash("Doctor ID already exists!", "warning")
            return redirect(url_for("add_doctor"))

        doctors[doctor_id] = {
            "name": name,
            "phone": phone,
            "password": generate_password_hash(password)
        }

        flash(f"✅ Doctor {name} added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_doctor.html")

# ------------------ DELETE PATIENT ------------------
@app.route("/admin/delete_patient/<phone>", methods=["POST"])
def delete_patient(phone):
    if "admin" not in session:
        flash("⚠️ Admin access required", "danger")
        return redirect(url_for("admin_login"))

    if phone in users:
        del users[phone]
    global patients_history
    patients_history = [p for p in patients_history if p["phone"] != phone]

    flash("✅ Patient deleted successfully", "success")
    return redirect(url_for("admin_dashboard"))

# ------------------ DOCTOR LOGIN ------------------
@app.route("/doctor-login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        doctor_id = request.form.get("doctor_id", "").strip()
        password = request.form.get("password", "")

        doctor = doctors.get(doctor_id)
        if doctor and check_password_hash(doctor["password"], password):
            session["doctor_id"] = doctor_id
            session["doctor_name"] = doctor["name"]
            flash(f"✅ Welcome Dr. {doctor['name']}", "success")
            return redirect(url_for("doctor_dashboard"))

        flash("❌ Invalid credentials", "danger")

    return render_template("doctor_login.html")

# ------------------ DOCTOR DASHBOARD ------------------
@app.route("/doctor-dashboard")
def doctor_dashboard():
    if "doctor_id" not in session:
        flash("⚠️ Please login first", "warning")
        return redirect(url_for("doctor_login"))

    return render_template("doctor_dashboard.html",
                           doctor_name=session["doctor_name"],
                           patients=patients_history)

# ------------------ DOCTOR LOGOUT ------------------
@app.route("/doctor-logout")
def doctor_logout():
    session.pop("doctor_id", None)
    session.pop("doctor_name", None)
    flash("👋 Doctor logged out", "info")
    return redirect(url_for("home"))

# ------------------ RUN APP ------------------
if __name__ == "__main__":
    app.run(debug=True)
