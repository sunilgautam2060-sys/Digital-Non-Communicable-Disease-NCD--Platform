from extensions import db
from datetime import datetime


class Patient(db.Model):
    __tablename__ = "patient"

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    address = db.Column(db.Text)
    account_type = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notification_preferences = db.Column(db.JSON, nullable=True)

    appointments = db.relationship("Appointment", back_populates="patient", lazy="dynamic")
    health_records = db.relationship("HealthRecord", back_populates="patient", lazy="dynamic")
    medications = db.relationship("Medication", back_populates="patient", lazy="dynamic")

    def __repr__(self):
        return f"<Patient {self.id}: {self.fullname} ({self.email})>"


class Provider(db.Model):
    __tablename__ = "provider"

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    provider_type = db.Column(db.String(30), nullable=False)
    specialization = db.Column(db.String(60))
    organization = db.Column(db.String(120))
    location = db.Column(db.String(120))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    appointments = db.relationship("Appointment", back_populates="provider", lazy="dynamic")
    consultation_notes = db.relationship("ConsultationNote", back_populates="provider", lazy="dynamic")
    followups = db.relationship("FollowUp", back_populates="provider", lazy="dynamic")
    settings = db.relationship("ProviderSettings", back_populates="provider", uselist=False)

    def __repr__(self):
        return f"<Provider {self.id}: {self.fullname} ({self.email})>"


class Appointment(db.Model):
    __tablename__ = "appointment"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    service = db.Column(db.String(80))
    consultation_type = db.Column(db.String(50))
    location = db.Column(db.String(200))
    condition_reason = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notification_message = db.Column(db.Text)
    last_action_by = db.Column(db.String(20))
    last_action_at = db.Column(db.DateTime)

    patient = db.relationship("Patient", back_populates="appointments")
    provider = db.relationship("Provider", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment {self.id}: Patient {self.patient_id} -> Provider {self.provider_id} ({self.status})>"


class HealthRecord(db.Model):
    __tablename__ = "health_record"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    record_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    date_recorded = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="health_records")

    def __repr__(self):
        return f"<HealthRecord {self.id}: {self.record_type}={self.value}>"


class Medication(db.Model):
    __tablename__ = "medication"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    dose = db.Column(db.String(80), nullable=False)
    instructions = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    patient = db.relationship("Patient", back_populates="medications")
    logs = db.relationship("MedicationLog", back_populates="medication", lazy="dynamic")

    def __repr__(self):
        return f"<Medication {self.id}: Patient {self.patient_id}>"


class MedicationLog(db.Model):
    __tablename__ = "medication_log"
    __table_args__ = (
        db.UniqueConstraint("medication_id", "intake_date", name="uq_medication_log_medication_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey("medication.id"), nullable=False, index=True)
    intake_date = db.Column(db.Date, nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    medication = db.relationship("Medication", back_populates="logs")

    def __repr__(self):
        return f"<MedicationLog {self.id}: Medication {self.medication_id} on {self.intake_date}>"


class ConsultationNote(db.Model):
    __tablename__ = "consultation_note"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=False)
    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointment.id", name="fk_consultation_note_appointment"),
        nullable=True,
    )
    note_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    provider = db.relationship("Provider", back_populates="consultation_notes")

    def __repr__(self):
        return f"<ConsultationNote {self.id}: Provider {self.provider_id} -> Patient {self.patient_id}>"


class FollowUp(db.Model):
    __tablename__ = "follow_up"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=False)
    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey("appointment.id", name="fk_follow_up_appointment"),
        nullable=True,
    )
    follow_up_date = db.Column(db.Date, nullable=False)
    follow_up_time = db.Column(db.Time, nullable=True)
    follow_up_type = db.Column(db.String(50))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)

    provider = db.relationship("Provider", back_populates="followups")

    def __repr__(self):
        return f"<FollowUp {self.id}: Patient {self.patient_id} on {self.follow_up_date} ({self.status})>"


class ProviderSettings(db.Model):
    __tablename__ = "provider_settings"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), unique=True, nullable=False)
    appointment_notifications = db.Column(db.Boolean, default=True, nullable=False)
    patient_notifications = db.Column(db.Boolean, default=True, nullable=False)
    followup_notifications = db.Column(db.Boolean, default=True, nullable=False)
    system_notifications = db.Column(db.Boolean, default=True, nullable=False)
    profile_visible = db.Column(db.Boolean, default=True, nullable=False)
    organization_visible = db.Column(db.Boolean, default=True, nullable=False)
    availability_config = db.Column(db.JSON, nullable=True)

    provider = db.relationship("Provider", back_populates="settings")

    def __repr__(self):
        return f"<ProviderSettings {self.id}: Provider {self.provider_id}>"
