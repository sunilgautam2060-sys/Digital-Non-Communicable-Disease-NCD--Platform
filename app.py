from flask import Flask, render_template, request, redirect, url_for, session, jsonify
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
FollowUp = models.FollowUp


# =========================================================
# DEMO DATA STORAGE
# =========================================================

app.config["registered_user"] = None
app.config["registered_provider"] = None

# Patient-management storage
app.config["patients"] = {}
app.config["patient_counter"] = 1

app.config["consultation_notes"] = []
app.config["followups"] = []

app.config["note_counter"] = 1
app.config["followup_counter"] = 1

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

        patient["followup_required"] = any(
            item.get("status") == "Pending"
            for item in app.config["followups"]
            if item.get("patient_id")
            == patient["patient_id"]

            and normalize_text(
                item.get("provider_email", "")
            )
            == normalize_text(
                session.get("provider_email", "")
            )
        )

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

    provider_email = normalize_text(
        session.get("provider_email", "")
    )

    return [
        note

        for note in app.config["consultation_notes"]

        if normalize_text(
            note.get("patient_id", "")
        ) == normalize_text(patient_id)

        and normalize_text(
            note.get("provider_email", "")
        ) == provider_email
    ]


# =========================================================
# FOLLOW-UP HELPERS
# =========================================================

def get_provider_patient_followups(patient_id):

    provider_email = normalize_text(
        session.get("provider_email", "")
    )

    return [
        item

        for item in app.config["followups"]

        if normalize_text(
            item.get("patient_id", "")
        ) == normalize_text(patient_id)

        and normalize_text(
            item.get("provider_email", "")
        ) == provider_email
    ]


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
        record_type="Weight",
    ).order_by(
        HealthRecord.date_recorded.desc(),
        HealthRecord.created_at.desc(),
    ).all()
    current_weight = records[0] if records else None
    previous_weight = records[1] if len(records) > 1 else None

    return render_template(
        "monitoring.html",
        current_weight=current_weight,
        previous_weight=previous_weight,
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

    patient_email = session.get(
        "email",
        ""
    )

    notifications = build_patient_notifications(
        patient_email
    )

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
                settings_error=(
                    "Settings could not be saved."
                )
            ), 500

        session["fullname"] = patient.fullname

        session["phone"] = patient.phone

        session["address"] = patient.address or ""

        return render_template(
            "settings.html",
            settings_success=(
                "Settings saved successfully."
            )
        )

    return render_template(
        "settings.html"
    )


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

    note_text = request.form.get(
        "note",
        ""
    ).strip()

    if note_text:

        note_id = (
            app.config["note_counter"]
        )

        app.config["note_counter"] += 1

        app.config[
            "consultation_notes"
        ].append({

            "id": note_id,

            "patient_id": patient_id,

            "provider_email": session.get(
                "provider_email",
                ""
            ),

            "provider_name": session.get(
                "provider_fullname",
                ""
            ),

            "note": note_text,

            "created_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        })

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

    provider_email = normalize_text(
        session.get(
            "provider_email",
            ""
        )
    )

    note_text = request.form.get(
        "note",
        ""
    ).strip()

    for note in app.config[
        "consultation_notes"
    ]:

        if (
            note.get("id")
            == note_id

            and normalize_text(
                note.get(
                    "patient_id",
                    ""
                )
            )
            == normalize_text(
                patient_id
            )

            and normalize_text(
                note.get(
                    "provider_email",
                    ""
                )
            )
            == provider_email
        ):

            if note_text:

                note["note"] = (
                    note_text
                )

                note["updated_at"] = (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

            break

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

    provider_email = normalize_text(
        session.get(
            "provider_email",
            ""
        )
    )

    remaining_notes = []

    for note in app.config[
        "consultation_notes"
    ]:

        is_target = (
            note.get("id")
            == note_id

            and normalize_text(
                note.get(
                    "patient_id",
                    ""
                )
            )
            == normalize_text(
                patient_id
            )

            and normalize_text(
                note.get(
                    "provider_email",
                    ""
                )
            )
            == provider_email
        )

        if not is_target:

            remaining_notes.append(
                note
            )

    app.config[
        "consultation_notes"
    ] = remaining_notes

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

    followup_date = request.form.get(
        "followup_date",
        ""
    ).strip()

    followup_time = request.form.get(
        "followup_time",
        ""
    ).strip()

    followup_type = request.form.get(
        "followup_type",
        ""
    ).strip()

    notes = request.form.get(
        "notes",
        ""
    ).strip()

    if followup_date:

        followup_id = (
            app.config[
                "followup_counter"
            ]
        )

        app.config[
            "followup_counter"
        ] += 1

        app.config[
            "followups"
        ].append({

            "id": followup_id,

            "patient_id": patient_id,

            "patient_name": patient.get(
                "fullname",
                ""
            ),

            "provider_email": session.get(
                "provider_email",
                ""
            ),

            "provider_name": session.get(
                "provider_fullname",
                ""
            ),

            "followup_date": (
                followup_date
            ),

            "followup_time": (
                followup_time
            ),

            "followup_type": (
                followup_type
            ),

            "notes": notes,

            "status": "Pending",

            "created_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        })

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

    provider_email = normalize_text(
        session.get(
            "provider_email",
            ""
        )
    )

    for item in app.config[
        "followups"
    ]:

        if (
            item.get("id")
            == followup_id

            and normalize_text(
                item.get(
                    "patient_id",
                    ""
                )
            )
            == normalize_text(
                patient_id
            )

            and normalize_text(
                item.get(
                    "provider_email",
                    ""
                )
            )
            == provider_email
        ):

            item["status"] = (
                "Completed"
            )

            item["completed_at"] = (
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

            break

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

    provider_email = normalize_text(
        session.get(
            "provider_email",
            ""
        )
    )

    followups = [

        item

        for item
        in app.config[
            "followups"
        ]

        if normalize_text(
            item.get(
                "provider_email",
                ""
            )
        ) == provider_email
    ]

    followups.sort(
        key=lambda item: (
            item.get(
                "followup_date",
                ""
            )
        )
    )

    return render_template(
        "follow_up.html",
        followups=followups
    )


# =========================================================
# AVAILABILITY PAGE
# =========================================================

@app.route("/availability")
@provider_required
def availability():
    """
    Provider availability page.

    The current availability page stores its schedule in
    browser localStorage. The settings object below is also
    supplied to Jinja so templates that reference `settings`
    do not fail with an UndefinedError.
    """

    availability_settings = {
        "duration": 30,
        "buffer": 10,
        "break_enabled": True,
        "break_start": "13:00",
        "break_end": "14:00"
    }

    return render_template(
        "availability.html",
        settings=availability_settings
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

                    provider_settings=(
                        app.config[
                            "provider_settings"
                        ]
                    ),

                    settings_error=(
                        "Full name is required."
                    )
                ), 400

            provider = (
                app.config.get(
                    "registered_provider"
                )
            )

            if provider:

                provider["fullname"] = (
                    fullname
                )

                provider["phone"] = (
                    phone
                )

                provider["organization"] = (
                    organization
                )

                app.config[
                    "registered_provider"
                ] = provider

                session[
                    "provider_fullname"
                ] = fullname

                session[
                    "provider_phone"
                ] = phone

                session[
                    "provider_organization"
                ] = organization

            return render_template(
                "provider_settings.html",

                provider_settings=(
                    app.config[
                        "provider_settings"
                    ]
                ),

                settings_success=(
                    "Account preferences saved successfully."
                )
            )

        # =================================================
        # SAVE NOTIFICATION SETTINGS
        # =================================================

        elif action == "save_notifications":

            settings_data = (
                app.config[
                    "provider_settings"
                ]
            )

            settings_data[
                "appointment_notifications"
            ] = (
                request.form.get(
                    "appointment_notifications"
                ) == "on"
            )

            settings_data[
                "patient_notifications"
            ] = (
                request.form.get(
                    "patient_notifications"
                ) == "on"
            )

            settings_data[
                "followup_notifications"
            ] = (
                request.form.get(
                    "followup_notifications"
                ) == "on"
            )

            settings_data[
                "system_notifications"
            ] = (
                request.form.get(
                    "system_notifications"
                ) == "on"
            )

            app.config[
                "provider_settings"
            ] = settings_data

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

            settings_data = (
                app.config[
                    "provider_settings"
                ]
            )

            settings_data[
                "profile_visible"
            ] = (
                request.form.get(
                    "profile_visible"
                ) == "on"
            )

            settings_data[
                "organization_visible"
            ] = (
                request.form.get(
                    "organization_visible"
                ) == "on"
            )

            app.config[
                "provider_settings"
            ] = settings_data

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

        provider_settings=(
            app.config[
                "provider_settings"
            ]
        )
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
