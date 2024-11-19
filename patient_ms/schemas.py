from pydantic import BaseModel

class PatientCreate(BaseModel):
    patient_id: str
    patient_name: str
    medical_history: str

class PatientResponse(BaseModel):
    id: int
    patient_id: str
    patient_name: str
    medical_history: str

    class Config:
        orm_mode = True  # Allows SQLAlchemy models to be returned in responses

