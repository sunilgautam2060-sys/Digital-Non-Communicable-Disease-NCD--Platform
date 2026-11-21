from flask import Flask, flash, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from functools import wraps
from dotenv import load_dotenv
from flask_migrate import Migrate
from extensions import db
import os


load_dotenv()

secret_key = os.environ.get("SECRET_KEY")
database_url = os.environ.get("DATABASE_URL")

if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required but not set")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is required but not set")

app = Flask(__name__)
app.secret_key = secret_key

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Import models AFTER db is initialized so SQLAlchemy and
# Flask-Migrate can register them with the app.
import models  # noqa: E402,F401

# Keep the model classes available to the existing route code while
# importing the module only after `db` has been initialized.
Patient = models.Patient
Provider = models.Provider
Appointment = models.Appointment
HealthRecord = models.HealthRecord
ConsultationNote = models.ConsultationNote
FollowUp = models.FollowUp
ProviderSettings = models.ProviderSettings
Medication = models.Medication
MedicationLog = models.MedicationLog


# =========================================================
# DEMO DATA STORAGE
# =========================================================

app.config["registered_user"] = None
app.config["registered_provider"] = None

# Patient-management storage
app.config["patients"] = {}
app.config["patient_counter"] = 1

# Provider settings storage
app.config["provider_settings"] = {
    "appointment_notifications": True,
    "patient_notifications": True,
    "followup_notifications": True,
    "system_notifications": True,
    "profile_visible": True,
    "organization_visible": True
}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def provider_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("provider_logged_in"):
            return redirect(url_for("provider_login"))
        return function(*args, **kwargs)

    return wrapper


def patient_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return function(*args, **kwargs)

    return wrapper


def normalize_text(value):
    """
    Normalize text so provider/patient matching is reliable.
    Example:
        'Dr. Ram  Sharma'
        'dr. ram sharma'
    become comparable values.
    """
    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def calculate_age(date_of_birth):
    if not date_of_birth:
        return "Not provided"

    try:
        birth_date = datetime.strptime(
            date_of_birth,
            "%Y-%m-%d"
        ).date()

        today = date.today()

        age = today.year - birth_date.year

        if (today.month, today.day) < (
            birth_date.month,
            birth_date.day
        ):
            age -= 1

        return age

    except (ValueError, TypeError):
        return "Not provided"


# =========================================================
# PROVIDER IDENTITY HELPERS
# =========================================================

def get_registered_provider():
    """
    Return the provider associated with the current session.
    """
    provider = None
    provider_id = session.get("provider_id")

    if provider_id is not None:
        provider = db.session.get(Provider, provider_id)

    if provider is None:
        provider_email = normalize_text(
            session.get("provider_email", "")
        ).lower()

        if provider_email:
            provider = Provider.query.filter_by(
                email=provider_email
            ).first()

    if provider is not None:
        return {
            "fullname": provider.fullname,
            "email": provider.email,
            "phone": provider.phone,
            "provider_type": provider.provider_type,
            "specialization": provider.specialization,
            "organization": provider.organization,
            "location": provider.location,
        }

    # Preserve compatibility with older in-memory demo data.
    return app.config.get("registered_provider") or {}


def resolve_provider_identity(provider_name="", provider_email=""):
    """
    Resolve provider name/email from the registered provider.

    Email is preferred because it is the most reliable identifier.
    Name matching is retained for compatibility with the existing
    appointment form.
    """

    registered_provider = get_registered_provider()

    registered_email = normalize_text(
        registered_provider.get("email", "")
    )

    registered_name = normalize_text(
        registered_provider.get("fullname", "")
    )

    requested_email = normalize_text(provider_email)
    requested_name = normalize_text(provider_name)

    # Best case: email matches
    if (
        requested_email
        and registered_email
        and requested_email == registered_email
    ):
        return {
            "name": registered_provider.get("fullname", ""),
            "email": registered_provider.get("email", "")
        }

    # Existing appointment form normally sends provider_name
    if (
        requested_name
        and registered_name
        and requested_name == registered_name
    ):
        return {
            "name": registered_provider.get("fullname", ""),
            "email": registered_provider.get("email", "")
        }

    # If there is only one registered provider, use that provider.
    # This makes the current demo system reliable even when the
    # frontend sends only the provider name.
    if registered_provider:
        return {
            "name": registered_provider.get("fullname", ""),
            "email": registered_provider.get("email", "")
        }

    return {
        "name": provider_name,
        "email": provider_email
    }


def appointment_belongs_to_provider(appointment):
    """
    Check whether an appointment belongs to the currently
    logged-in provider.

    Email is preferred. Name is retained as a fallback for
    existing demo records. If there is only one registered
    provider and an old appointment has no provider identity,
    the appointment is assigned to that provider.
    """

    provider_email = normalize_text(
        session.get("provider_email", "")
    )

    provider_name = normalize_text(
        session.get("provider_fullname", "")
    )

    appointment_email = normalize_text(
        appointment.get("provider_email", "")
    )

    appointment_name = normalize_text(
        appointment.get("provider_name", "")
    )

    registered_provider = get_registered_provider()

    registered_email = normalize_text(
        registered_provider.get("email", "")
    )

    registered_name = normalize_text(
        registered_provider.get("fullname", "")
    )

    # Current logged-in provider email
    if (
        provider_email
        and appointment_email
        and provider_email == appointment_email
    ):
        return True

    # Current logged-in provider name
    if (
        provider_name
        and appointment_name
        and provider_name == appointment_name
    ):
        return True

    # Registered provider email fallback
    if (
        registered_email
        and appointment_email
        and registered_email == appointment_email
    ):
        return True

    # Registered provider name fallback
    if (
        registered_name
        and appointment_name
        and registered_name == appointment_name
    ):
        return True

    # Older demo appointments may not contain provider identity.
    # If there is one registered provider, attach the appointment
    # to that provider.
    if (
        registered_provider
        and not appointment_email
        and not appointment_name
    ):
        appointment["provider_email"] = (
            registered_provider.get("email", "")
        )

        appointment["provider_name"] = (
            registered_provider.get("fullname", "")
        )

        return True

    return False


# =========================================================
# PATIENT MANAGEMENT
# =========================================================

def get_or_create_patient(appointment):
    """
    Create one patient record per patient email.

    Multiple appointments from the same patient reuse
    the same patient record.
    """

    email = normalize_text(
        appointment.get("patient_email", "")
    )

    if not email:
        return None

    patients = app.config["patients"]

    if email not in patients:

        patient_number = app.config["patient_counter"]
        app.config["patient_counter"] += 1

        patient_id = f"NCD-P{patient_number:05d}"

        patients[email] = {
            "patient_id": patient_id,
            "fullname": appointment.get("patient_name", ""),
            "email": email,
            "phone": appointment.get("patient_phone", ""),
            "date_of_birth": appointment.get(
                "patient_dob",
                ""
            ),
            "gender": appointment.get(
                "patient_gender",
                ""
            ),
            "address": appointment.get(
                "patient_address",
                ""
            ),
            "account_type": appointment.get(
                "account_type",
                ""
            ),
            "created_at": appointment.get(
                "created_at",
                ""
            )
        }

    patient = patients[email]

    # Refresh patient details from latest appointment.
    update_fields = [
        ("patient_name", "fullname"),
        ("patient_phone", "phone"),
        ("patient_dob", "date_of_birth"),
        ("patient_gender", "gender"),
        ("patient_address", "address"),
        ("account_type", "account_type")
    ]

    for source_key, patient_key in update_fields:

        value = appointment.get(source_key)

        if value:
            patient[patient_key] = value

    # Attach patient ID to appointment.
    appointment["patient_id"] = patient["patient_id"]

    return patient


# =========================================================
# PROVIDER APPOINTMENTS
# =========================================================

def appointment_to_dict(appointment):
    """Convert an appointment row to the dictionary shape used by templates."""
    patient = appointment.patient
    provider = appointment.provider
    service_fees = {
        "General Consultation": 1000,
        "Diabetes Consultation": 1000,
        "Blood Pressure Consultation": 1200,
        "Thyroid Consultation": 1200,
        "Nutrition & Lifestyle": 800,
    }
    created_at = appointment.created_at
    updated_at = appointment.updated_at
    action_at = appointment.last_action_at

    return {
        "id": appointment.id,
        "appointment_id": appointment.id,
        "patient_id": str(patient.id),
        "patient_name": patient.fullname,
        "patient_email": patient.email,
        "patient_phone": patient.phone,
        "patient_dob": patient.date_of_birth.isoformat() if patient.date_of_birth else "",
        "patient_gender": patient.gender or "",
        "patient_address": patient.address or "",
        "account_type": patient.account_type or "",
        "provider_id": provider.id,
        "provider_name": provider.fullname,
        "provider_email": provider.email,
        "provider_phone": provider.phone,
        "provider_type": provider.provider_type,
        "provider_specialization": provider.specialization or "",
        "doctor": provider.fullname,
        "specialty": provider.specialization or provider.provider_type,
        "appointment_date": appointment.appointment_date.isoformat(),
        "appointment_date_display": appointment.appointment_date.strftime("%B %d, %Y"),
        "appointment_time": appointment.appointment_time.strftime("%I:%M %p").lstrip("0"),
        "date": appointment.appointment_date.isoformat(),
        "time": appointment.appointment_time.strftime("%I:%M %p").lstrip("0"),
        "service": appointment.service or "General Consultation",
        "condition": appointment.service or "General Consultation",
        "consultation_type": appointment.consultation_type or "",
        "type": appointment.consultation_type or "",
        "fee": service_fees.get(appointment.service, 0),
        "condition_reason": appointment.condition_reason or "",
        "reason": appointment.condition_reason or "",
        "location": appointment.location or "",
        "status": appointment.status,
        "created_at": created_at.isoformat(sep=" ", timespec="seconds") if created_at else "",
        "updated_at": updated_at.isoformat(sep=" ", timespec="seconds") if updated_at else "",
        "notification": appointment.notification_message or "",
        "action_by": appointment.last_action_by or "",
        "action_at": action_at.isoformat(sep=" ", timespec="seconds") if action_at else "",
    }


def get_bookable_providers():
    return [
        {
            "id": provider.id,
            "name": provider.fullname,
            "specialty": provider.specialization or provider.provider_type,
            "email": provider.email,
        }
        for provider in Provider.query.order_by(Provider.fullname).all()
    ]


def get_patient_appointments(patient_id):
    """Return a patient's appointments, newest first."""
    if not patient_id:
        return []

    rows = Appointment.query.filter_by(
        patient_id=patient_id
    ).order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc(),
        Appointment.created_at.desc(),
    ).all()
    return [appointment_to_dict(row) for row in rows]


def get_upcoming_patient_appointment(patient_id):
    if not patient_id:
        return None
    row = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.status.in_(["Pending", "Confirmed"]),
        Appointment.appointment_date >= date.today(),
    ).order_by(
        Appointment.appointment_date.asc(),
        Appointment.appointment_time.asc(),
    ).first()
    return appointment_to_dict(row) if row else None


def get_provider_appointments():
    """
    Return appointments belonging to the logged-in provider.
    """
    provider_id = session.get("provider_id")
    if not provider_id:
        return []

    rows = Appointment.query.filter_by(
        provider_id=provider_id
    ).order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.desc(),
        Appointment.created_at.desc(),
    ).all()
    return [appointment_to_dict(row) for row in rows]


# =========================================================
# PROVIDER PATIENTS
# =========================================================

def get_provider_patients():
    """
    Build a unique patient list from this provider's appointments.
    """
    provider_appointments = get_provider_appointments()
    pending_followup_patient_ids = {
        row.patient_id
        for row in FollowUp.query.filter_by(
            provider_id=session.get("provider_id"),
            status="Pending",
        ).all()
    }
    patient_map = {}
    for appointment in provider_appointments:
        email = appointment["patient_email"]
        patient = patient_map.setdefault(email, {
            "patient_id": appointment["patient_id"],
            "fullname": appointment["patient_name"],
            "email": email,
            "phone": appointment["patient_phone"],
            "date_of_birth": appointment["patient_dob"],
            "gender": appointment["patient_gender"],
            "address": appointment["patient_address"],
            "account_type": appointment["account_type"],
            "appointments": [],
        })
        patient["appointments"].append(appointment)

    patients = list(patient_map.values())
    for patient in patients:
        history = patient["appointments"]
        history.sort(
            key=lambda item: (
                item.get("appointment_date", ""),
                item.get("appointment_time", "")
            ),
            reverse=True
        )

        patient["age"] = calculate_age(
            patient.get("date_of_birth")
        )

        patient["total_appointments"] = len(history)

        patient["last_appointment"] = (
            history[0].get("appointment_date", "")
            if history
            else ""
        )

        patient["latest_status"] = (
            history[0].get("status", "Pending")
            if history
            else "Pending"
        )

        latest = history[0] if history else {}

        patient["appointment_date"] = latest.get(
            "appointment_date",
            ""
        )

        patient["appointment_time"] = latest.get(
            "appointment_time",
            ""
        )

        patient["reason"] = latest.get(
            "reason",
            ""
        )

        patient["consultation_type"] = latest.get(
            "consultation_type",
            ""
        )

        patient["appointment_statuses"] = sorted(
            set(
                item.get("status", "Pending")
                for item in history
            )
        )

        patient["appointment_history"] = [
            {
                "id": item.get("id"),
                "appointment_date": item.get(
                    "appointment_date",
                    ""
                ),
                "appointment_time": item.get(
                    "appointment_time",
                    ""
                ),
                "condition": item.get(
                    "condition",
                    ""
                ),
                "status": item.get(
                    "status",
                    "Pending"
                ),
                "reason": item.get(
                    "reason",
                    ""
                ),
                "consultation_type": item.get(
                    "consultation_type",
                    ""
                )
            }

            for item in history
        ]

        patient["conditions"] = sorted(
            set(
                item.get("condition", "")
                for item in history
                if item.get("condition")
            )
        )

        patient["condition"] = (
            ", ".join(patient["conditions"])
            if patient["conditions"]
            else "Not specified"
        )

        patient["has_upcoming"] = any(
            item.get("status") in [
                "Pending",
                "Confirmed"
            ]
            and item.get(
                "appointment_date",
                ""
            ) >= date.today().isoformat()

            for item in history
        )

        patient["followup_required"] = int(patient["patient_id"]) in pending_followup_patient_ids

    patients.sort(
        key=lambda item: (
            item.get("fullname", "").lower()
        )
    )

    return patients


def get_provider_patient(patient_id):
    """
    Find a patient only if the patient has an appointment
    with the current provider.
    """

    for patient in get_provider_patients():
        if str(patient["patient_id"]) == str(patient_id):
            return patient

    return None


# =========================================================
# CONSULTATION NOTE HELPERS
# =========================================================

def get_provider_patient_notes(patient_id):
    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return []
    rows = ConsultationNote.query.filter_by(
        patient_id=patient_id,
        provider_id=session.get("provider_id"),
    ).order_by(ConsultationNote.created_at.desc()).all()
    return [
        {
            "id": note.id,
            "patient_id": str(note.patient_id),
            "provider_id": note.provider_id,
            "appointment_id": note.appointment_id,
            "note": note.note_text,
            "created_at": note.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": note.updated_at.strftime("%Y-%m-%d %H:%M:%S") if note.updated_at else "",
        }
        for note in rows
    ]


# =========================================================
# FOLLOW-UP HELPERS
# =========================================================

def get_provider_patient_followups(patient_id):
    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return []
    rows = FollowUp.query.filter_by(
        patient_id=patient_id,
        provider_id=session.get("provider_id"),
    ).order_by(FollowUp.follow_up_date.desc(), FollowUp.created_at.desc()).all()
    return [followup_to_dict(item) for item in rows]


def followup_to_dict(item):
    patient = db.session.get(Patient, item.patient_id)
    return {
        "id": item.id,
        "patient_id": str(item.patient_id),
        "patient_name": patient.fullname if patient else "Patient",
        "patient_email": patient.email if patient else "",
        "provider_id": item.provider_id,
        "appointment_id": item.appointment_id,
        "followup_date": item.follow_up_date.isoformat(),
        "followup_time": item.follow_up_time.strftime("%I:%M %p").lstrip("0") if item.follow_up_time else "",
        "followup_type": item.follow_up_type or "",
        "instructions": item.notes or "",
        "status": item.status,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": item.completed_at.strftime("%Y-%m-%d %H:%M:%S") if item.completed_at else "",
    }


# =========================================================
# PATIENT NOTIFICATIONS
# =========================================================

def build_patient_notifications(patient_email):
    """
    Build patient notifications directly from appointment data.

    This means the notification status always comes from
    the same appointment record that the provider changes.
    """

    patient_email = normalize_text(patient_email)

    patient = Patient.query.filter_by(email=patient_email).first()
    patient_appointments = get_patient_appointments(
        patient.id if patient else None
    )

    notifications = []

    for appointment in patient_appointments:

        status = appointment.get(
            "status",
            "Pending"
        )

        notification_message = appointment.get(
            "notification",
            ""
        )

        if not notification_message:

            provider_name = appointment.get(
                "provider_name",
                "your selected provider"
            )

            notification_message = (
                f"Your appointment with "
                f"{provider_name} is "
                f"{status.lower()}."
            )

        notifications.append({
            "id": f"appointment-{appointment.get('id')}",
            "type": "appointment",
            "category": "appointment",
            "icon": "📅",
            "title": f"Appointment {status}",
            "message": notification_message,
            "date": appointment.get(
                "appointment_date",
                ""
            ),
            "time": appointment.get(
                "appointment_time",
                ""
            ),
            "status": status,
            "appointment_id": appointment.get(
                "id"
            ),
            "provider_name": appointment.get(
                "provider_name",
                ""
            ),
            "service": appointment.get(
                "condition",
                ""
            ),
            "created_at": appointment.get(
                "updated_at",
                appointment.get(
                    "created_at",
                    ""
                )
            )
        })

    notifications.sort(
        key=lambda item: (
            item.get("created_at", "")
        ),
        reverse=True
    )

    return notifications


# =========================================================
# PROVIDER NOTIFICATIONS
# =========================================================

def build_provider_notifications():
    """
    Build provider notifications from pending appointment requests
    and appointment status updates.
    """

    provider_appointments = get_provider_appointments()

    notifications = []

    for appointment in provider_appointments:

        status = appointment.get(
            "status",
            "Pending"
        )

        if status == "Pending":

            notifications.append({
                "id": (
                    f"provider-appointment-"
                    f"{appointment.get('id')}"
                ),
                "type": "appointment",
                "category": "appointment",
                "icon": "📅",
                "title": "New Appointment Request",
                "message": (
                    f"{appointment.get('patient_name', 'Patient')} "
                    f"requested a "
                    f"{appointment.get('condition', 'health')} "
                    f"consultation for "
                    f"{appointment.get('appointment_date', '')} "
                    f"at "
                    f"{appointment.get('appointment_time', '')}."
                ),
                "date": appointment.get(
                    "appointment_date",
                    ""
                ),
                "time": appointment.get(
                    "appointment_time",
                    ""
                ),
                "status": status,
                "appointment_id": appointment.get(
                    "id"
                ),
                "patient_name": appointment.get(
                    "patient_name",
                    ""
                ),
                "created_at": appointment.get(
                    "created_at",
                    ""
                )
            })

        else:

            notifications.append({
                "id": (
                    f"provider-status-"
                    f"{appointment.get('id')}-"
                    f"{status.lower()}"
                ),
                "type": "appointment",
                "category": "appointment",
                "icon": "🔔",
                "title": f"Appointment {status}",
                "message": (
                    f"Appointment with "
                    f"{appointment.get('patient_name', 'Patient')} "
                    f"is currently {status.lower()}."
                ),
                "date": appointment.get(
                    "appointment_date",
                    ""
                ),
                "time": appointment.get(
                    "appointment_time",
                    ""
                ),
                "status": status,
                "appointment_id": appointment.get(
                    "id"
                ),
                "patient_name": appointment.get(
                    "patient_name",
                    ""
                ),
                "created_at": appointment.get(
                    "updated_at",
                    appointment.get(
                        "created_at",
                        ""
                    )
                )
            })

    notifications.sort(
        key=lambda item: (
            item.get("created_at", "")
        ),
        reverse=True
    )

    return notifications


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# PATIENT REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form.get(
            "fullname",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        date_of_birth = request.form.get(
            "date_of_birth",
            ""
        ).strip()

        gender = request.form.get(
            "gender",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        account_type = request.form.get(
            "account_type",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not all([
            fullname,
            email,
            phone,
            date_of_birth,
            gender,
            address,
            account_type,
            password
        ]):
            return render_template(
                "register.html",
                error=(
                    "Please fill in all required fields."
                )
            )

        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        if len(password) < 8:

            return render_template(
                "register.html",
                error=(
                    "Password must contain at least 8 characters."
                )
            )

        # Reject duplicate emails before writing.
        existing_patient = (
            Patient.query.filter_by(
                email=email
            ).first()
        )

        if existing_patient:

            return render_template(
                "register.html",
                error=(
                    "An account with this email "
                    "already exists."
                )
            )

        # Convert the form date string to a real date.
        dob_value = None

        if date_of_birth:

            try:

                dob_value = datetime.strptime(
                    date_of_birth,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                dob_value = None

        try:

            patient = Patient(
                fullname=fullname,
                email=email,
                phone=phone,
                date_of_birth=dob_value,
                gender=gender or None,
                address=address or None,
                account_type=account_type or None,
                password_hash=generate_password_hash(
                    password
                ),
            )

            db.session.add(patient)
            db.session.commit()

        except Exception:

            db.session.rollback()

            return render_template(
                "register.html",
                error=(
                    "Registration failed. "
                    "Please try again."
                )
            )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# PATIENT LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        patient = Patient.query.filter_by(
            email=email
        ).first()

        if not patient or not check_password_hash(
            patient.password_hash,
            password
        ):

            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        session.clear()

        session["logged_in"] = True

        session["email"] = patient.email

        session["fullname"] = patient.fullname

        session["phone"] = patient.phone

        session["date_of_birth"] = (
            patient.date_of_birth.isoformat()
            if patient.date_of_birth
            else ""
        )

        session["gender"] = patient.gender or ""

        session["address"] = patient.address or ""

        session["account_type"] = patient.account_type or ""

        session["patient_id"] = patient.id

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# PATIENT DASHBOARD
# =========================================================

@app.route("/dashboard")
@patient_required
def dashboard():

    return render_template(
        "dashboard.html",
        fullname=session.get(
            "fullname",
            "User"
        )
    )


# =========================================================
# MONITORING
# =========================================================

@app.route("/monitoring")
@patient_required
def monitoring():
    records = HealthRecord.query.filter_by(
        patient_id=session.get("patient_id"),
    ).order_by(
        HealthRecord.date_recorded.desc(),
        HealthRecord.created_at.desc(),
    ).all()
    records_by_type = {}
    for record in records:
        records_by_type.setdefault(record.record_type, []).append(record)
    weights = records_by_type.get("Weight", [])
    patient_id = session.get("patient_id")
    medications = Medication.query.filter_by(
        patient_id=patient_id,
        is_active=True,
    ).order_by(Medication.name.asc()).all()
    taken_today = {
        log.medication_id
        for log in MedicationLog.query.join(Medication).filter(
            Medication.patient_id == patient_id,
            MedicationLog.intake_date == date.today(),
        ).all()
    }

    return render_template(
        "monitoring.html",
        records=records,
        current_weight=weights[0] if weights else None,
        previous_weight=weights[1] if len(weights) > 1 else None,
        latest_bp=(records_by_type.get("Blood Pressure") or [None])[0],
        latest_glucose=(records_by_type.get("Blood Glucose") or [None])[0],
        latest_tsh=(records_by_type.get("Thyroid TSH") or [None])[0],
        medications=medications,
        medication_taken_ids=taken_today,
    )


@app.route("/monitoring/weight", methods=["POST"])
@patient_required
def save_weight():
    payload = request.get_json(silent=True) or {}
    try:
        weight = float(payload.get("value", ""))
    except (TypeError, ValueError):
        return jsonify(error="Enter a valid weight."), 400
    if not 1 <= weight <= 1000:
        return jsonify(error="Weight must be between 1 and 1000 kg."), 400

    record = HealthRecord(
        patient_id=session.get("patient_id"),
        record_type="Weight",
        value=f"{weight:.1f}",
        date_recorded=date.today(),
    )
    db.session.add(record)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save patient weight")
        return jsonify(error="Weight could not be saved. Please try again."), 500
    return jsonify(message="Weight saved."), 201


@app.route("/monitoring/record", methods=["POST"])
@patient_required
def save_health_record():
    payload = request.get_json(silent=True) or request.form
    record_type = str(payload.get("type", "")).strip()
    value = str(payload.get("value", "")).strip()
    date_text = str(payload.get("date", "")).strip()
    allowed_types = {"Blood Pressure", "Blood Glucose", "Thyroid TSH"}
    if record_type not in allowed_types:
        return jsonify(error="Choose a supported measurement type."), 400
    try:
        record_date = date.fromisoformat(date_text)
    except ValueError:
        return jsonify(error="Enter a valid measurement date."), 400
    if record_date > date.today():
        return jsonify(error="Measurement date cannot be in the future."), 400

    if record_type == "Blood Pressure":
        parts = value.split("/")
        if len(parts) != 2 or any(not part.isdigit() or len(part) > 3 for part in parts):
            return jsonify(error="Enter blood pressure as systolic/diastolic, for example 120/80."), 400
    else:
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return jsonify(error="Enter a valid numeric reading."), 400
        if not 0 < numeric_value <= 100000:
            return jsonify(error="Enter a positive reading."), 400

    record = HealthRecord(
        patient_id=session.get("patient_id"),
        record_type=record_type,
        value=value,
        date_recorded=record_date,
    )
    db.session.add(record)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save patient health measurement")
        return jsonify(error="Reading could not be saved. Please try again."), 500
    return jsonify(message="Reading saved."), 201


@app.route("/monitoring/medications", methods=["POST"])
@patient_required
def add_medication():
    payload = request.get_json(silent=True) or request.form
    name = str(payload.get("name", "")).strip()
    dose = str(payload.get("dose", "")).strip()
    instructions = str(payload.get("instructions", "")).strip()
    if not name or len(name) > 120:
        return jsonify(error="Enter a medication name up to 120 characters."), 400
    if not dose or len(dose) > 80:
        return jsonify(error="Enter the dose or label up to 80 characters."), 400
    if len(instructions) > 1000:
        return jsonify(error="Instructions must be 1000 characters or fewer."), 400

    medication = Medication(
        patient_id=session.get("patient_id"),
        name=name,
        dose=dose,
        instructions=instructions or None,
    )
    db.session.add(medication)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save patient medication")
        return jsonify(error="Medication could not be saved. Please try again."), 500
    return jsonify(message="Medication saved."), 201


@app.route("/monitoring/medications/<int:medication_id>/taken", methods=["POST"])
@patient_required
def mark_medication_taken(medication_id):
    medication = Medication.query.filter_by(
        id=medication_id,
        patient_id=session.get("patient_id"),
        is_active=True,
    ).first()
    if not medication:
        return jsonify(error="Medication was not found."), 404

    log = MedicationLog.query.filter_by(
        medication_id=medication.id,
        intake_date=date.today(),
    ).first()
    if log:
        return jsonify(message="Today's dose is already recorded.")

    db.session.add(MedicationLog(
        medication_id=medication.id,
        intake_date=date.today(),
    ))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # A concurrent request may have created today's unique log first.
        existing = MedicationLog.query.filter_by(
            medication_id=medication.id,
            intake_date=date.today(),
        ).first()
        if existing:
            return jsonify(message="Today's dose is already recorded.")
        app.logger.exception("Could not save medication intake")
        return jsonify(error="Medication intake could not be saved."), 500
    return jsonify(message="Today's dose recorded.")


# =========================================================
# PREVENTION
# =========================================================

@app.route("/prevention")
@patient_required
def prevention():

    return render_template(
        "prevention.html"
    )


# =========================================================
# COMMUNITY
# =========================================================

@app.route("/community")
@patient_required
def community():

    return render_template(
        "community.html"
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
@patient_required
def profile():

    return render_template(
        "profile.html",
        fullname=session.get(
            "fullname",
            ""
        ),
        email=session.get(
            "email",
            ""
        ),
        phone=session.get(
            "phone",
            ""
        ),
        date_of_birth=session.get(
            "date_of_birth",
            ""
        ),
        gender=session.get(
            "gender",
            ""
        ),
        address=session.get(
            "address",
            ""
        ),
        account_type=session.get(
            "account_type",
            ""
        )
    )


# =========================================================
# RECORDS
# =========================================================

@app.route("/records")
@patient_required
def records():
    health_records = HealthRecord.query.filter_by(
        patient_id=session.get("patient_id")
    ).order_by(
        HealthRecord.date_recorded.desc(),
        HealthRecord.created_at.desc(),
    ).all()

    return render_template(
        "records.html",
        records=health_records,
    )


@app.route("/records/<int:record_id>/delete", methods=["POST"])
@patient_required
def delete_health_record(record_id):
    record = HealthRecord.query.filter_by(
        id=record_id,
        patient_id=session.get("patient_id"),
    ).first()
    if not record:
        return "Health record not found.", 404

    try:
        db.session.delete(record)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not delete patient health record")
        flash("The health record could not be deleted. Please try again.", "error")
        return redirect(url_for("records"))

    flash("Health record deleted.", "success")
    return redirect(url_for("records"))


# =========================================================
# APPOINTMENTS
# =========================================================

@app.route("/appointments", methods=["GET", "POST"])
@patient_required
def appointments():
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        wants_json = request.is_json

        def booking_error(message, status=400):
            if wants_json:
                return jsonify(success=False, error=message), status
            return render_template(
                "appointments.html",
                appointments=get_patient_appointments(session.get("patient_id")),
                upcoming_appointment=get_upcoming_patient_appointment(session.get("patient_id")),
                bookable_providers=get_bookable_providers(),
                error=message,
            ), status

        patient = db.session.get(Patient, session.get("patient_id"))
        try:
            provider_id = int(payload.get("provider_id", ""))
        except (TypeError, ValueError):
            provider_id = None
        provider = db.session.get(Provider, provider_id) if provider_id else None

        date_text = str(payload.get("appointment_date", "")).strip()
        time_text = str(payload.get("appointment_time", "")).strip()
        service = str(payload.get("service", "")).strip()
        consultation_type = str(payload.get("consultation_type", "")).strip()
        location = str(payload.get("location", "")).strip()
        reason = str(payload.get("reason", "")).strip()

        if not patient:
            return booking_error("Your patient account could not be found. Please log in again.", 401)
        if not provider:
            return booking_error("Please select a registered service provider.")
        if not all([date_text, time_text, service, consultation_type, reason]):
            return booking_error("Please complete all required appointment fields.")

        try:
            appointment_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            try:
                appointment_time = datetime.strptime(time_text, "%I:%M %p").time()
            except ValueError:
                appointment_time = datetime.strptime(time_text, "%H:%M").time()
        except ValueError:
            return booking_error("Please enter a valid appointment date and time.")

        if appointment_date < date.today():
            return booking_error("Appointment date cannot be in the past.")

        availability_error = validate_appointment_slot(
            provider.id,
            appointment_date,
            appointment_time,
        )
        if availability_error:
            return booking_error(availability_error, 409 if "conflicts" in availability_error else 400)

        try:
            appointment = Appointment(
                patient_id=patient.id,
                provider_id=provider.id,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                service=service,
                consultation_type=consultation_type,
                location=location or None,
                condition_reason=reason,
                status="Pending",
                notification_message="Your appointment request is pending provider confirmation.",
                last_action_by="patient",
                last_action_at=datetime.utcnow(),
            )
            db.session.add(appointment)
            db.session.commit()
        except Exception:
            db.session.rollback()
            return booking_error("The appointment could not be saved. Please try again.", 500)

        if wants_json:
            return jsonify(
                success=True,
                message="Appointment request submitted.",
                appointment=appointment_to_dict(appointment),
            ), 201
        return redirect(url_for("appointments"))

    patient_appointments = get_patient_appointments(session.get("patient_id"))
    upcoming_appointment = get_upcoming_patient_appointment(session.get("patient_id"))
    bookable_providers = get_bookable_providers()
    return render_template(
        "appointments.html",
        appointments=patient_appointments,
        upcoming_appointment=upcoming_appointment,
        bookable_providers=bookable_providers,
    )


@app.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@patient_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=session.get("patient_id"),
    ).first()
    if not appointment:
        return jsonify(success=False, error="Appointment not found."), 404
    if appointment.status in {"Cancelled", "Completed"}:
        return jsonify(success=False, error="This appointment can no longer be cancelled."), 400

    appointment.status = "Cancelled"
    appointment.last_action_by = "patient"
    appointment.last_action_at = datetime.utcnow()
    appointment.notification_message = "The patient cancelled this appointment."
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error="The appointment could not be cancelled."), 500
    return jsonify(success=True)


@app.route("/appointments/<int:appointment_id>/reschedule", methods=["POST"])
@patient_required
def reschedule_appointment(appointment_id):
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=session.get("patient_id"),
    ).first()
    if not appointment:
        return jsonify(success=False, error="Appointment not found."), 404
    if appointment.status in {"Cancelled", "Completed"}:
        return jsonify(success=False, error="This appointment can no longer be rescheduled."), 400

    payload = request.get_json(silent=True) or request.form
    date_text = str(payload.get("appointment_date", "")).strip()
    time_text = str(payload.get("appointment_time", "")).strip()
    try:
        new_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        try:
            new_time = datetime.strptime(time_text, "%I:%M %p").time()
        except ValueError:
            new_time = datetime.strptime(time_text, "%H:%M").time()
    except ValueError:
        return jsonify(success=False, error="Please enter a valid new date and time."), 400
    if new_date < date.today():
        return jsonify(success=False, error="Appointment date cannot be in the past."), 400

    availability_error = validate_appointment_slot(
        appointment.provider_id,
        new_date,
        new_time,
        exclude_id=appointment.id,
    )
    if availability_error:
        return jsonify(success=False, error=availability_error), 409 if "conflicts" in availability_error else 400

    appointment.appointment_date = new_date
    appointment.appointment_time = new_time
    appointment.status = "Pending"
    appointment.last_action_by = "patient"
    appointment.last_action_at = datetime.utcnow()
    appointment.notification_message = "The patient requested a new appointment time."
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error="The appointment could not be rescheduled."), 500
    return jsonify(success=True)


# =========================================================
# PATIENT NOTIFICATIONS
# =========================================================

@app.route("/notifications")
@patient_required
def notifications():
    patient = db.session.get(Patient, session.get("patient_id"))
    preferences = patient.notification_preferences if patient else None
    if preferences is None or preferences.get("appointmentAlerts", True):
        notifications = build_patient_notifications(
            patient.email if patient else session.get("email", "")
        )
    else:
        notifications = []

    return render_template(
        "notifications.html",
        notifications=notifications
    )


# =========================================================
# PATIENT SETTINGS
# =========================================================

@app.route("/settings", methods=["GET", "POST"])
@patient_required
def settings():

    default_notification_preferences = {
        "healthReminders": True,
        "appointmentAlerts": True,
        "healthInformation": True,
    }

    if request.method == "POST":

        fullname = request.form.get(
            "fullname",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        patient_id = session.get("patient_id")

        patient = Patient.query.get(
            patient_id
        ) if patient_id else None

        if not patient:

            return render_template(
                "settings.html",
                notification_preferences=default_notification_preferences,
                settings_error=(
                    "Patient account was not found."
                )
            ), 404

        if fullname:
            patient.fullname = fullname

        if phone:
            patient.phone = phone

        if address:
            patient.address = address

        try:

            db.session.commit()

        except Exception:

            db.session.rollback()

            return render_template(
                "settings.html",
                notification_preferences=(
                    patient.notification_preferences
                    or default_notification_preferences
                ),
                settings_error=(
                    "Settings could not be saved."
                )
            ), 500

        session["fullname"] = patient.fullname

        session["phone"] = patient.phone

        session["address"] = patient.address or ""

        return render_template(
            "settings.html",
            notification_preferences=(
                patient.notification_preferences
                or default_notification_preferences
            ),
            settings_success=(
                "Settings saved successfully."
            )
        )

    patient = db.session.get(Patient, session.get("patient_id"))
    if not patient:
        return render_template(
            "settings.html",
            notification_preferences=default_notification_preferences,
            settings_error="Patient account was not found.",
        ), 404

    return render_template(
        "settings.html",
        notification_preferences=(
            patient.notification_preferences or default_notification_preferences
        ),
    )


@app.route("/settings/notification-preferences", methods=["POST"])
@patient_required
def save_notification_preferences():
    payload = request.get_json(silent=True)
    preference_names = (
        "healthReminders",
        "appointmentAlerts",
        "healthInformation",
    )
    if not isinstance(payload, dict) or any(
        type(payload.get(name)) is not bool for name in preference_names
    ):
        return jsonify(error="Choose valid notification preferences."), 400

    patient = db.session.get(Patient, session.get("patient_id"))
    if not patient:
        return jsonify(error="Patient account was not found."), 404

    patient.notification_preferences = {
        name: payload[name] for name in preference_names
    }
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save patient notification preferences")
        return jsonify(error="Notification preferences could not be saved."), 500

    return jsonify(message="Notification preferences saved.")


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route("/change-password", methods=["GET", "POST"])
@app.route("/settings/change-password", methods=["POST"])
@patient_required
def change_password():
    if request.method == "GET":
        return render_template("change-password.html")

    is_json = request.is_json
    payload = request.get_json(silent=True) or {} if is_json else request.form

    def respond(message, status=200, success=False):
        if is_json:
            return jsonify(message=message), status
        return render_template(
            "change-password.html",
            error=None if success else message,
            success=message if success else None,
        ), status

    current_password = payload.get("current_password", "")
    new_password = payload.get("new_password", "")
    confirm_password = payload.get("confirm_password", "")
    patient_id = session.get("patient_id")
    patient = db.session.get(Patient, patient_id) if patient_id else None

    if not patient:
        return respond("User account was not found.", 404)
    if not check_password_hash(patient.password_hash, current_password):
        return respond("Current password is incorrect.", 400)
    if not new_password:
        return respond("Please enter a new password.", 400)
    if len(new_password) < 8:
        return respond("New password must contain at least 8 characters.", 400)
    if confirm_password and new_password != confirm_password:
        return respond("New password and confirmation do not match.", 400)
    if new_password == current_password:
        return respond("New password must be different from your current password.", 400)

    try:
        patient.password_hash = generate_password_hash(new_password)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not update patient password")
        return respond("Password could not be updated.", 500)
    return respond("Password updated successfully.", success=True)


# =========================================================
# PROVIDER REGISTER
# =========================================================

@app.route(
    "/provider-register",
    methods=["GET", "POST"]
)
def provider_register():

    if request.method == "POST":

        # The provider form sends first_name and last_name as
        # separate fields. Combine them for the model's fullname.
        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        last_name = request.form.get(
            "last_name",
            ""
        ).strip()

        fullname = " ".join(
            part for part in [first_name, last_name] if part
        )

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        provider_type = request.form.get(
            "provider_type",
            ""
        ).strip()

        specialization = request.form.get(
            "specialization",
            ""
        ).strip()

        organization = request.form.get(
            "organization",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not all([
            fullname,
            email,
            phone,
            provider_type,
            specialization,
            organization,
            location,
            password
        ]):

            return render_template(
                "provider_register.html",
                error=(
                    "Please fill in all required fields."
                )
            )

        if password != confirm_password:

            return render_template(
                "provider_register.html",
                error="Passwords do not match."
            )

        if len(password) < 8:

            return render_template(
                "provider_register.html",
                error=(
                    "Password must contain at least 8 characters."
                )
            )

        # Reject duplicate provider emails before writing.
        existing_provider = Provider.query.filter_by(
            email=email
        ).first()

        if existing_provider:

            return render_template(
                "provider_register.html",
                error=(
                    "A provider account with this "
                    "email already exists."
                )
            )

        try:

            provider = Provider(
                fullname=fullname,
                email=email,
                phone=phone,
                provider_type=provider_type,
                specialization=specialization or None,
                organization=organization or None,
                location=location or None,
                password_hash=generate_password_hash(
                    password
                ),
            )

            db.session.add(provider)
            db.session.commit()

        except Exception:

            db.session.rollback()

            return render_template(
                "provider_register.html",
                error=(
                    "Registration failed. "
                    "Please try again."
                )
            )

        return redirect(
            url_for("provider_login")
        )

    return render_template(
        "provider_register.html"
    )


# =========================================================
# PROVIDER LOGIN
# =========================================================

@app.route(
    "/provider-login",
    methods=["GET", "POST"]
)
def provider_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        provider = Provider.query.filter_by(
            email=email
        ).first()

        if not provider or not check_password_hash(
            provider.password_hash,
            password
        ):

            return render_template(
                "provider_login.html",
                error="Invalid email or password."
            )

        session.clear()

        session["provider_logged_in"] = True

        session["provider_id"] = provider.id

        session["provider_fullname"] = (
            provider.fullname
        )

        session["provider_email"] = (
            provider.email
        )

        session["provider_phone"] = (
            provider.phone
        )

        session["provider_type"] = (
            provider.provider_type
        )

        session["provider_specialization"] = (
            provider.specialization or ""
        )

        session["provider_organization"] = (
            provider.organization or ""
        )

        session["provider_location"] = (
            provider.location or ""
        )

        session["provider_id"] = provider.id

        return redirect(
            url_for("service_provider")
        )

    return render_template(
        "provider_login.html"
    )


# =========================================================
# SERVICE PROVIDER DASHBOARD
# =========================================================

@app.route("/service-provider")
@provider_required
def service_provider():

    appointments = get_provider_appointments()

    total_appointments = len(
        appointments
    )

    pending_appointments = sum(
        1

        for item in appointments

        if item.get("status")
        == "Pending"
    )

    confirmed_appointments = sum(
        1

        for item in appointments

        if item.get("status")
        == "Confirmed"
    )

    completed_appointments = sum(
        1

        for item in appointments

        if item.get("status")
        == "Completed"
    )

    patients = get_provider_patients()
    today_appointments = [
        item for item in appointments
        if item.get("appointment_date") == date.today().isoformat()
    ]
    followups_due = FollowUp.query.filter_by(
        provider_id=session.get("provider_id"),
        status="Pending",
    ).filter(
        FollowUp.follow_up_date <= date.today()
    ).count()

    return render_template(
        "service_provider.html",

        fullname=session.get(
            "provider_fullname",
            "Provider"
        ),

        provider_type=session.get(
            "provider_type",
            "Healthcare Provider"
        ),

        total_appointments=(
            total_appointments
        ),

        pending_appointments=(
            pending_appointments
        ),

        confirmed_appointments=(
            confirmed_appointments
        ),

        completed_appointments=(
            completed_appointments
        ),

        total_patients=len(
            patients
        ),

        today_appointments=today_appointments,

        followups_due=followups_due,

        appointments=appointments,

        patients=patients
    )


# =========================================================
# PROVIDER APPOINTMENTS
# =========================================================

@app.route("/provider-appointments")
@provider_required
def provider_appointments():

    appointments = get_provider_appointments()

    pending_count = sum(
        1

        for item in appointments

        if item.get("status")
        == "Pending"
    )

    confirmed_count = sum(
        1

        for item in appointments

        if item.get("status")
        == "Confirmed"
    )

    completed_count = sum(
        1

        for item in appointments

        if item.get("status")
        == "Completed"
    )

    cancelled_count = sum(
        1

        for item in appointments

        if item.get("status")
        in [
            "Cancelled",
            "Rejected"
        ]
    )

    return render_template(
        "provider_appointments.html",

        appointments=appointments,
        appointment_list=appointments,

        pending_count=pending_count,

        confirmed_count=confirmed_count,

        completed_count=completed_count,

        cancelled_count=cancelled_count,

        provider_name=session.get(
            "provider_fullname",
            "Service Provider"
        )
    )


# =========================================================
# APPOINTMENT ACTION
# =========================================================

@app.route(
    "/provider-appointments/<int:appointment_id>/<action>",
    methods=["POST"]
)
@provider_required
def appointment_action(appointment_id, action):
    transitions = {
        "confirm": ("Pending", "Confirmed"),
        "reject": ("Pending", "Rejected"),
        "cancel": ("Confirmed", "Cancelled"),
        "complete": ("Confirmed", "Completed"),
    }
    transition = transitions.get(action)
    if not transition:
        return redirect(url_for("provider_appointments"))

    provider_id = session.get("provider_id")
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        provider_id=provider_id,
    ).first()
    if not appointment or appointment.status != transition[0]:
        return redirect(url_for("provider_appointments"))

    new_status = transition[1]
    appointment.status = new_status
    # This column stores the acting role (String(20)), not the provider email.
    appointment.last_action_by = "provider"
    appointment.last_action_at = datetime.utcnow()
    provider_name = appointment.provider.fullname
    if new_status == "Confirmed":
        appointment.notification_message = f"Your appointment with {provider_name} has been confirmed."
    elif new_status == "Rejected":
        appointment.notification_message = f"Your appointment request with {provider_name} has been rejected."
    elif new_status == "Cancelled":
        appointment.notification_message = f"Your appointment with {provider_name} has been cancelled."
    else:
        appointment.notification_message = f"Your appointment with {provider_name} has been completed."

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    return redirect(url_for("provider_appointments"))


# PATIENT DETAILS
# =========================================================

@app.route("/patients")
@provider_required
def patients():
    return render_template(
        "patients.html",
        patients=get_provider_patients(),
    )


@app.route(
    "/patients/<patient_id>"
)
@provider_required
def patient_details(
    patient_id
):

    patient = get_provider_patient(
        patient_id
    )

    if not patient:
        return redirect(url_for("patients"))

    notes = get_provider_patient_notes(
        patient_id
    )

    followups = get_provider_patient_followups(
        patient_id
    )

    return render_template(
        "patients_details.html",
        patient=patient,
        notes=notes,
        followups=followups
    )


# =========================================================
# ADD CONSULTATION NOTE
# =========================================================

@app.route(
    "/patients/<patient_id>/add-note",
    methods=["POST"]
)
@provider_required
def add_consultation_note(
    patient_id
):

    patient = get_provider_patient(
        patient_id
    )

    if not patient:

        return redirect(
            url_for(
                "patients"
            )
        )

    note_text = request.form.get("note", "").strip()
    if not note_text:
        return redirect(url_for("patient_details", patient_id=patient_id))

    appointment_id = request.form.get("appointment_id", "").strip()
    appointment = None
    if appointment_id:
        try:
            appointment = Appointment.query.filter_by(
                id=int(appointment_id),
                patient_id=int(patient_id),
                provider_id=session.get("provider_id"),
            ).first()
        except (TypeError, ValueError):
            appointment = None
        if not appointment:
            return redirect(url_for("patient_details", patient_id=patient_id))

    note = ConsultationNote(
        patient_id=int(patient_id),
        provider_id=session.get("provider_id"),
        appointment_id=appointment.id if appointment else None,
        note_text=note_text,
    )
    db.session.add(note)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save provider consultation note")

    return redirect(
        url_for(
            "patient_details",
            patient_id=patient_id
        )
    )


# =========================================================
# EDIT CONSULTATION NOTE
# =========================================================

@app.route(
    "/patients/<patient_id>/edit-note/<int:note_id>",
    methods=["POST"]
)
@provider_required
def edit_consultation_note(
    patient_id,
    note_id
):

    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return redirect(url_for("patients"))
    note = ConsultationNote.query.filter_by(
        id=note_id,
        patient_id=patient_id,
        provider_id=session.get("provider_id"),
    ).first()
    note_text = request.form.get("note", "").strip()
    if note and note_text:
        note.note_text = note_text
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not update provider consultation note")

    return redirect(
        url_for(
            "patient_details",
            patient_id=patient_id
        )
    )


# =========================================================
# DELETE CONSULTATION NOTE
# =========================================================

@app.route(
    "/patients/<patient_id>/delete-note/<int:note_id>",
    methods=["POST"]
)
@provider_required
def delete_consultation_note(
    patient_id,
    note_id
):

    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return redirect(url_for("patients"))
    note = ConsultationNote.query.filter_by(
        id=note_id,
        patient_id=patient_id,
        provider_id=session.get("provider_id"),
    ).first()
    if note:
        db.session.delete(note)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not delete provider consultation note")

    return redirect(
        url_for(
            "patient_details",
            patient_id=patient_id
        )
    )


# =========================================================
# ADD FOLLOW-UP
# =========================================================

@app.route(
    "/patients/<patient_id>/add-followup",
    methods=["POST"]
)
@provider_required
def add_followup(
    patient_id
):

    patient = get_provider_patient(
        patient_id
    )

    if not patient:

        return redirect(
            url_for(
                "patients"
            )
        )

    try:
        patient_id_value = int(patient_id)
        followup_date = date.fromisoformat(request.form.get("followup_date", "").strip())
    except (TypeError, ValueError):
        return redirect(url_for("patient_details", patient_id=patient_id))

    followup_time_text = request.form.get("followup_time", "").strip()
    followup_time = None
    if followup_time_text:
        try:
            followup_time = datetime.strptime(followup_time_text, "%H:%M").time()
        except ValueError:
            return redirect(url_for("patient_details", patient_id=patient_id))

    appointment_id_text = request.form.get("appointment_id", "").strip()
    appointment = None
    if appointment_id_text:
        try:
            appointment = Appointment.query.filter_by(
                id=int(appointment_id_text),
                patient_id=patient_id_value,
                provider_id=session.get("provider_id"),
            ).first()
        except (TypeError, ValueError):
            appointment = None
        if not appointment:
            return redirect(url_for("patient_details", patient_id=patient_id))

    instructions = request.form.get(
        "instructions",
        request.form.get("notes", ""),
    ).strip()
    if len(instructions) < 2:
        return redirect(url_for("patient_details", patient_id=patient_id))

    followup = FollowUp(
        patient_id=patient_id_value,
        provider_id=session.get("provider_id"),
        appointment_id=appointment.id if appointment else None,
        follow_up_date=followup_date,
        follow_up_time=followup_time,
        follow_up_type=request.form.get("followup_type", "").strip() or "General follow-up",
        notes=instructions,
        status="Pending",
    )
    db.session.add(followup)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Could not save provider follow-up")

    return redirect(
        url_for(
            "patient_details",
            patient_id=patient_id
        )
    )


# =========================================================
# MARK FOLLOW-UP COMPLETED
# =========================================================

@app.route(
    "/patients/<patient_id>/followup/<int:followup_id>/complete",
    methods=["POST"]
)
@provider_required
def complete_followup(
    patient_id,
    followup_id
):

    try:
        patient_id_value = int(patient_id)
    except (TypeError, ValueError):
        return redirect(url_for("patients"))
    followup = FollowUp.query.filter_by(
        id=followup_id,
        patient_id=patient_id_value,
        provider_id=session.get("provider_id"),
    ).first()
    if followup and followup.status != "Completed":
        followup.status = "Completed"
        followup.completed_at = datetime.utcnow()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not complete provider follow-up")

    return redirect(
        url_for(
            "patient_details",
            patient_id=patient_id
        )
    )


# =========================================================
# CONSULTATION PAGE
# =========================================================

@app.route("/consultation")
@provider_required
def consultation():

    provider_patients = (
        get_provider_patients()
    )

    return render_template(
        "consultation.html",
        patients=provider_patients
    )


# =========================================================
# FOLLOW-UP PAGE
# =========================================================

@app.route("/follow-up")
@provider_required
def follow_up():
    rows = FollowUp.query.filter_by(
        provider_id=session.get("provider_id")
    ).order_by(FollowUp.follow_up_date.asc(), FollowUp.created_at.asc()).all()
    followups = [followup_to_dict(item) for item in rows]

    return render_template(
        "follow_up.html",
        followups=followups
    )


# =========================================================
# AVAILABILITY PAGE
# =========================================================

def validate_availability_config(payload):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if not isinstance(payload, dict) or not isinstance(payload.get("weekly"), dict):
        return None, "Availability schedule is invalid."
    if not isinstance(payload.get("settings"), dict) or not isinstance(payload.get("exceptions"), list):
        return None, "Availability settings are invalid."

    weekly = {}
    parsed_hours = {}
    for day in days:
        entry = payload["weekly"].get(day)
        if not isinstance(entry, dict) or not isinstance(entry.get("enabled"), bool):
            return None, "Each weekday needs an availability setting."
        start = entry.get("start")
        end = entry.get("end")
        try:
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
        except (TypeError, ValueError):
            return None, f"{day} must have valid start and end times."
        if entry["enabled"] and start_time >= end_time:
            return None, f"{day} must end after it starts."
        weekly[day] = {"enabled": entry["enabled"], "start": start, "end": end}
        parsed_hours[day] = (start_time, end_time)

    settings = payload["settings"]
    try:
        duration = int(settings.get("duration"))
        buffer_minutes = int(settings.get("buffer"))
        break_enabled = settings.get("breakEnabled")
        break_start = settings.get("breakStart")
        break_end = settings.get("breakEnd")
        break_start_time = datetime.strptime(break_start, "%H:%M").time()
        break_end_time = datetime.strptime(break_end, "%H:%M").time()
    except (TypeError, ValueError):
        return None, "Appointment duration, buffer, and break times must be valid."
    if duration not in {15, 20, 30, 45, 60} or buffer_minutes not in {0, 5, 10, 15, 20}:
        return None, "Appointment duration or buffer is not supported."
    if not isinstance(break_enabled, bool) or break_start_time >= break_end_time:
        return None, "Break settings are invalid."
    if break_enabled:
        for day, (start_time, end_time) in parsed_hours.items():
            if weekly[day]["enabled"] and (break_start_time < start_time or break_end_time > end_time):
                return None, f"The break must be within {day}'s working hours."

    exceptions = []
    seen_dates = set()
    if len(payload["exceptions"]) > 366:
        return None, "Too many date exceptions."
    for item in payload["exceptions"]:
        if not isinstance(item, dict):
            return None, "A date exception is invalid."
        exception_id = item.get("id")
        exception_date = item.get("date")
        exception_type = item.get("type")
        reason = item.get("reason", "")
        if not isinstance(exception_id, str) or not exception_id or len(exception_id) > 100:
            return None, "A date exception needs a valid identifier."
        if exception_type not in {"off", "special"} or not isinstance(reason, str) or len(reason) > 500:
            return None, "A date exception contains invalid details."
        try:
            date.fromisoformat(exception_date)
        except (TypeError, ValueError):
            return None, "A date exception needs a valid date."
        if exception_date in seen_dates:
            return None, "Only one exception can be set for each date."
        seen_dates.add(exception_date)
        start = item.get("start", "")
        end = item.get("end", "")
        if exception_type == "special":
            try:
                special_start = datetime.strptime(start, "%H:%M").time()
                special_end = datetime.strptime(end, "%H:%M").time()
            except (TypeError, ValueError):
                return None, "Special working hours need valid times."
            if special_start >= special_end:
                return None, "Special working hours must end after they start."
        else:
            start = ""
            end = ""
        exceptions.append({
            "id": exception_id,
            "date": exception_date,
            "type": exception_type,
            "reason": reason.strip(),
            "start": start,
            "end": end,
        })

    return {
        "weekly": weekly,
        "settings": {
            "duration": duration,
            "buffer": buffer_minutes,
            "breakEnabled": break_enabled,
            "breakStart": break_start,
            "breakEnd": break_end,
        },
        "exceptions": exceptions,
    }, None


def default_availability_config():
    weekly = {}
    for day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        enabled = day_name not in {"Saturday", "Sunday"}
        weekly[day_name] = {
            "enabled": enabled,
            "start": "09:00",
            "end": "17:00" if enabled else "13:00",
        }
    return {
        "weekly": weekly,
        "settings": {
            "duration": 30,
            "buffer": 10,
            "breakEnabled": True,
            "breakStart": "13:00",
            "breakEnd": "14:00",
        },
        "exceptions": [],
    }


def validate_appointment_slot(provider_id, appointment_date, appointment_time, exclude_id=None):
    provider_settings = ProviderSettings.query.filter_by(provider_id=provider_id).first()
    config = (
        provider_settings.availability_config
        if provider_settings and provider_settings.availability_config
        else default_availability_config()
    )
    settings = config.get("settings", {})
    duration = int(settings.get("duration", 30))
    buffer_minutes = int(settings.get("buffer", 10))
    start_minutes = appointment_time.hour * 60 + appointment_time.minute
    end_minutes = start_minutes + duration
    exception = next(
        (item for item in config.get("exceptions", []) if item.get("date") == appointment_date.isoformat()),
        None,
    )

    if exception and exception.get("type") == "off":
        return "This provider is unavailable on the selected date."
    if exception and exception.get("type") == "special":
        day_start = datetime.strptime(exception["start"], "%H:%M").hour * 60 + datetime.strptime(exception["start"], "%H:%M").minute
        day_end = datetime.strptime(exception["end"], "%H:%M").hour * 60 + datetime.strptime(exception["end"], "%H:%M").minute
    else:
        day_config = config.get("weekly", {}).get(appointment_date.strftime("%A"), {})
        if not day_config.get("enabled", False):
            return "This provider is not available on the selected weekday."
        try:
            start_time = datetime.strptime(day_config.get("start", ""), "%H:%M").time()
            end_time = datetime.strptime(day_config.get("end", ""), "%H:%M").time()
        except (TypeError, ValueError):
            return "The provider's availability schedule is invalid. Please contact the provider."
        day_start = start_time.hour * 60 + start_time.minute
        day_end = end_time.hour * 60 + end_time.minute

    if start_minutes < day_start or end_minutes > day_end:
        return "The selected time is outside the provider's available hours."

    if not exception and settings.get("breakEnabled", False):
        try:
            break_start_time = datetime.strptime(settings.get("breakStart", ""), "%H:%M").time()
            break_end_time = datetime.strptime(settings.get("breakEnd", ""), "%H:%M").time()
        except (TypeError, ValueError):
            return "The provider's break schedule is invalid. Please contact the provider."
        break_start = break_start_time.hour * 60 + break_start_time.minute
        break_end = break_end_time.hour * 60 + break_end_time.minute
        if start_minutes < break_end and end_minutes > break_start:
            return "The selected time overlaps the provider's break."

    query = Appointment.query.filter(
        Appointment.provider_id == provider_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status.in_(["Pending", "Confirmed"]),
    )
    if exclude_id is not None:
        query = query.filter(Appointment.id != exclude_id)
    for existing in query.all():
        existing_start = existing.appointment_time.hour * 60 + existing.appointment_time.minute
        existing_end = existing_start + duration
        if (
            start_minutes < existing_end + buffer_minutes
            and existing_start < end_minutes + buffer_minutes
        ):
            return "This time conflicts with another appointment. Please choose a different time."
    return None


@app.route("/availability", methods=["GET", "POST"])
@provider_required
def availability():
    """
    Provider availability page.

    The current availability page stores its schedule in
    browser localStorage. The settings object below is also
    supplied to Jinja so templates that reference `settings`
    do not fail with an UndefinedError.
    """

    provider_id = session.get("provider_id")
    provider_settings = ProviderSettings.query.filter_by(provider_id=provider_id).first()

    if request.method == "POST":
        config, error = validate_availability_config(request.get_json(silent=True))
        if error:
            return jsonify(error=error), 400
        if not provider_settings:
            provider_settings = ProviderSettings(provider_id=provider_id)
            db.session.add(provider_settings)
        provider_settings.availability_config = config
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception("Could not save provider availability")
            return jsonify(error="Availability could not be saved. Please try again."), 500
        return jsonify(message="Availability saved to your provider account.")

    return render_template(
        "availability.html",
        settings=provider_settings.availability_config.get("settings", {}) if provider_settings and provider_settings.availability_config else {},
        availability_config=provider_settings.availability_config if provider_settings else None,
        has_saved_availability=bool(provider_settings and provider_settings.availability_config),
    )


# =========================================================
# PROVIDER NOTIFICATIONS
# =========================================================

@app.route("/provider-notifications")
@provider_required
def provider_notifications():

    notifications = (
        build_provider_notifications()
    )

    return render_template(
        "provider_notifications.html",
        notifications=notifications,
        unread_count=len(notifications),
    )


# =========================================================
# PROVIDER PROFILE
# =========================================================

@app.route("/provider-profile")
@provider_required
def provider_profile():

    return render_template(
        "provider_profile.html",

        fullname=session.get(
            "provider_fullname"
        ),

        email=session.get(
            "provider_email"
        ),

        phone=session.get(
            "provider_phone"
        ),

        provider_type=session.get(
            "provider_type"
        ),

        specialization=session.get(
            "provider_specialization"
        ),

        organization=session.get(
            "provider_organization"
        ),

        location=session.get(
            "provider_location"
        )
    )


# =========================================================
# PROVIDER SETTINGS
# =========================================================

@app.route(
    "/provider-settings",
    methods=["GET", "POST"]
)
@provider_required
def provider_settings():

    provider_id = session.get("provider_id")
    settings_record = ProviderSettings.query.filter_by(
        provider_id=provider_id
    ).first()
    settings_data = {
        "appointment_notifications": settings_record.appointment_notifications if settings_record else True,
        "patient_notifications": settings_record.patient_notifications if settings_record else True,
        "followup_notifications": settings_record.followup_notifications if settings_record else True,
        "system_notifications": settings_record.system_notifications if settings_record else True,
        "profile_visible": settings_record.profile_visible if settings_record else True,
        "organization_visible": settings_record.organization_visible if settings_record else True,
    }

    # =====================================================
    # POST REQUEST
    # =====================================================

    if request.method == "POST":

        action = request.form.get(
            "action",
            ""
        ).strip()

        # =================================================
        # SAVE ACCOUNT PREFERENCES
        # =================================================

        if action == "save_preferences":

            fullname = request.form.get(
                "fullname",
                ""
            ).strip()

            phone = request.form.get(
                "phone",
                ""
            ).strip()

            organization = request.form.get(
                "organization",
                ""
            ).strip()

            if not fullname:
                return render_template(
                    "provider_settings.html",
                    provider_settings=settings_data,
                    settings_error="Full name is required.",
                ), 400

            if len(fullname) > 120 or len(phone) > 20 or len(organization) > 120:
                return render_template(
                    "provider_settings.html",
                    provider_settings=settings_data,
                    settings_error="Please check the length of your name, phone, and organization fields.",
                ), 400

            provider = db.session.get(Provider, provider_id)
            if not provider:
                return render_template(
                    "provider_settings.html",
                    provider_settings=settings_data,
                    settings_error="Provider account was not found.",
                ), 404

            provider.fullname = fullname
            provider.phone = phone
            provider.organization = organization or None

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception("Could not save provider account preferences")
                return render_template(
                    "provider_settings.html",
                    provider_settings=settings_data,
                    settings_error="Account preferences could not be saved. Please try again.",
                ), 500

            session["provider_fullname"] = provider.fullname
            session["provider_phone"] = provider.phone
            session["provider_organization"] = provider.organization or ""

            return render_template(
                "provider_settings.html",

                provider_settings=settings_data,

                settings_success=(
                    "Account preferences saved successfully."
                )
            )

        # =================================================
        # SAVE NOTIFICATION SETTINGS
        # =================================================

        elif action == "save_notifications":
            if not settings_record:
                settings_record = ProviderSettings(provider_id=provider_id)
                db.session.add(settings_record)

            for key in (
                "appointment_notifications",
                "patient_notifications",
                "followup_notifications",
                "system_notifications",
            ):
                setattr(settings_record, key, request.form.get(key) == "on")

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception("Could not save provider notification settings")
                return render_template(
                    "provider_settings.html",
                    provider_settings=settings_data,
                    settings_error="Notification settings could not be saved. Please try again.",
                ), 500

            settings_data.update({
                key: getattr(settings_record, key)
                for key in (
                    "appointment_notifications",
                    "patient_notifications",
                    "followup_notifications",
                    "system_notifications",
                )
            })

            return render_template(
                "provider_settings.html",

                provider_settings=(
                    settings_data
                ),

                settings_success=(
                    "Notification settings saved successfully."
                )
            )

        # =================================================
        # SAVE PRIVACY SETTINGS
        # =================================================

        elif action == "save_privacy":
            if not settings_record:
                settings_record = ProviderSettings(provider_id=provider_id)
                db.session.add(settings_record)

            settings_record.profile_visible = request.form.get("profile_visible") == "on"
            settings_record.organization_visible = request.form.get("organization_visible") == "on"

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception("Could not save provider privacy settings")
                return render_template(
                    "provider_settings.html",
                    provider_settings=settings_data,
                    settings_error="Privacy settings could not be saved. Please try again.",
                ), 500

            settings_data["profile_visible"] = settings_record.profile_visible
            settings_data["organization_visible"] = settings_record.organization_visible

            return render_template(
                "provider_settings.html",

                provider_settings=(
                    settings_data
                ),

                settings_success=(
                    "Privacy settings saved successfully."
                )
            )

        # =================================================
        # CHANGE PASSWORD
        # =================================================

        elif action == "change_password":

            current_password = request.form.get(
                "current_password",
                ""
            )

            new_password = request.form.get(
                "new_password",
                ""
            )

            confirm_password = request.form.get(
                "confirm_password",
                ""
            )

            provider_id = session.get("provider_id")

            provider = Provider.query.get(
                provider_id
            ) if provider_id else None

            if not provider:

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "Provider account was not found."
                    )
                ), 404

            if not current_password:

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "Please enter your current password."
                    )
                ), 400

            if not new_password:

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "Please enter a new password."
                    )
                ), 400

            if len(new_password) < 8:

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "New password must contain at least 8 characters."
                    )
                ), 400

            if (
                new_password
                != confirm_password
            ):

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "New password and confirmation do not match."
                    )
                ), 400

            if (
                new_password
                == current_password
            ):

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "New password must be different "
                        "from your current password."
                    )
                ), 400

            if not check_password_hash(
                provider.password_hash,
                current_password
            ):

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "Current password is incorrect."
                    )
                ), 400

            try:

                provider.password_hash = (
                    generate_password_hash(new_password)
                )

                db.session.commit()

            except Exception:

                db.session.rollback()

                return render_template(
                    "provider_settings.html",

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "Password could not be updated."
                    )
                ), 500

            session[
                "provider_logged_in"
            ] = True

            return render_template(
                "provider_settings.html",

                provider_settings=(
                    app.config[
                        "provider_settings"
                    ]
                ),

                settings_success=(
                    "Password updated successfully."
                )
            )

        # =================================================
        # INVALID ACTION
        # =================================================

        else:

            return render_template(
                "provider_settings.html",

                provider_settings=(
                    app.config[
                        "provider_settings"
                    ]
                ),

                settings_error=(
                    "Invalid settings request."
                )
            ), 400

    # =====================================================
    # GET REQUEST
    # =====================================================

    return render_template(
        "provider_settings.html",

        provider_settings=settings_data
    )


# =========================================================
# PROVIDER LOGOUT
# =========================================================

@app.route("/provider-logout")
def provider_logout():

    session.clear()

    return redirect(
        url_for("provider_login")
    )


# =========================================================
# PATIENT LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
