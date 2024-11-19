from pydantic import BaseModel


class PrescriptionSchema(BaseModel):
    id: int
    billno: int
    prno: int
    ptid: int 
    prname: str
    dosage: int 
