"""
Database layer for IHIS Simulation Dashboard.
Uses SQLAlchemy + MySQL (Local).
"""

import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, String, Float, Integer, Boolean,
    DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Will be set from environment or app config
DATABASE_URL = os.environ.get("DATABASE_URL", "")

Base = declarative_base()
engine = None
SessionLocal = None

def init_db(database_url: str = None):
    """Initialize database connection and create tables."""
    global engine, SessionLocal, DATABASE_URL
    if database_url:
        DATABASE_URL = database_url
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not set. Pass local MySQL connection URL.")

    # Normalize mysql:// to mysql+pymysql:// if driver not specified
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

    # Configure connection pooling and encoding optimized for MySQL
    if DATABASE_URL.startswith("mysql"):
        if "charset" not in DATABASE_URL:
            DATABASE_URL += ("&" if "?" in DATABASE_URL else "?") + "charset=utf8mb4"
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10,
            max_overflow=20
        )
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return SessionLocal()

# ============================================================
# Models
# ============================================================

class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_resources = Column(Integer, default=0)
    valid_resources = Column(Integer, default=0)
    invalid_resources = Column(Integer, default=0)
    status = Column(String(50), default="processing")  # processing, completed, failed

    patients = relationship("Patient", back_populates="batch", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="batch", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="batch", cascade="all, delete-orphan")
    conditions = relationship("Condition", back_populates="batch", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="batch", cascade="all, delete-orphan")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(100), primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False)
    given_name = Column(String(255))
    family_name = Column(String(255))
    birth_date = Column(String(20))
    gender = Column(String(20))
    address_city = Column(String(255))
    address_country = Column(String(100))
    marital_status = Column(String(50))
    resource_type = Column(String(50), default="Patient")
    fhir_valid = Column(Boolean, default=False)
    raw_json = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    batch = relationship("UploadBatch", back_populates="patients")

class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(String(100), primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False)
    patient_id = Column(String(100))
    encounter_class = Column(String(50))
    encounter_type = Column(String(255))
    period_start = Column(String(50))
    period_end = Column(String(50))
    status = Column(String(50))
    resource_type = Column(String(50), default="Encounter")
    fhir_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    batch = relationship("UploadBatch", back_populates="encounters")

class Observation(Base):
    __tablename__ = "observations"

    id = Column(String(100), primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False)
    patient_id = Column(String(100))
    encounter_id = Column(String(100))
    loinc_code = Column(String(50))
    display = Column(String(500))
    value_quantity = Column(Float)
    value_unit = Column(String(100))
    value_string = Column(Text)
    status = Column(String(50))
    resource_type = Column(String(50), default="Observation")
    fhir_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    batch = relationship("UploadBatch", back_populates="observations")

class Condition(Base):
    __tablename__ = "conditions"

    id = Column(String(100), primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False)
    patient_id = Column(String(100))
    icd10_code = Column(String(50))
    snomed_code = Column(String(50))
    display = Column(String(500))
    clinical_status = Column(String(50))
    onset_date = Column(String(50))
    resource_type = Column(String(50), default="Condition")
    fhir_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    batch = relationship("UploadBatch", back_populates="conditions")

class Medication(Base):
    __tablename__ = "medications"

    id = Column(String(100), primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), nullable=False)
    patient_id = Column(String(100))
    rxnorm_code = Column(String(50))
    snomed_code = Column(String(50))
    medication_name = Column(String(500))
    status = Column(String(50))
    authored_on = Column(String(50))
    resource_type = Column(String(50), default="MedicationRequest")
    fhir_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    batch = relationship("UploadBatch", back_populates="medications")

class Dhis2Data(Base):
    __tablename__ = "dhis2_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    indicator_name = Column(String(500))
    indicator_id = Column(String(100))
    period = Column(String(20))
    org_unit = Column(String(255))
    value = Column(Float)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_patients = Column(Integer)
    total_encounters = Column(Integer)
    total_observations = Column(Integer)
    total_conditions = Column(Integer)
    total_medications = Column(Integer)
    total_resources = Column(Integer)
    fhir_valid_count = Column(Integer)
    fhir_compliance_pct = Column(Float)
    arrival_rate = Column(Float)
    service_rate = Column(Float)
    num_servers = Column(Integer)
    utilisation = Column(Float)
    system_stable = Column(Boolean)
    avg_response_ms = Column(Float)
    avg_queue_wait_ms = Column(Float)
    throughput_tps = Column(Float)
    availability_pct = Column(Float)
    failure_rate_pct = Column(Float)
    results_json = Column(JSON)
