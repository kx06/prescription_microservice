from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from models import Base, Prescription
from schemas import PrescriptionSchema
from database import engine, SessionLocal
from fluent import sender
from fluent import event
from datetime import datetime, timedelta
import asyncio
import logging
import uuid


app = FastAPI()


FLUENTD_TAG = 'prescription.service'
fluent_sender = sender.FluentSender(FLUENTD_TAG, host='localhost', port=24224)


class FluentdHandler(logging.Handler):
    def emit(self, record):
        try:
            data = {
                'message': self.format(record),
            }
            
            if record.exc_info:
                data['error_details'] = {
                    'error_code': 'PR01',
                    'error_message': str(record.exc_info[1])
                }

            fluent_sender.emit(record.levelname.lower(), data)
        except Exception as e:
            print(f"Failed to send log to Fluentd: {e}", file=sys.stderr)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

fluentd_handler = FluentdHandler()
formatter = logging.Formatter('%(message)s')
fluentd_handler.setFormatter(formatter)
logger.addHandler(fluentd_handler)

def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db
    finally:
        if db is not None:
            db.close()

prIntr = {
    115: [120, 135],
    120: [115],
    135: [115]
}

@app.post("/api/add_prescription", response_model=PrescriptionSchema)
async def add_prescription(request: PrescriptionSchema, db: Session = Depends(get_db)):
    start_time = datetime.now()
    
    existing_prescriptions = db.query(Prescription).filter(Prescription.billno == request.billno).all()
    if existing_prescriptions:
        for prescription in existing_prescriptions:
            if prescription.prno != request.prno:
                if request.prno in prIntr.get(prescription.prno, []) or prescription.prno in prIntr.get(request.prno, []):
                    logger.warning({
                        'log_id': str(uuid.uuid4()),
                        'node_id': 'node_2',
                        'log_level': 'WARN',
                        'message_type': 'LOG',
                        'message': "Possible drug interaction detected.",
                        'service_name': 'prescription_service',
                        'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                        'threshold_limit_ms': 3600000,  # 1 hour
                        'timestamp': datetime.utcnow().isoformat()
                    })

    if request.dosage > 100:
        logger.error({
            'log_id': str(uuid.uuid4()),
            'node_id': 'node_2',
            'log_level': 'ERROR',
            'message_type': 'LOG',
            'message': "Invalid dosage detected. Prescription not saved.",
            'service_name': 'prescription_service',
            'error_details': {
                'error_code': 'PR01',
                'error_message': 'Invalid dosage'
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        raise HTTPException(status_code=400, detail="Invalid dosage.")

    # Save the prescription
    prescription = Prescription(billno=request.billno, prno=request.prno, ptid=request.ptid, prname=request.prname, dosage=request.dosage)
    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    logger.info({
        'log_id': str(uuid.uuid4()),
        'node_id': 'node_2',
        'log_level': 'INFO',
        'message_type': 'LOG',
        'message': "Prescription successfully created.",
        'service_name': 'prescription_service',
        'timestamp': datetime.utcnow().isoformat()
    })

    return prescription

@app.get("/api/prescriptions/{ptid}", response_model=list[PrescriptionSchema])
def get_prescriptions_by_ptid(ptid: int, db: Session = Depends(get_db)):
    start_time = datetime.now()
    prescriptions = db.query(Prescription).filter(Prescription.ptid == ptid).all()
    if not prescriptions:
        raise HTTPException(status_code=404, detail=f"No prescriptions found for PTID {ptid}")
    
    logger.info({
        'log_id': str(uuid.uuid4()),
        'node_id': 'node_2',
        'log_level': 'INFO',
        'message_type': 'LOG',
        'message': f"Retrieved prescriptions for PTID {ptid}.",
        'service_name': 'prescription_service',
        'timestamp': datetime.utcnow().isoformat()
    })
    
    return prescriptions

last_heartbeat_time = datetime.utcnow()

@app.on_event("startup")
async def startup_event():
    logger.info({
        'node_id': 'node_2',
        'message_type': 'REGISTRATION',
        'service_name': 'prescription_service',
        'timestamp': datetime.utcnow().isoformat()
    })
    asyncio.create_task(send_heartbeat())

@app.on_event("shutdown")
async def on_shutdown():
        logger.info({
            'node_id': 'node_2',
            'message_type': 'HEARTBEAT',
            'status': 'DOWN',
            'timestamp': datetime.utcnow().isoformat()
        })

async def send_heartbeat():
    """Send periodic heartbeats every 60 seconds."""
    global last_heartbeat_time
    while True:
        logger.info({
            'node_id': 'node_2',
            'message_type': 'HEARTBEAT',
            'status': 'UP',
            'timestamp': datetime.utcnow().isoformat()
        })
        last_heartbeat_time = datetime.utcnow()
        await asyncio.sleep(60)
