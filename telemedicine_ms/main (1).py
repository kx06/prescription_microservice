import logging
import time
import uuid
import sys
from datetime import datetime
from threading import Thread
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fluent import sender
from app.models import Patient as PatientModel
from app.schemas import PatientCreate
from app.database import SessionLocal, engine
from app import models

# Generate unique node ID
NODE_ID = str(uuid.uuid4())
SERVICE_NAME = "TelemedicinePlatform"

# Configure Fluentd sender
fluent_sender = sender.FluentSender('telemedicine.service', host='localhost', port=24224)

class FluentdHandler(logging.Handler):
    def emit(self, record):
        try:
            data = {
                'message': self.format(record)
            }
           
            if record.exc_info:
                data['exc_info'] = self.formatter.formatException(record.exc_info)

            fluent_sender.emit(record.levelname.lower(), data)
        except Exception as e:
            print(f"Failed to send log to Fluentd: {e}", file=sys.stderr)

# Set up logging
logger = logging.getLogger('telemedicine')
logger.setLevel(logging.INFO)

# Remove existing handlers
for h in logger.handlers[:]:
    logger.removeHandler(h)

# Configure Fluentd handler
fluentd_handler = FluentdHandler()
formatter = logging.Formatter('%(message)s')
fluentd_handler.setFormatter(formatter)
logger.addHandler(fluentd_handler)

# Add console handler for debugging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(console_handler)

# Create database tables
models.Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="Telemedicine Platform API",
    description="API for managing telemedicine sessions and patient connections",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def send_heartbeat():
    while True:
        try:
            logger.info({
                "node_id": NODE_ID,
                "message_type": "HEARTBEAT",
                "status": "UP",
                "service_name": SERVICE_NAME,
                "timestamp": datetime.utcnow().isoformat()
            })
            time.sleep(60)
        except Exception as e:
            logger.error({
                "node_id": NODE_ID,
                "message_type": "LOG",
                "log_level": "ERROR",
                "service_name": SERVICE_NAME,
                "error_details": {
                    "error_code": "HEARTBEAT_ERROR",
                    "error_message": str(e)
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            time.sleep(60)

heartbeat_thread = Thread(target=send_heartbeat)
heartbeat_thread.daemon = True
heartbeat_thread.start()

@app.post("/patients/register")
async def register_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    try:
        # Since the schema is different, we'll create a patient with the available fields
        db_patient = PatientModel(name=patient.name, condition=patient.condition)
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
       
        logger.info({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "INFO",
            "message_type": "LOG",
            "message": f"New patient registered: {db_patient.id}",
            "service_name": SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat()
        })
        return {"message": "Patient registered successfully", "patient_id": db_patient.id}
    except Exception as e:
        logger.error({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "ERROR",
            "message_type": "LOG",
            "message": f"Error registering patient",
            "service_name": SERVICE_NAME,
            "error_details": {
                "error_code": "REG_ERROR",
                "error_message": str(e)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/session/connect/{patient_id}")
async def connect_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.id == patient_id).first()
    if not patient:
        logger.warning({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "WARN",
            "message_type": "LOG",
            "message": f"Patient not found during connection attempt: {patient_id}",
            "service_name": SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=404, detail="Patient not found")
   
    try:
        # Note: The current schema doesn't have a status field,
        # so we're simulating the connection logic
        logger.info({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "INFO",
            "message_type": "LOG",
            "message": f"Patient connected successfully: {patient_id}",
            "service_name": SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat()
        })
        return {"message": "Connected successfully"}
    except Exception as e:
        logger.error({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "ERROR",
            "message_type": "LOG",
            "message": f"Connection error for patient: {patient_id}",
            "service_name": SERVICE_NAME,
            "error_details": {
                "error_code": "CONN_ERROR",
                "error_message": str(e)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=500, detail="Connection failed")

@app.post("/session/disconnect/{patient_id}")
async def disconnect_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(PatientModel).filter(PatientModel.id == patient_id).first()
    if not patient:
        logger.warning({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "WARN",
            "message_type": "LOG",
            "message": f"Patient not found for disconnection: {patient_id}",
            "service_name": SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=404, detail="Patient not found")
   
    try:
        # Note: The current schema doesn't track session status directly,
        # so we're simulating the disconnection logic
        logger.info({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "INFO",
            "message_type": "LOG",
            "message": f"Patient disconnected: {patient_id}",
            "service_name": SERVICE_NAME,
            "timestamp": datetime.utcnow().isoformat()
        })
        return {"message": "Disconnected successfully"}
    except Exception as e:
        logger.error({
            "log_id": str(uuid.uuid4()),
            "node_id": NODE_ID,
            "log_level": "ERROR",
            "message_type": "LOG",
            "message": f"Disconnection error for patient: {patient_id}",
            "service_name": SERVICE_NAME,
            "error_details": {
                "error_code": "DISC_ERROR",
                "error_message": str(e)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=500, detail="Disconnection failed")

# Registration message on startup
logger.info({
    "node_id": NODE_ID,
    "message_type": "REGISTRATION",
    "service_name": SERVICE_NAME,
    "timestamp": datetime.utcnow().isoformat()
})