from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from patient_service import PatientService
from schemas import PatientCreate, PatientResponse
from database import get_db
from fluent import sender
from fluent import event
from datetime import datetime, timedelta
import asyncio
import logging
import uuid
import time

app = FastAPI()
FLUENTD_TAG = 'patient.service'
fluent_sender = sender.FluentSender(FLUENTD_TAG, host='localhost', port=24224)

class FluentdHandler(logging.Handler):
    def emit(self, record):
        try:
            data = {
                #'timestamp': datetime.utcnow().isoformat(),
                #'level': record.levelname,
                'message': self.format(record),
                #'module': record.module,
                #'filename': record.filename,
                #'lineno': record.lineno,
                #'funcName': record.funcName
            }
            
            if record.exc_info:
                data['exc_info'] = self.formatter.formatException(record.exc_info)

            fluent_sender.emit(record.levelname.lower(), data)
        except Exception as e:
            print(f"Failed to send log to Fluentd: {e}", file=sys.stderr)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

fluentd_handler = FluentdHandler()
formatter = logging.Formatter('%(message)s')
fluentd_handler.setFormatter(formatter)
logger.addHandler(fluentd_handler)

@app.post("/patient/add", response_model=PatientResponse)
async def add_patient(patient: PatientCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    patient_service = PatientService(db)
    start_time=time.time()
    try:
        existing_patient = patient_service.get_patient_by_id(patient.patient_id)
        if existing_patient:
            response_time_ms = (time.time() - start_time) * 1000 
            logger.warning({
                'log_id':str(uuid.uuid4()),
                'node_id':"node_1",
                'log-level':"WARN",
                "message_type":"LOG",              
                'message': f"Duplicate patient record detected for patient ID: {patient.patient_id}",
                'service_name':"patient",
                'response_time_ms':f"{response_time_ms:.2f}",
                'threshold_limit_ms':"20000",
                'timestamp':datetime.utcnow().isoformat()
            })
            raise HTTPException(status_code=400, detail="Patient already exists. Manual verification required.")
        
        new_patient = patient_service.add_patient(patient.patient_id, patient.patient_name, patient.medical_history)
        logger.info({
            "log_id": str(uuid.uuid4()),
            "node_id": "node_1",
            'log-level':"INFO",
            "message_type": "LOG",
            'message': f"New patient record created for {patient.patient_name}",
            "service_name": "patient",
            "timestamp": datetime.utcnow().isoformat()
        })
        return new_patient
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error({      
            "log_id": str(uuid.uuid4()),
            "node_id": "node_1",
            "log_level": "ERROR",
            "message_type": "LOG",
            'message': f"Error adding patient record for {patient.patient_name}",
            "service_name": "patient",
            "error_details": {
        	"error_code": "PTE01",
        	"error_message": "Error occured while adding patient to the database."
    	     },
    	     "timestamp": datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=500, detail="An error occurred while adding the patient.")

@app.put("/patient/update", response_model=PatientResponse)
async def update_patient(patient_id: str, medical_history: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    patient_service = PatientService(db)
    try:
        patient = patient_service.get_patient_by_id(patient_id)
        if not patient:
            logger.error({
            	'log-id':str(uuid.uuid4()),
            	'node-id':'node_1',
            	'log_level':"ERROR",
            	'message_type':"LOG",
                'message': f"Error updating code as Patient ID {patient_id} not in the database",
                "service_name":"patient",
                "error_details":{
                    "error_code":"PTE02",
                    "error_message":"Patient ID given is not found in database"
                },
                "timestamp":datetime.utcnow().isoformat()
            })
            raise HTTPException(status_code=404, detail="Patient with the given ID not found")
        updated_patient = patient_service.update_patient(patient_id, medical_history)
        logger.info({
            "log_id": str(uuid.uuid4()),
            "node_id": "node_1",
            'log-level':"INFO",
            "message_type": "LOG",
            'message': f"Medical history for patient ID {patient_id} updated successfully",
            "service_name": "patient",
            "timestamp": datetime.utcnow().isoformat()
        })
        return updated_patient
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating the patient.")

@app.delete("/patient/delete")
async def delete_patient(patient_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    patient_service = PatientService(db)
    start_time=time.time()
    response_time_ms = (time.time() - start_time) * 1000 
    logger.warning({
        'log_id':str(uuid.uuid4()),
        'node_id':"node_1",
        'log-level':"WARN",
        "message_type":"LOG",              
        'message': f"All details of patient with ID: {patient_id} will be deleted",
        'service_name':"patient",
        'response_time_ms':f"{response_time_ms:.2f}",
        'threshold_limit_ms':"20000",
        'timestamp':datetime.utcnow().isoformat()
    })
    try:
        patient_service.delete_patient(patient_id)
        logger.info({
            "log_id": str(uuid.uuid4()),
            "node_id": "node_1",
            'log-level':"INFO",
            "message_type": "LOG",
            'message': f"Deleted patient with ID {patient_id}",
            "service_name": "patient",
            "timestamp": datetime.utcnow().isoformat()
        })
        return {"message": f"Patient with ID {patient_id} deleted successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred while deleting the patient.")

@app.get("/")
async def home():
    logger.info({
        "log_id": str(uuid.uuid4()),
        "node_id": "node_1",
        'log-level':"INFO",
        "message_type": "LOG",
        'message': f"Welcome to patient DB",
        "service_name": "patient",
        "timestamp": datetime.utcnow().isoformat()
        })
    return {"message": f"Home page."}
   

@app.on_event("startup")
async def startup_event():
    logger.info({
	"node_id": "node_1",
	"message_type": "REGISTRATION",
    	"service_name": "patient",
    	"timestamp": datetime.utcnow().isoformat()
    })
    asyncio.create_task(send_heartbeat())

@app.on_event("shutdown")
async def on_shutdown():
    logger.info({
    	    "node_id": "node_1",
            "message_type": "HEARTBEAT",
     	    "status": "DOWN",
            "timestamp": datetime.utcnow().isoformat()
    })

async def send_heartbeat():
    while True:
        logger.info({
            "node_id": "node_1",
            "message_type": "HEARTBEAT",
            "status": "UP",
            "timestamp": datetime.utcnow().isoformat()
        })
        await asyncio.sleep(60) 

