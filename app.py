from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime, date
from functools import wraps
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# =========================================================
# DEMO DATA STORAGE
# =========================================================

app.config["registered_user"] = None
app.config["registered_provider"] = None

app.config["appointments"] = []
app.config["appointment_counter"] = 1

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
    Return the currently registered provider.
    """
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

def get_provider_appointments():
    """
    Return appointments belonging to the logged-in provider.

    Provider email is the primary identifier.
    Provider name is retained as a fallback for older records.
    """

    result = []

    for appointment in app.config["appointments"]:

        if appointment_belongs_to_provider(appointment):

            # Make sure old appointments also receive
            # the current provider identity.
            if not appointment.get("provider_email"):
                appointment["provider_email"] = (
                    session.get("provider_email", "")
                )

            if not appointment.get("provider_name"):
                appointment["provider_name"] = (
                    session.get("provider_fullname", "")
                )

            # Make sure the appointment has a patient record.
            get_or_create_patient(appointment)

            result.append(appointment)

    # Latest appointments first.
    result.sort(
        key=lambda item: (
            item.get("appointment_date", ""),
            item.get("appointment_time", ""),
            item.get("created_at", "")
        ),
        reverse=True
    )

    return result


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

        patient = get_or_create_patient(appointment)

        if not patient:
            continue

        email = patient["email"]

        if email not in patient_map:

            patient_map[email] = dict(patient)

            patient_map[email]["appointments"] = []

        patient_map[email]["appointments"].append(
            appointment
        )

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

        if patient["patient_id"] == patient_id:
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

    patient_appointments = [
        item

        for item in app.config["appointments"]

        if normalize_text(
            item.get("patient_email", "")
        ) == patient_email
    ]

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

        app.config["registered_user"] = {
            "fullname": fullname,
            "email": email,
            "phone": phone,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "address": address,
            "account_type": account_type,
            "password": password
        }

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

        registered_user = app.config.get(
            "registered_user"
        )

        if not registered_user:

            return render_template(
                "login.html",
                error=(
                    "No registered account found. "
                    "Please create an account first."
                )
            )

        if (
            email
            == registered_user["email"].lower()
            and password
            == registered_user["password"]
        ):

            session.clear()

            session["logged_in"] = True

            session["email"] = (
                registered_user["email"]
            )

            session["fullname"] = (
                registered_user["fullname"]
            )

            session["phone"] = (
                registered_user["phone"]
            )

            session["date_of_birth"] = (
                registered_user["date_of_birth"]
            )

            session["gender"] = (
                registered_user["gender"]
            )

            session["address"] = (
                registered_user["address"]
            )

            session["account_type"] = (
                registered_user["account_type"]
            )

            return redirect(
                url_for("dashboard")
            )

        return render_template(
            "login.html",
            error="Invalid email or password."
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

    return render_template(
        "monitoring.html"
    )


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

    patient_email = normalize_text(
        session.get("email", "")
    )

    patient_appointments = [
        item

        for item in app.config["appointments"]

        if normalize_text(
            item.get("patient_email", "")
        ) == patient_email
    ]

    return render_template(
        "records.html",
        appointments=patient_appointments
    )


# =========================================================
# APPOINTMENTS
# =========================================================

@app.route("/appointments", methods=["GET", "POST"])
@patient_required
def appointments():

    if request.method == "POST":

        provider_name = request.form.get(
            "provider_name",
            ""
        ).strip()

        provider_email = request.form.get(
            "provider_email",
            ""
        ).strip()

        appointment_date = request.form.get(
            "appointment_date",
            ""
        ).strip()

        appointment_time = request.form.get(
            "appointment_time",
            ""
        ).strip()

        consultation_type = request.form.get(
            "consultation_type",
            ""
        ).strip()

        condition = request.form.get(
            "condition",
            ""
        ).strip()

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        if not appointment_date:
            return render_template(
                "appointments.html",
                error="Please select an appointment date."
            )

        if not appointment_time:
            return render_template(
                "appointments.html",
                error="Please select an appointment time."
            )

        if not provider_name:
            return render_template(
                "appointments.html",
                error="Please select a service provider."
            )

        resolved_provider = resolve_provider_identity(
            provider_name,
            provider_email
        )

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        appointment_id = (
            app.config["appointment_counter"]
        )

        app.config["appointment_counter"] += 1

        appointment = {

            "id": appointment_id,

            "patient_id": "",

            "patient_name": session.get(
                "fullname",
                ""
            ),

            "patient_email": session.get(
                "email",
                ""
            ),

            "patient_phone": session.get(
                "phone",
                ""
            ),

            "patient_dob": session.get(
                "date_of_birth",
                ""
            ),

            "patient_gender": session.get(
                "gender",
                ""
            ),

            "patient_address": session.get(
                "address",
                ""
            ),

            "account_type": session.get(
                "account_type",
                ""
            ),

            "provider_name": resolved_provider.get(
                "name",
                provider_name
            ),

            "provider_email": resolved_provider.get(
                "email",
                provider_email
            ),

            "appointment_date": appointment_date,

            "appointment_time": appointment_time,

            "consultation_type": (
                consultation_type
            ),

            "condition": condition,

            "reason": reason,

            "status": "Pending",

            "created_at": now,

            "updated_at": now,

            "notification": (
                "Your appointment request has been "
                "submitted and is pending provider confirmation."
            ),

            "action_by": "",

            "action_at": ""
        }

        get_or_create_patient(
            appointment
        )

        app.config["appointments"].append(
            appointment
        )

        return redirect(
            url_for("appointments")
        )

    patient_email = normalize_text(
        session.get("email", "")
    )

    patient_appointments = [

        item

        for item in app.config["appointments"]

        if normalize_text(
            item.get("patient_email", "")
        ) == patient_email

    ]

    patient_appointments.sort(
        key=lambda item: (
            item.get("appointment_date", ""),
            item.get("appointment_time", ""),
            item.get("created_at", "")
        ),
        reverse=True
    )

    return render_template(
        "appointments.html",
        appointments=patient_appointments
    )


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

        registered_user = app.config.get(
            "registered_user"
        )

        if registered_user:

            if fullname:
                registered_user["fullname"] = fullname

            if phone:
                registered_user["phone"] = phone

            if address:
                registered_user["address"] = address

            app.config["registered_user"] = (
                registered_user
            )

            session["fullname"] = (
                registered_user["fullname"]
            )

            session["phone"] = (
                registered_user["phone"]
            )

            session["address"] = (
                registered_user["address"]
            )

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

@app.route(
    "/change-password",
    methods=["GET", "POST"]
)
@patient_required
def change_password():

    if request.method == "POST":

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

        user = app.config.get(
            "registered_user"
        )

        if not user:

            return render_template(
                "change-password.html",
                error="User account was not found."
            ), 404

        if (
            current_password
            != user.get("password", "")
        ):

            return render_template(
                "change-password.html",
                error="Current password is incorrect."
            ), 400

        if not new_password:

            return render_template(
                "change-password.html",
                error="Please enter a new password."
            ), 400

        if len(new_password) < 8:

            return render_template(
                "change-password.html",
                error=(
                    "New password must contain at least 8 characters."
                )
            ), 400

        if new_password != confirm_password:

            return render_template(
                "change-password.html",
                error=(
                    "New password and confirmation do not match."
                )
            ), 400

        if new_password == current_password:

            return render_template(
                "change-password.html",
                error=(
                    "New password must be different "
                    "from your current password."
                )
            ), 400

        user["password"] = new_password

        app.config["registered_user"] = user

        return render_template(
            "change-password.html",
            success="Password updated successfully."
        )

    return render_template(
        "change-password.html"
    )


# =========================================================
# PROVIDER REGISTER
# =========================================================

@app.route(
    "/provider-register",
    methods=["GET", "POST"]
)
def provider_register():

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

        app.config["registered_provider"] = {

            "fullname": fullname,

            "email": email,

            "phone": phone,

            "provider_type": provider_type,

            "specialization": specialization,

            "organization": organization,

            "location": location,

            "password": password

        }

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

        provider = app.config.get(
            "registered_provider"
        )

        if not provider:

            return render_template(
                "provider_login.html",
                error=(
                    "No provider account found. "
                    "Please register first."
                )
            )

        if (
            email
            == provider.get(
                "email",
                ""
            ).lower()

            and password
            == provider.get(
                "password",
                ""
            )
        ):

            session.clear()

            session["provider_logged_in"] = True

            session["provider_fullname"] = (
                provider.get(
                    "fullname",
                    ""
                )
            )

            session["provider_email"] = (
                provider.get(
                    "email",
                    ""
                )
            )

            session["provider_phone"] = (
                provider.get(
                    "phone",
                    ""
                )
            )

            session["provider_type"] = (
                provider.get(
                    "provider_type",
                    ""
                )
            )

            session["provider_specialization"] = (
                provider.get(
                    "specialization",
                    ""
                )
            )

            session["provider_organization"] = (
                provider.get(
                    "organization",
                    ""
                )
            )

            session["provider_location"] = (
                provider.get(
                    "location",
                    ""
                )
            )

            return redirect(
                url_for("service_provider")
            )

        return render_template(
            "provider_login.html",
            error="Invalid email or password."
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
def appointment_action(
    appointment_id,
    action
):

    allowed_actions = {
        "confirm": "Confirmed",
        "reject": "Rejected",
        "cancel": "Cancelled",
        "complete": "Completed"
    }

    if action not in allowed_actions:

        return redirect(
            url_for(
                "provider_appointments"
            )
        )

    appointment = None

    for item in app.config["appointments"]:

        if (
            item.get("id")
            == appointment_id

            and appointment_belongs_to_provider(
                item
            )
        ):

            appointment = item
            break

    if not appointment:

        return redirect(
            url_for(
                "provider_appointments"
            )
        )

    new_status = allowed_actions[
        action
    ]

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    appointment["status"] = (
        new_status
    )

    appointment["updated_at"] = (
        now
    )

    appointment["action_by"] = (
        session.get(
            "provider_email",
            ""
        )
    )

    appointment["action_at"] = (
        now
    )

    patient_name = appointment.get(
        "patient_name",
        "Patient"
    )

    provider_name = appointment.get(
        "provider_name",
        session.get(
            "provider_fullname",
            "Service Provider"
        )
    )

    if new_status == "Confirmed":

        appointment["notification"] = (
            f"Your appointment with "
            f"{provider_name} has been confirmed."
        )

    elif new_status == "Rejected":

        appointment["notification"] = (
            f"Your appointment request with "
            f"{provider_name} has been rejected."
        )

    elif new_status == "Cancelled":

        appointment["notification"] = (
            f"Your appointment with "
            f"{provider_name} has been cancelled."
        )

    elif new_status == "Completed":

        appointment["notification"] = (
            f"Your appointment with "
            f"{provider_name} has been completed."
        )

    else:

        appointment["notification"] = (
            f"Appointment status updated to "
            f"{new_status}."
        )

    return redirect(
        url_for(
            "provider_appointments"
        )
    )


# =========================================================
# PATIENTS
# =========================================================

@app.route("/patients")
@provider_required
def patients():

    provider_patients = (
        get_provider_patients()
    )

    return render_template(
        "patients.html",
        patients=provider_patients
    )


# =========================================================
# PATIENT DETAILS
# =========================================================

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

        return (
            render_template(
                "patient_details.html",
                patient=None,
                notes=[],
                followups=[],
                error="Patient not found."
            ),
            404
        )

    notes = get_provider_patient_notes(
        patient_id
    )

    followups = get_provider_patient_followups(
        patient_id
    )

    return render_template(
        "patient_details.html",
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
        notifications=notifications
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

            provider = app.config.get(
                "registered_provider"
            )

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

            if (
                current_password
                != provider.get(
                    "password",
                    ""
                )
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

            provider["password"] = (
                new_password
            )

            app.config[
                "registered_provider"
            ] = provider

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