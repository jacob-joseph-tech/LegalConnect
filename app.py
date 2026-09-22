from flask import Flask, render_template, request, redirect, session, url_for
import google.generativeai as genai
import sqlite3
import uuid
import random
import smtplib
import os
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
from flask import g
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from email.mime.text import MIMEText

app = Flask(__name__)

from flask import send_from_directory

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png","jpg","jpeg","webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

app.secret_key = os.getenv("FLASK_SECRET_KEY")
from flask import g

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("database.db", timeout=10)
        g.db.row_factory = sqlite3.Row
    return g.db

def send_email(to_email, subject, body):

    sender_email = os.getenv("MAIL_USERNAME")
    app_password = os.getenv("MAIL_PASSWORD")  

    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.send_message(msg)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    return render_template("index.html")


# ---------------- REGISTER ----------------
@app.route("/register_client", methods=["GET", "POST"])
def register_client():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # --- VALIDATION ---
        if password != confirm_password:
            return render_template(
                "register_client.html",
                error="Passwords do not match"
            )

        if len(password) < 6:
            return render_template(
                "register_client.html",
                error="Password must be at least 6 characters"
            )

        hashed_password = generate_password_hash(password)

        db = get_db()

        try:
            cursor = db.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,'client')",
                (name, email, hashed_password)
            )

            user_id = cursor.lastrowid  # 🔥 correct way

            db.execute(
                "INSERT INTO clients (user_id) VALUES (?)",
                (user_id,)
            )

            db.commit()

        except sqlite3.IntegrityError:
            return render_template(
                "register_client.html",
                error="Email already exists. Please use another."
            )

        return redirect("/login/client")

    return render_template("register_client.html")

@app.route("/register_lawyer", methods=["GET", "POST"])
def register_lawyer():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        specialization = request.form["specialization"]
        experience = request.form["experience"]
        fee = request.form["fee"]
        license_number = request.form["license_number"]

        # --- PASSWORD VALIDATION ---
        if password != confirm_password:
            return render_template("register_lawyer.html", error="Passwords do not match")

        if len(password) < 6:
            return render_template("register_lawyer.html", error="Password too short")

        # --- NUMERIC VALIDATION ---
        if not experience.isdigit() or not fee.isdigit():
            return render_template("register_lawyer.html", error="Experience and fee must be numbers")

        # --- FILE VALIDATION ---
        file = request.files["verification_file"]

        if file.filename == "":
            return render_template("register_lawyer.html", error="No file selected")

        allowed_extensions = {"pdf", "png", "jpg", "jpeg"}
        ext = file.filename.rsplit(".", 1)[-1].lower()

        if ext not in allowed_extensions:
            return render_template("register_lawyer.html", error="Invalid file type")

        # Unique filename (critical)
        unique_filename = str(uuid.uuid4()) + "." + ext
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(file_path)

        hashed_password = generate_password_hash(password)

        db = get_db()

        try:
            cursor = db.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,'lawyer')",
                (name, email, hashed_password)
            )

            user_id = cursor.lastrowid

            db.execute("""
                INSERT INTO lawyers 
                (user_id,specialization,experience,consultation_fee,
                 license_number,verification_file,approved)
                VALUES (?,?,?,?,?,?,0)
            """, (
                user_id, specialization, experience, fee,
                license_number, unique_filename
            ))

            db.commit()

        except sqlite3.IntegrityError:
            return render_template(
                "register_lawyer.html",
                error="Email already exists. Please use another."
            )

        return redirect("/login/lawyer")

    return render_template("register_lawyer.html")
# ---------------- LOGIN ----------------
@app.route("/login/<role>", methods=["GET", "POST"])
def role_login(role):

    if role not in ["client", "lawyer", "admin"]:
        return redirect(url_for("index"))

    template = f"{role}_login.html"

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE email=? AND role=?",
            (email, role)
        ).fetchone()

        # USER NOT FOUND
        if not user:
            return render_template(
                template,
                error="Invalid email or password"
            )

        # ACCOUNT DEACTIVATED
        if user["is_active"] == 0:
            return render_template(
                template,
                error="Your account has been deactivated."
            )

        # WRONG PASSWORD
        if not check_password_hash(user["password"], password):
            return render_template(
                template,
                error="Invalid email or password"
            )

        # LAWYER APPROVAL CHECK
        if role == "lawyer":

            lawyer = db.execute(
                "SELECT approved, rejection_reason FROM lawyers WHERE user_id=?",
                (user["id"],)
            ).fetchone()

            if not lawyer:
                return render_template(
                    template,
                    error="Verification record missing."
                )

            if lawyer["rejection_reason"]:

                return render_template(
                    template,
                    error=f"""
                    Your registration was rejected.
                    Reason: {lawyer['rejection_reason']}
                    """
                )

            if lawyer["approved"] == 0:

                return render_template(
                    template,
                    error="Your account is pending admin approval."
                )

        # SUCCESS LOGIN
        session["user_id"] = user["id"]
        session["role"] = role
        session["name"] = user["name"]

        return redirect(url_for("dashboard"))

    return render_template(template)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    role = session.get("role")

    # ===== ADMIN DASHBOARD =====
    if role == "admin":

        stats = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM lawyers) AS total_applications,
            (SELECT COUNT(*) FROM lawyers WHERE approved=1) AS approved_lawyers,
            (SELECT COUNT(*) FROM lawyers WHERE approved=0 AND rejection_reason IS NULL) AS pending_lawyers,
            (SELECT COUNT(*) FROM lawyers WHERE rejection_reason IS NOT NULL) AS rejected_lawyers,

            (SELECT COUNT(*) FROM lawyers l JOIN users u ON l.user_id=u.id WHERE l.approved=1 AND u.is_active=1) AS active_lawyers,
            (SELECT COUNT(*) FROM lawyers l JOIN users u ON l.user_id=u.id WHERE l.approved=1 AND u.is_active=0) AS deactivated_lawyers,

            (SELECT COUNT(*) FROM clients) AS total_clients,
            (SELECT COUNT(*) FROM clients c JOIN users u ON c.user_id=u.id WHERE u.is_active=1) AS active_clients,

            (SELECT COUNT(*) FROM cases) AS total_cases,
            (SELECT COUNT(*) FROM cases WHERE status='Open') AS open_cases,
            (SELECT COUNT(*) FROM cases WHERE status='In Progress') AS progress_cases,
            (SELECT COUNT(*) FROM cases WHERE status='Closed') AS closed_cases
        """).fetchone()

        recent_lawyers = db.execute("""
            SELECT u.name, l.specialization
            FROM lawyers l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.id DESC LIMIT 5
        """).fetchall()

        recent_clients = db.execute("""
            SELECT name
            FROM users
            WHERE role='client'
            ORDER BY id DESC LIMIT 5
        """).fetchall()

        recent_cases = db.execute("""
            SELECT title, status
            FROM cases
            ORDER BY id DESC LIMIT 5
        """).fetchall()

        return render_template(
            "admin_dashboard.html",
            **dict(stats),
            recent_lawyers=recent_lawyers,
            recent_clients=recent_clients,
            recent_cases=recent_cases
        )

    # ===== LAWYER =====
    elif role == "lawyer":
        return redirect(url_for("lawyer_dashboard"))

    # ===== CLIENT =====
    elif role == "client":

        client = db.execute(
            "SELECT id FROM clients WHERE user_id=?",
            (session["user_id"],)
        ).fetchone()

        if not client:
            return redirect(url_for("logout"))  # safety fallback

        cases = db.execute("""
            SELECT *
            FROM cases
            WHERE client_id=?
            ORDER BY 
                CASE status
                    WHEN 'Open' THEN 1
                    WHEN 'In Progress' THEN 2
                    ELSE 3
                END,
                id DESC
            LIMIT 20
        """, (client["id"],)).fetchall()

        notif_count = db.execute("""
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id=? AND is_read=0
        """, (session["user_id"],)).fetchone()[0]

        return render_template(
            "client_dashboard.html",
            cases=cases,
            notif_count=notif_count
        )

    # ===== INVALID ROLE =====
    else:
        return redirect(url_for("logout"))

@app.route("/debug")
def debug():
    db = get_db()
    users = db.execute("SELECT * FROM users").fetchall()
    clients = db.execute("SELECT * FROM clients").fetchall()
    lawyers = db.execute("SELECT * FROM lawyers").fetchall()

    return f"""
    Users: {len(users)} <br>
    Clients: {len(clients)} <br>
    Lawyers: {len(lawyers)}
    """

@app.route("/create-case", methods=["GET", "POST"])
def create_case():
    if "user_id" not in session or session["role"] != "client":
        return redirect(url_for("login"))

    db = get_db()

    client = db.execute(
        "SELECT id FROM clients WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]

        db.execute(
            "INSERT INTO cases (client_id, title, description, status) VALUES (?,?,?,?)",
            (client["id"], title, description, "Open")
        )
        db.commit()

        return redirect(url_for("dashboard"))

    return render_template("create_case.html")

@app.route("/view-cases")
def view_cases():
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()

    cases = db.execute("""
        SELECT 
            cases.id,
            cases.title,
            cases.status,
            client_user.name AS client_name,
            lawyer_user.name AS lawyer_name
        FROM cases
        JOIN clients ON cases.client_id = clients.id
        JOIN users AS client_user ON clients.user_id = client_user.id
        LEFT JOIN lawyers ON cases.lawyer_id = lawyers.id
        LEFT JOIN users AS lawyer_user ON lawyers.user_id = lawyer_user.id
    """).fetchall()

    return render_template("view_cases.html", cases=cases)

@app.route("/assign-case/<int:case_id>", methods=["GET", "POST"])
def assign_case(case_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    db = get_db()

    case = db.execute(
        "SELECT * FROM cases WHERE id=?",
        (case_id,)
    ).fetchone()

    lawyers = db.execute("""
        SELECT lawyers.id, users.name 
        FROM lawyers
        JOIN users ON lawyers.user_id = users.id
    """).fetchall()

    if request.method == "POST":
        lawyer_id = request.form["lawyer_id"]

        db.execute(
            "UPDATE cases SET lawyer_id=?, status=? WHERE id=?",
            (lawyer_id, "In Progress", case_id)
        )
        db.commit()

        return "Lawyer assigned successfully!"

    form = "<h2>Assign Lawyer</h2><form method='POST'>"
    for l in lawyers:
        form += f"<input type='radio' name='lawyer_id' value='{l['id']}'> {l['name']}<br>"
    form += "<button type='submit'>Assign</button></form>"

    return form


@app.route("/lawyer-dashboard")
def lawyer_dashboard():
    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    lawyer = db.execute(
        "SELECT id FROM lawyers WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

  
    # Lawyer's cases
    cases = [dict(row) for row in db.execute("""
        SELECT cases.id, cases.title, cases.status,
               users.name AS client
        FROM cases
        JOIN clients ON cases.client_id = clients.id
        JOIN users ON clients.user_id = users.id
        WHERE cases.lawyer_id=?
    """, (lawyer["id"],)).fetchall()]

    for case in cases:

        ipc_sections = db.execute("""

        SELECT ipc_sections.section_code,
               ipc_sections.section_title

        FROM case_ipc_mapping

        JOIN ipc_sections
        ON ipc_sections.id = case_ipc_mapping.ipc_id

        WHERE case_ipc_mapping.case_id=?

        """,(case["id"],)).fetchall()

        case["ipc_sections"] = ipc_sections

    # Reviews
    reviews = db.execute("""
        SELECT reviews.rating,
               reviews.comment,
               users.name
        FROM reviews
        JOIN clients ON clients.id = reviews.client_id
        JOIN users ON users.id = clients.user_id
        WHERE reviews.lawyer_id=?
        ORDER BY reviews.created_at DESC
    """, (lawyer["id"],)).fetchall()

    avg = db.execute("""
        SELECT AVG(rating) as avg_rating
        FROM reviews
        WHERE lawyer_id=?
    """, (lawyer["id"],)).fetchone()

    notif_count = db.execute("""
    SELECT COUNT(*)
    FROM notifications
    WHERE user_id=? AND is_read=0
    """,(session["user_id"],)).fetchone()[0]

    return render_template(
        "lawyer_dashboard.html",
        cases=cases,
        reviews=reviews,
        avg_rating=avg["avg_rating"],               
        notif_count=notif_count
    )

@app.route("/update-status/<int:case_id>", methods=["GET", "POST"])
def update_status(case_id):
    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    if request.method == "POST":
        new_status = request.form["status"]

        db.execute(
            "UPDATE cases SET status=? WHERE id=?",
            (new_status, case_id)
        )
        db.commit()

        return redirect(url_for("lawyer_dashboard"))

    return render_template("update_status.html")

@app.route("/upload-file/<int:case_id>", methods=["GET", "POST"])
def upload_file(case_id):
    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    if request.method == "POST":
        file = request.files["file"]

        if not file or file.filename == "":
            return "No file selected"

        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        file.save(path)

        db.execute(
            "INSERT INTO case_files (case_id, file_name, file_path) VALUES (?,?,?)",
            (case_id, filename, path)
        )
        db.commit()

        return redirect(url_for("lawyer_dashboard"))

    return render_template("upload_file.html", case_id=case_id)

@app.route("/case-files/<int:case_id>")
def case_files(case_id):

    db = get_db()

    files = db.execute("""
    SELECT *
    FROM case_files
    WHERE case_id=?
    """,(case_id,)).fetchall()

    return render_template(
        "case_files.html",
        files=files
    )


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)


@app.route("/seed-ipc")
def seed_ipc():
    db = get_db()

    ipc_list = [
        ("420", "Cheating and dishonestly inducing delivery of property"),
        ("378", "Theft"),
        ("302", "Murder"),
        ("351", "Assault"),
        ("506", "Criminal intimidation")
    ]

    for code, title in ipc_list:
        db.execute(
            "INSERT INTO ipc_sections (section_code, section_title) VALUES (?,?)",
            (code, title)
        )

    db.commit()
    return "IPC sections added!"

@app.route("/map-ipc/<int:case_id>", methods=["GET", "POST"])
def map_ipc(case_id):

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    if request.method == "POST":

        selected_ipcs = request.form.getlist("ipc_ids")

        for ipc_id in selected_ipcs:

            db.execute("""
            INSERT OR IGNORE INTO case_ipc_mapping
            (case_id, ipc_id)
            VALUES (?, ?)
            """,(case_id, ipc_id))

        db.commit()

        return redirect(url_for("lawyer_dashboard"))

    ipc_sections = db.execute("""
    SELECT *
    FROM ipc_sections
    ORDER BY section_code
    """).fetchall()

    return render_template(
        "map_ipc.html",
        ipc_sections=ipc_sections
    )


@app.route("/ipc-bot", methods=["POST"])
def ipc_bot():

    description = request.form["description"]

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are a legal assistant for Indian law.

    A user described a legal issue. 

    1. Suggest possible IPC sections.
    2. Suggest the most suitable lawyer specialization.

    Possible lawyer types:
    - Criminal Lawyer
    - Civil Lawyer
    - Cyber Crime Lawyer
    - Family Lawyer
    - Corporate Lawyer

    Case description:
    {description}

    Respond in this format:

    IPC Sections:
    - IPC number – title

    Recommended Lawyer:
    - Lawyer specialization
    """

    response = model.generate_content(prompt)

    return response.text

@app.route("/search-lawyers")
def search_lawyers():

    if "user_id" not in session or session["role"] != "client":
        return redirect(url_for("role_login", role="client"))

    db = get_db()

    # ===== PAGINATION =====
    page = request.args.get("page", 1, type=int)
    PER_PAGE = 6
    offset = (page - 1) * PER_PAGE

    # ===== FILTERS =====
    specialization = request.args.get("specialization")
    rating = request.args.get("rating", type=float)
    experience = request.args.get("experience")
    fee = request.args.get("fee")
    sort = request.args.get("sort")

    base_query = """
        FROM lawyers
        JOIN users ON lawyers.user_id = users.id
        LEFT JOIN reviews ON reviews.lawyer_id = lawyers.id
        WHERE lawyers.approved = 1
        AND users.is_active = 1
    """

    filters = []
    params = []

    # ===== APPLY FILTERS =====

    if specialization:
        filters.append("lawyers.specialization = ?")
        params.append(specialization)

    if experience:
        if experience == "0-3":
            filters.append("lawyers.experience BETWEEN 0 AND 3")
        elif experience == "3-7":
            filters.append("lawyers.experience BETWEEN 3 AND 7")
        elif experience == "7+":
            filters.append("lawyers.experience >= 7")

    if fee:
        if fee == "0-500":
            filters.append("lawyers.consultation_fee BETWEEN 0 AND 500")
        elif fee == "500-1500":
            filters.append("lawyers.consultation_fee BETWEEN 500 AND 1500")
        elif fee == "1500+":
            filters.append("lawyers.consultation_fee >= 1500")

    # Combine filters safely
    filter_sql = ""
    if filters:
        filter_sql = " AND " + " AND ".join(filters)

    # ===== COUNT QUERY =====
    count_query = f"""
        SELECT COUNT(DISTINCT lawyers.id)
        {base_query}
        {filter_sql}
    """

    total = db.execute(count_query, params).fetchone()[0]
    total_pages = (total + PER_PAGE - 1) // PER_PAGE

    # Fix invalid page
    if page > total_pages and total_pages > 0:
        page = total_pages
        offset = (page - 1) * PER_PAGE

    # ===== MAIN QUERY =====
    main_params = params.copy()

    query = f"""
        SELECT lawyers.id,
               users.name,
               users.profile_photo,
               lawyers.specialization,
               lawyers.experience,
               lawyers.consultation_fee,
               ROUND(AVG(reviews.rating),1) as avg_rating,
               COUNT(reviews.id) as review_count
        {base_query}
        {filter_sql}
        GROUP BY lawyers.id
    """

    # Rating filter AFTER aggregation
    if rating:
        query += " HAVING COALESCE(avg_rating, 0) >= ?"
        main_params.append(rating)

    # Sorting
    if sort == "rating":
        query += " ORDER BY avg_rating DESC"
    elif sort == "experience":
        query += " ORDER BY lawyers.experience DESC"
    elif sort == "fee_low":
        query += " ORDER BY lawyers.consultation_fee ASC"
    else:
        query += " ORDER BY lawyers.id DESC"

    # Pagination
    query += " LIMIT ? OFFSET ?"
    main_params.extend([PER_PAGE, offset])

    lawyers = db.execute(query, main_params).fetchall()

    # ===== RANGE DISPLAY =====
    start = offset + 1 if total > 0 else 0
    end = min(offset + PER_PAGE, total)

    return render_template(
        "search_lawyers.html",
        lawyers=lawyers,
        page=page,
        total_pages=total_pages,
        total=total,
        start=start,
        end=end
    )

@app.route("/lawyer/<int:lawyer_id>")
def lawyer_profile(lawyer_id):

    db = get_db()

    lawyer = db.execute("""
        SELECT lawyers.id,
               users.name,
               users.email,
               lawyers.specialization,
               lawyers.experience,
               lawyers.consultation_fee
        FROM lawyers
        JOIN users ON users.id = lawyers.user_id
        WHERE lawyers.id = ? AND lawyers.approved = 1
    """, (lawyer_id,)).fetchone()

    if not lawyer:
        return "Lawyer not found or not approved."

    reviews = db.execute("""
        SELECT reviews.rating,
               reviews.comment,
               users.name
        FROM reviews
        JOIN clients ON clients.id = reviews.client_id
        JOIN users ON users.id = clients.user_id
        WHERE reviews.lawyer_id = ?
        ORDER BY reviews.created_at DESC
    """, (lawyer_id,)).fetchall()

    avg = db.execute("""
        SELECT AVG(rating) as avg_rating
        FROM reviews
        WHERE lawyer_id = ?
    """, (lawyer_id,)).fetchone()

    can_review = False

    if "user_id" in session and session["role"] == "client":
        client = db.execute(
        "SELECT id FROM clients WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if client:
        valid_case = db.execute("""
            SELECT id FROM cases
            WHERE client_id=? AND lawyer_id=? AND status='Closed'
        """, (client["id"], lawyer_id)).fetchone()

        if valid_case:
            already_reviewed = db.execute("""
                SELECT id FROM reviews
                WHERE client_id=? AND lawyer_id=?
            """, (client["id"], lawyer_id)).fetchone()

            if not already_reviewed:
                can_review = True

    availability = db.execute("""
        SELECT day_of_week, start_time, end_time
        FROM lawyer_availability
        WHERE lawyer_id=?
        ORDER BY
        CASE day_of_week
        WHEN 'Monday' THEN 1
        WHEN 'Tuesday' THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday' THEN 4
        WHEN 'Friday' THEN 5
        WHEN 'Saturday' THEN 6
        WHEN 'Sunday' THEN 7
        END
    """,(lawyer_id,)).fetchall()

    return render_template(
    "lawyer_profile.html",
    lawyer=lawyer,
    reviews=reviews,
    avg_rating=avg["avg_rating"],
    availability=availability,
    can_review=can_review
    
)

@app.route("/book-appointment/<int:lawyer_id>", methods=["GET","POST"])
def book_appointment(lawyer_id):

    if "user_id" not in session or session["role"] != "client":
        return redirect(url_for("login"))

    db = get_db()

    client = db.execute(
        "SELECT id FROM clients WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "POST":

        existing = db.execute("""
        SELECT id
        FROM appointments
        WHERE lawyer_id = ?
        AND appointment_date = ?
        AND appointment_time = ?
        """,(
           lawyer_id,
           request.form["date"],
           request.form["time"]
        )).fetchone()

        if existing:
            return "This time slot is already booked. Please choose another."

        db.execute("""
        INSERT INTO appointments
        (client_id, lawyer_id, appointment_date, appointment_time,
        case_title, case_description, meeting_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
        """,(
            client["id"],
            lawyer_id,
            request.form["date"],
            request.form["time"],
            request.form["title"],
            request.form["description"],
            request.form["meeting_type"]    
        ))

        db.commit()

# 🔔 Notify lawyer about new appointment
        lawyer_user = db.execute("""
        SELECT user_id
        FROM lawyers
        WHERE id=?
        """,(lawyer_id,)).fetchone()

        db.execute("""  
        INSERT INTO notifications (user_id,message)
        VALUES (?,?)
        """,(
        lawyer_user["user_id"],
        f"New appointment request received for {request.form['date']} at {request.form['time']}."
        ))

        db.commit()

        return redirect(url_for("dashboard"))

    availability = db.execute("""
    SELECT day_of_week,start_time,end_time
    FROM lawyer_availability
    WHERE lawyer_id=?
    """,(lawyer_id,)).fetchall()

    availability = [dict(row) for row in availability]

    booked_slots = db.execute("""
    SELECT appointment_date, appointment_time
    FROM appointments
    WHERE lawyer_id=?
    """,(lawyer_id,)).fetchall()

    booked_slots = [dict(row) for row in booked_slots]

    return render_template(
        "book_appointment.html",
        availability=availability,
        booked_slots=booked_slots
    )

@app.route("/lawyer-appointments")
def lawyer_appointments():
    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    lawyer = db.execute(
        "SELECT id FROM lawyers WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    appointments = db.execute("""
    SELECT 
        appointments.id,
        appointments.appointment_date,
        appointments.appointment_time,
        appointments.case_title,
        appointments.case_description,
        appointments.status,
        users.name AS client_name
    FROM appointments
    JOIN clients ON clients.id = appointments.client_id
    JOIN users ON users.id = clients.user_id
    WHERE appointments.lawyer_id = ?
    ORDER BY appointments.appointment_date DESC
    """,(lawyer["id"],)).fetchall()

    return render_template("lawyer_appointments.html", appointments=appointments)


@app.route("/approve-appointment/<int:appointment_id>", methods=["GET","POST"])
def approve_appointment(appointment_id):

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    appt = db.execute("""
        SELECT *
        FROM appointments
        WHERE id=?
    """, (appointment_id,)).fetchone()

    if not appt:
        return "Appointment not found"

    # If lawyer submits form
    if request.method == "POST":

        meeting_type = request.form["meeting_type"]
        meeting_link = request.form.get("meeting_link")
        meeting_location = request.form.get("meeting_location")

        # Approve appointment
        db.execute("""
        UPDATE appointments
        SET status='Approved',
            meeting_type=?,
            meeting_link=?,
            meeting_location=?
        WHERE id=?
        """,(meeting_type,meeting_link,meeting_location,appointment_id))

        # Convert appointment → case
        db.execute("""
        INSERT INTO cases (client_id, lawyer_id, title, description, status)
        VALUES (?, ?, ?, ?, 'Open')
        """, (
            appt["client_id"],
            appt["lawyer_id"],
            appt["case_title"],
            appt["case_description"]
        ))

        # Notify client
        client = db.execute("""
            SELECT user_id
            FROM clients
            WHERE id=?
        """, (appt["client_id"],)).fetchone()

        db.execute("""
        INSERT INTO notifications (user_id,message)
        VALUES (?,?)
        """,(
        client["user_id"],
        "Your appointment has been approved. Please check meeting details."
        ))

        db.commit()

        return redirect(url_for("lawyer_appointments"))

    return render_template("approve_appointment.html", appointment=appt)

@app.route("/reject-appointment/<int:appointment_id>")
def reject_appointment(appointment_id):
    db = get_db()
    db.execute("""
        UPDATE appointments SET status='Rejected' WHERE id=?
    """, (appointment_id,))

    appointment = db.execute("""
    SELECT clients.user_id
    FROM appointments
    JOIN clients ON clients.id = appointments.client_id
    WHERE appointments.id=?
    """,(appointment_id,)).fetchone()

    db.execute("""
    INSERT INTO notifications (user_id,message)
    VALUES (?,?)
    """,(appointment["user_id"],"Your appointment request was rejected."))

    db.commit()
    return redirect(url_for("lawyer_appointments"))

@app.route("/debug-cases")
def debug_cases():
    db = get_db()
    rows = db.execute("SELECT id, client_id, lawyer_id, title FROM cases").fetchall()
    return str(rows)

@app.route("/case-chat/<int:case_id>", methods=["GET", "POST"])
def case_chat(case_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]
    role = session["role"]

    # ===== GET CASE DETAILS =====
    case = db.execute("""
        SELECT c.client_id, c.lawyer_id, c.title
        FROM cases c
        WHERE c.id=?
    """, (case_id,)).fetchone()

    if not case:
        return redirect(url_for("dashboard"))

    # ===== ACCESS CONTROL =====
    allowed = False

    if role == "client":
        client = db.execute(
            "SELECT id FROM clients WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if client and client["id"] == case["client_id"]:
            allowed = True

    elif role == "lawyer":
        lawyer = db.execute(
            "SELECT id FROM lawyers WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if lawyer and lawyer["id"] == case["lawyer_id"]:
            allowed = True

    if not allowed:
        return redirect(url_for("dashboard"))

    # ===== SEND MESSAGE =====
    if request.method == "POST":
        msg = request.form.get("message", "").strip()

        if not msg:
            return redirect(url_for("case_chat", case_id=case_id))

        if len(msg) > 1000:
            return redirect(url_for("case_chat", case_id=case_id))

        db.execute("""
            INSERT INTO messages (case_id, sender_id, sender_role, message)
            VALUES (?, ?, ?, ?)
        """, (case_id, user_id, role, msg))

        db.commit()

        return redirect(url_for("case_chat", case_id=case_id))

    # ===== GET MESSAGES (LIMITED) =====
    messages = db.execute("""
        SELECT sender_role, message, timestamp
        FROM messages
        WHERE case_id=?
        ORDER BY timestamp ASC
        LIMIT 100
    """, (case_id,)).fetchall()

    return render_template(
        "case_chat.html",
        messages=messages,
        case=case
    )

@app.route("/approve-lawyers")
def approve_lawyers():
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/login/admin")

    db = get_db()

    lawyers = db.execute("""
        SELECT lawyers.id,
               lawyers.user_id,
               users.name,
               users.email,
               lawyers.specialization,
               lawyers.experience,
               lawyers.license_number,
               lawyers.verification_file,
               lawyers.approved,
               lawyers.rejection_reason
        FROM lawyers
        JOIN users ON users.id = lawyers.user_id
    """).fetchall()

    return render_template("approve_lawyers.html", lawyers=lawyers)

@app.route("/approve-lawyer/<int:lawyer_id>")
def approve_lawyer(lawyer_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect("/login/admin")

    db = get_db()
    db.execute("UPDATE lawyers SET approved = 1 WHERE id = ?", (lawyer_id,))
    db.commit()

    return redirect("/approve-lawyers")

@app.route("/reject-lawyer/<int:lawyer_id>", methods=["POST"])
def reject_lawyer(lawyer_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("dashboard"))

    reason = request.form["reason"]
    db = get_db()

    db.execute("""
        UPDATE lawyers
        SET approved = 0,
            rejection_reason = ?
        WHERE id = ?
    """, (reason, lawyer_id))

    db.commit()
    return redirect(url_for("approve_lawyers"))

@app.route("/submit-review/<int:lawyer_id>", methods=["POST"])
def submit_review(lawyer_id):

    if "user_id" not in session or session["role"] != "client":
        return redirect("/login/client")

    db = get_db()

    client = db.execute(
        "SELECT id FROM clients WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if not client:
        return "Client not found."

    # 🔒 Check if client had CLOSED case with this lawyer
    valid_case = db.execute("""
        SELECT id FROM cases
        WHERE client_id=? AND lawyer_id=? AND status='Closed'
    """, (client["id"], lawyer_id)).fetchone()

    if not valid_case:
        return "You can only review a lawyer after a completed case."

    rating = request.form["rating"]
    comment = request.form["comment"]

    # 🔒 Prevent duplicate review
    existing_review = db.execute("""
        SELECT id FROM reviews
        WHERE client_id=? AND lawyer_id=?
    """, (client["id"], lawyer_id)).fetchone()

    if existing_review:
        return "You have already reviewed this lawyer."

    db.execute("""
        INSERT INTO reviews (lawyer_id, client_id, rating, comment)
        VALUES (?, ?, ?, ?)
    """, (lawyer_id, client["id"], rating, comment))

    db.commit()

    return redirect(f"/lawyer/{lawyer_id}")

@app.route("/manage-lawyers")
def manage_lawyers():
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("role_login", role="admin"))

    db = get_db()

    lawyers = db.execute("""
        SELECT lawyers.id,
               lawyers.user_id,
               users.name,
               users.email,
               lawyers.specialization,
               lawyers.experience,
               lawyers.approved,
               users.is_active
        FROM lawyers
        JOIN users ON users.id = lawyers.user_id
    """).fetchall()

    return render_template("manage_lawyers.html", lawyers=lawyers)

@app.route("/deactivate-user/<int:user_id>")
def deactivate_user(user_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    db.commit()

    return redirect(url_for("manage_lawyers"))


@app.route("/activate-user/<int:user_id>")
def activate_user(user_id):
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("dashboard"))

    db = get_db()
    db.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
    db.commit()

    return redirect(url_for("manage_lawyers"))

@app.route("/manage-clients")
def manage_clients():
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("role_login", role="admin"))

    db = get_db()

    clients = db.execute("""
        SELECT clients.id,
               clients.user_id,
               users.name,
               users.email,
               users.is_active
        FROM clients
        JOIN users ON users.id = clients.user_id
    """).fetchall()

    return render_template("manage_clients.html", clients=clients)

@app.route("/submit-complaint", methods=["GET", "POST"])
def submit_complaint():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    if request.method == "POST":

        subject = request.form["subject"]
        message = request.form["message"]

        db.execute(
            "INSERT INTO complaints (user_id, subject, message) VALUES (?,?,?)",
            (session["user_id"], subject, message)
        )

        db.commit()

        return redirect(url_for("dashboard"))

    return render_template("submit_complaint.html")

@app.route("/admin-complaints")
def admin_complaints():

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("dashboard"))

    db = get_db()

    complaints = db.execute("""
        SELECT complaints.id,
               users.name,
               complaints.subject,
               complaints.message,
               complaints.status,
               complaints.created_at
        FROM complaints
        JOIN users ON users.id = complaints.user_id
        ORDER BY complaints.created_at DESC
    """).fetchall()

    return render_template("admin_complaints.html", complaints=complaints)

@app.route("/my-appointments")
def my_appointments():

    if "user_id" not in session or session["role"] != "client":
        return redirect(url_for("login"))

    db = get_db()

    client = db.execute(
        "SELECT id FROM clients WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    appointments = db.execute("""
        SELECT appointments.*,
               users.name AS lawyer_name,
               appointments.meeting_type,
               appointments.meeting_link,
               appointments.meeting_location
        FROM appointments
        JOIN lawyers ON lawyers.id = appointments.lawyer_id
        JOIN users ON users.id = lawyers.user_id
        WHERE appointments.client_id=?
        ORDER BY appointment_date DESC
    """, (client["id"],)).fetchall()

    return render_template(
        "client_appointments.html",
        appointments=appointments
    )

@app.route("/set-availability", methods=["GET","POST"])
def set_availability():

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    lawyer = db.execute(
        "SELECT id FROM lawyers WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "POST":

        day = request.form["day"]
        start = request.form["start"]
        end = request.form["end"]

        db.execute("""
        INSERT INTO lawyer_availability
        (lawyer_id, day_of_week, start_time, end_time)
        VALUES (?,?,?,?)
        """,(lawyer["id"],day,start,end))

        db.commit()

        return redirect(url_for("lawyer_dashboard"))

    return render_template("set_availability.html")

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    notifications = db.execute("""
    SELECT *
    FROM notifications
    WHERE user_id=?
    ORDER BY created_at DESC
    """,(session["user_id"],)).fetchall()

    # Mark all as read
    db.execute("""
    UPDATE notifications
    SET is_read=1
    WHERE user_id=?
    """,(session["user_id"],))

    db.commit()

    return render_template("notifications.html",notifications=notifications)

@app.route("/lawyer-calendar")
def lawyer_calendar():

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    lawyer = db.execute(
        "SELECT id FROM lawyers WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    appointments = db.execute("""
        SELECT id, appointment_date, appointment_time, case_title
        FROM appointments
        WHERE lawyer_id=? AND status='Approved'
    """,(lawyer["id"],)).fetchall()

    events = []

    for a in appointments:
        events.append({
            "title": a["case_title"],
            "start": a["appointment_date"] + "T" + a["appointment_time"]
        })

    return render_template("lawyer_calendar.html", events=events)

@app.route("/my-profile", methods=["GET","POST"])
def my_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    user = db.execute("""
    SELECT id,name,email,role,profile_photo
    FROM users
    WHERE id=?
    """,(session["user_id"],)).fetchone()

    # CLIENT PROFILE
    if user["role"] == "client":

        client = db.execute("""
        SELECT *
        FROM clients
        WHERE user_id=?
        """,(user["id"],)).fetchone()

        if request.method == "POST":

            name = request.form["name"]
            phone = request.form["phone"]
            address = request.form["address"]

            db.execute("UPDATE users SET name=? WHERE id=?", (name,user["id"]))

            db.execute("""
            UPDATE clients
            SET phone=?, address=?
            WHERE user_id=?
            """,(phone,address,user["id"]))

            db.commit()

            return redirect(url_for("my_profile"))

        return render_template("client_profile.html", user=user, client=client)


    # LAWYER PROFILE
    elif user["role"] == "lawyer":

        lawyer = db.execute("""
        SELECT *
        FROM lawyers
        WHERE user_id=?
        """,(user["id"],)).fetchone()

        if request.method == "POST":

            name = request.form["name"]
            specialization = request.form["specialization"]
            experience = request.form["experience"]
            fee = request.form["fee"]

            photo = request.files.get("photo")

            # update name
            db.execute(
                "UPDATE users SET name=? WHERE id=?",
                (name, user["id"])
            )

            # handle photo upload
            if photo and allowed_file(photo.filename):

                filename = secure_filename(photo.filename)

                photo.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                db.execute(
                    "UPDATE users SET profile_photo=? WHERE id=?",
                    (filename, user["id"])
                )

            # update lawyer details
            db.execute("""
            UPDATE lawyers
            SET specialization=?, experience=?, consultation_fee=?
            WHERE user_id=?
            """,(specialization, experience, fee, user["id"]))

            db.commit()

            return redirect(url_for("my_profile"))

        # ✅ GET AVAILABILITY HERE
        availability = db.execute("""
        SELECT *
        FROM lawyer_availability
        WHERE lawyer_id=?
        """,(lawyer["id"],)).fetchall()

        return render_template(
            "lawyer_profile_edit.html",
            user=user,
            lawyer=lawyer,
            availability=availability
        )
@app.route("/add-diary", methods=["GET", "POST"])
def add_diary():

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("login"))

    db = get_db()

    lawyer = db.execute(
        "SELECT id FROM lawyers WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        visibility = request.form["visibility"]

        # 1️⃣ Insert diary
        db.execute("""
        INSERT INTO case_diaries (lawyer_id, title, description, visibility)
        VALUES (?, ?, ?, ?)
        """, (lawyer["id"], title, description, visibility))

        diary_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # 2️⃣ Handle multiple file uploads
        files = request.files.getlist("files")

        for file in files:

            if file and file.filename != "":

                filename = secure_filename(file.filename)
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(path)

                # detect file type
                if filename.endswith((".png", ".jpg", ".jpeg")):
                    file_type = "image"
                elif filename.endswith((".mp4", ".mov")):
                    file_type = "video"
                elif filename.endswith((".mp3", ".wav")):
                    file_type = "audio"
                else:
                    file_type = "document"

                can_download = 1 if request.form.get("allow_download") else 0

                db.execute("""
                INSERT INTO case_media
                (diary_id, file_name, file_path, file_type, can_download)
                VALUES (?, ?, ?, ?, ?)
                """, (diary_id, filename, path, file_type, can_download))

        db.commit()

        return redirect(url_for("lawyer_dashboard"))

    return render_template("add_diary.html")

@app.route("/edit-diary/<int:diary_id>", methods=["GET", "POST"])
def edit_diary(diary_id):

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("index"))

    db = get_db()

    diary = db.execute("""
    SELECT *
    FROM case_diaries
    WHERE id=?
    """,(diary_id,)).fetchone()

    if not diary:
        return "Diary not found"

    if request.method == "POST":

        title = request.form["title"]
        description = request.form["description"]
        visibility = request.form["visibility"]

        db.execute("""
        UPDATE case_diaries
        SET title=?, description=?, visibility=?
        WHERE id=?
        """,(title, description, visibility, diary_id))

        db.commit()

        return redirect(url_for("my_diaries"))

    return render_template(
        "edit_diary.html",
        diary=diary
    )

@app.route("/delete-diary/<int:diary_id>")
def delete_diary(diary_id):

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("index"))

    db = get_db()

    # delete media first
    db.execute("""
    DELETE FROM case_media
    WHERE diary_id=?
    """,(diary_id,))

    # delete likes
    db.execute("""
    DELETE FROM diary_likes
    WHERE diary_id=?
    """,(diary_id,))

    # delete diary
    db.execute("""
    DELETE FROM case_diaries
    WHERE id=?
    """,(diary_id,))

    db.commit()

    return redirect(url_for("my_diaries"))

@app.route("/lawyer-diaries/<int:lawyer_id>")
def lawyer_diaries(lawyer_id):

    db = get_db()

    search = request.args.get("search")

    query = """
    SELECT case_diaries.*,
    (SELECT COUNT(*) FROM diary_likes WHERE diary_id=case_diaries.id) as likes
    FROM case_diaries
    WHERE lawyer_id=? AND visibility='public'
    """

    params = [lawyer_id]

    if search:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY created_at DESC"

    diaries = db.execute(query, params).fetchall()

    return render_template(
        "lawyer_diaries.html",
        diaries=diaries
    )

@app.route("/diary/<int:diary_id>")
def view_diary(diary_id):

    db = get_db()

    diary = db.execute("""
        SELECT * FROM case_diaries WHERE id=?
    """, (diary_id,)).fetchone()

    media = db.execute("""
        SELECT * FROM case_media WHERE diary_id=?
    """, (diary_id,)).fetchall()

    return render_template("view_diary.html", diary=diary, media=media)

@app.route("/like-diary/<int:diary_id>")
def like_diary(diary_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    existing = db.execute("""
    SELECT * FROM diary_likes
    WHERE diary_id=? AND user_id=?
    """,(diary_id, session["user_id"])).fetchone()

    if not existing:
        db.execute("""
        INSERT INTO diary_likes (diary_id, user_id)
        VALUES (?,?)
        """,(diary_id, session["user_id"]))
        db.commit()

    return redirect(request.referrer)

@app.route("/my-diaries")
def my_diaries():

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("index"))

    db = get_db()

    lawyer = db.execute("""
    SELECT id
    FROM lawyers
    WHERE user_id=?
    """,(session["user_id"],)).fetchone()

    diaries = db.execute("""
    SELECT case_diaries.*,

    (
        SELECT COUNT(*)
        FROM diary_likes
        WHERE diary_id=case_diaries.id
    ) as likes

    FROM case_diaries

    WHERE lawyer_id=?

    ORDER BY created_at DESC
    """,(lawyer["id"],)).fetchall()

    return render_template(
        "my_diaries.html",
        diaries=diaries
    )

@app.route("/forgot-password", methods=["GET","POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]
        db = get_db()

        user = db.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if not user:
            return render_template(
                "forgot_password.html",
                error="No account found with this email."
            )

        token = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(minutes=15)

        db.execute("""
        UPDATE users
        SET reset_token=?, reset_token_expiry=?
        WHERE id=?
        """,(token, str(expiry), user["id"]))

        db.commit()

        reset_link = f" https://framing-unified-charger.ngrok-free.dev/reset-password/{token}"

        send_email(
            email,
            "Password Reset - LegalConnect",
            f"""
            <h2>Password Reset</h2>

            <p>
            Click the button below to reset your password.
            </p>

            <a href="{reset_link}"
            style="
            background:black;
            color:white;
            padding:12px 20px;
            text-decoration:none;
            border-radius:8px;
            display:inline-block;
            ">
            Reset Password
            </a>

            <p style="margin-top:20px;">
            This link expires in 15 minutes.
            </p>
            """
        )

        return render_template(
            "forgot_password.html",
            success="Password reset link sent successfully."
        )

    return render_template("forgot_password.html")

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET","POST"])
def reset_password(token):

    db = get_db()

    user = db.execute("""
    SELECT * FROM users
    WHERE reset_token=?
    """,(token,)).fetchone()

    # ❌ Invalid token
    if not user:
        return render_template(
            "reset_password.html",
            error="Invalid reset link."
        )

    # 🔥 PASTE HERE (exactly here)
    from datetime import datetime

    if user["reset_token_expiry"]:
        expiry = datetime.fromisoformat(user["reset_token_expiry"])
        if datetime.now() > expiry:
            return render_template(
                "reset_password.html",
                error="Reset link expired."
            )

    # ✅ Continue normally
    if request.method == "POST":

        new_password = generate_password_hash(request.form["password"])

        db.execute("""
        UPDATE users
        SET password=?, reset_token=NULL, reset_token_expiry=NULL
        WHERE id=?
        """,(new_password, user["id"]))

        db.commit()

        return render_template(
            "reset_password.html",
            success="Password updated successfully."
        )

    return render_template("reset_password.html")

@app.route("/verify-otp", methods=["GET","POST"])
def verify_otp():

    if request.method == "POST":

        email = request.form["email"]
        otp = request.form["otp"]

        db = get_db()

        user = db.execute("""
        SELECT * FROM users
        WHERE email=? AND reset_otp=?
        """,(email, otp)).fetchone()

        if not user:
            return "Invalid OTP"

        # expiry check
        expiry = datetime.fromisoformat(user["otp_expiry"])
        if datetime.now() > expiry:
            return "OTP expired"

        session["reset_user"] = user["id"]

        return redirect(url_for("reset_password_secure"))

    return render_template("verify_otp.html")

@app.route("/delete-availability/<int:availability_id>")
def delete_availability(availability_id):

    if "user_id" not in session or session["role"] != "lawyer":
        return redirect(url_for("index"))

    db = get_db()

    db.execute("""
    DELETE FROM lawyer_availability
    WHERE id=?
    """,(availability_id,))

    db.commit()

    return redirect(url_for("my_profile"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")



if __name__ == "__main__":
    app.run(debug=True)