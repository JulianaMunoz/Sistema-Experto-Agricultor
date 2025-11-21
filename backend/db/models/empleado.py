from sqlalchemy import Column, Integer, String, Boolean
from core.base_class import Base

class Empleado(Base):
    __tablename__ = "empleado"
    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    es_admin = Column(Boolean, default=True)
