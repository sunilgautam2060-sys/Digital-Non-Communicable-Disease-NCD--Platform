"""Initial migration: Patient, Provider, Appointment, HealthRecord, ConsultationNote, FollowUp, ProviderSettings

Revision ID: 80e02a7b45bd
Revises: 
Create Date: 2026-11-21 07:27:51.228561

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '80e02a7b45bd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create new tables only - do not drop existing tables
    op.create_table('patient',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fullname', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('account_type', sa.String(length=30), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('patient_pkey')),
        sa.UniqueConstraint('email', name=op.f('patient_email_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    with op.batch_alter_table('patient', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_patient_email'), ['email'], unique=False)

    op.create_table('provider',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fullname', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('provider_type', sa.String(length=30), nullable=False),
        sa.Column('specialization', sa.String(length=60), nullable=True),
        sa.Column('organization', sa.String(length=120), nullable=True),
        sa.Column('location', sa.String(length=120), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('provider_pkey')),
        sa.UniqueConstraint('email', name=op.f('provider_email_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    with op.batch_alter_table('provider', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_provider_email'), ['email'], unique=False)

    op.create_table('provider_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('appointment_notifications', sa.Boolean(), nullable=False),
        sa.Column('patient_notifications', sa.Boolean(), nullable=False),
        sa.Column('followup_notifications', sa.Boolean(), nullable=False),
        sa.Column('system_notifications', sa.Boolean(), nullable=False),
        sa.Column('profile_visible', sa.Boolean(), nullable=False),
        sa.Column('organization_visible', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('provider_settings_provider_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('provider_settings_pkey')),
        sa.UniqueConstraint('provider_id', name=op.f('provider_settings_provider_id_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )

    op.create_table('appointment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('appointment_date', sa.Date(), nullable=False),
        sa.Column('appointment_time', sa.Time(), nullable=False),
        sa.Column('consultation_type', sa.String(length=50), nullable=True),
        sa.Column('condition_reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('notification_message', sa.Text(), nullable=True),
        sa.Column('last_action_by', sa.String(length=20), nullable=True),
        sa.Column('last_action_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patient.id'], name=op.f('appointment_patient_id_fkey')),
        sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('appointment_provider_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('appointment_pkey'))
    )

    op.create_table('consultation_note',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('consultation_note_provider_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('consultation_note_pkey'))
    )

    op.create_table('follow_up',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('follow_up_date', sa.Date(), nullable=False),
        sa.Column('follow_up_time', sa.Time(), nullable=False),
        sa.Column('follow_up_type', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['provider.id'], name=op.f('follow_up_provider_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('follow_up_pkey'))
    )

    op.create_table('health_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('record_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.Column('date_recorded', sa.Date(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patient.id'], name=op.f('health_record_patient_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('health_record_pkey'))
    )


def downgrade():
    # Drop only the tables we created
    op.drop_table('health_record')
    op.drop_table('follow_up')
    op.drop_table('consultation_note')
    op.drop_table('appointment')
    op.drop_table('provider_settings')
    with op.batch_alter_table('provider', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_provider_email'))
    op.drop_table('provider')
    with op.batch_alter_table('patient', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_patient_email'))
    op.drop_table('patient')