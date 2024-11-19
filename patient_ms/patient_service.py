from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Patient
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PatientService:
    def __init__(self, db: Session):
        self.db = db

    def add_patient(self, patient_id: str, patient_name: str, medical_history: str):
        new_patient = Patient(patient_id=patient_id, patient_name=patient_name, medical_history=medical_history)
        self.db.add(new_patient)
        self.db.commit()
        self.db.refresh(new_patient)
        logger.info(f"Patient added: {patient_id}, {patient_name}, {medical_history}")
        return new_patient

    def get_patient_by_id(self, patient_id: str):
        return self.db.query(Patient).filter(Patient.patient_id == patient_id).first()

    def update_patient(self, patient_id: str, medical_history: str):
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        patient.medical_history = medical_history
        self.db.commit()
        logger.info(f"Updated medical history for patient ID {patient_id}")
        return patient

    def delete_patient(self, patient_id: str):
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        self.db.delete(patient)
        self.db.commit()
        logger.info(f"Deleted patient with ID {patient_id}")

