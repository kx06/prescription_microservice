from sqlalchemy import Column, Integer, String
from database import Base

# PRNO, PTID, PRNAME, DOSAGE

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    billno = Column(Integer)
    prno = Column(Integer)
    ptid = Column(Integer)
    prname = Column(String)
    dosage = Column(Integer)

    def __repr__(self):
        return 'UserModel(id=%s, billno=%s prno=%s, ptid=%s, prname=%s, dosage=%s)' % (self.id, self.billno, self.prno, self.ptid, self.prname, self.dosage)
