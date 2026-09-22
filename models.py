import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# USERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin','lawyer','client')) NOT NULL
)
""")

# CLIENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    phone TEXT,
    address TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

# LAWYERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS lawyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    specialization TEXT,
    experience INTEGER,
    license_no TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")

# CASES
cursor.execute("""
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    lawyer_id INTEGER,
    title TEXT,
    description TEXT,
    status TEXT CHECK(status IN ('Open','In Progress','Closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(lawyer_id) REFERENCES lawyers(id)
)
""")

# IPC SECTIONS
cursor.execute("""
CREATE TABLE IF NOT EXISTS ipc_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_code TEXT,
    section_title TEXT
)
""")

# CASE–IPC MAPPING
cursor.execute("""
CREATE TABLE IF NOT EXISTS case_ipc_mapping (
    case_id INTEGER,
    ipc_id INTEGER,
    FOREIGN KEY(case_id) REFERENCES cases(id),
    FOREIGN KEY(ipc_id) REFERENCES ipc_sections(id),
    PRIMARY KEY (case_id, ipc_id)
)
""")

# APPOINTMENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER,
    lawyer_id INTEGER,
    date TEXT,
    time TEXT,
    status TEXT CHECK(status IN ('Pending','Approved','Rejected')),
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(lawyer_id) REFERENCES lawyers(id)
)
""")

# CASE FILES
cursor.execute("""
CREATE TABLE IF NOT EXISTS case_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER,
    file_name TEXT,
    file_path TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(case_id) REFERENCES cases(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    lawyer_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    appointment_time TEXT NOT NULL,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(client_id) REFERENCES clients(id),
    FOREIGN KEY(lawyer_id) REFERENCES lawyers(id)
)
""")

cursor.execute("""
CREATE TABLE appointment_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(appointment_id) REFERENCES appointments(id)
)
""")

conn.commit()
conn.close()

print("Database and tables created successfully!")