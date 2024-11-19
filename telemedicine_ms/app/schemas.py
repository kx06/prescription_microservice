from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ConsultationStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ConsultationType(str, Enum):
    INITIAL = "initial"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Patient's full name")
    condition: str = Field(..., min_length=5, max_length=500, description="Patient's medical condition")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "condition": "Type 2 Diabetes"
            }
        }

class ConsultationCreate(BaseModel):
    patient_id: int = Field(..., gt=0, description="Patient ID must be positive")
    doctor_name: str = Field(..., min_length=2, max_length=100)
    consultation_type: ConsultationType
    status: ConsultationStatus
    notes: Optional[str] = Field(None, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": 1,
                "doctor_name": "Dr. Sarah Smith",
                "consultation_type": "initial",
                "status": "scheduled",
                "notes": "Initial consultation for chronic condition"
            }
        }

class ConsultationResponse(BaseModel):
    consultation_id: int
    doctor_name: str
    status: str
    timestamp: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True
