LegalConnect

A full-stack Flask web application for lawyer discovery, appointment booking, case management, document sharing, reviews, and AI-assisted legal guidance.

Overview

LegalConnect is a role-based legal consultation platform developed as a BCA final-year project. It allows clients to connect with lawyers, book appointments, manage legal cases, communicate securely, and receive legal assistance through an AI-powered IPC recommendation feature.

## Project Structure

```text
LegalConnect/
├── app.py
├── models.py
├── update_db.py
├── check.py
├── requirements.txt
├── templates/
│   ├── admin/
│   ├── client/
│   ├── lawyer/
│   └── ...
├── uploads/
├── .gitignore
└── README.md
Features
Client
Register and log in
Search lawyers by specialization
Book appointments
Track case status
Chat with assigned lawyer
Submit reviews and complaints
Lawyer
Professional profile
Availability management
Appointment approval/rejection
Case management
File upload
IPC section mapping
Case diary with media uploads
Admin
Lawyer verification
User management
Complaint management
Dashboard analytics
Technology Stack
Python
Flask
SQLite
HTML
CSS
Bootstrap
JavaScript
Google Gemini API
Database

The project follows Third Normal Form (3NF) with separate tables for:

Users
Clients
Lawyers
Cases
Appointments
Reviews
Messages
Notifications
IPC Sections
Case Diaries
<img width="1886" height="847" alt="Screenshot 2026-09-22 211124" src="https://github.com/user-attachments/assets/ee673ff1-7d86-47ac-9bc8-49b38455c77a" />
<img width="1908" height="852" alt="Screenshot 2026-09-22 211028" src="https://github.com/user-attachments/assets/754186d7-e8d6-4164-9277-4744516c5e16" />
<img width="1913" height="876" alt="Screenshot 2026-09-22 211001" src="https://github.com/user-attachments/assets/88cc523e-089d-432f-ac9e-c2cd73cd8348" />

Installation
git clone https://github.com/jacob-joseph-tech/LegalConnect.git
cd LegalConnect
pip install -r requirements.txt
python app.py

Create a .env file with your own credentials before running the project.
