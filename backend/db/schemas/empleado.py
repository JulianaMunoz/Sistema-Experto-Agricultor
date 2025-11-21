from pydantic import BaseModel, EmailStr, ConfigDict

class EmpleadoCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    es_admin: bool = True  # opcional, por defecto admin

class EmpleadoRead(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    es_admin: bool = True
    model_config = ConfigDict(from_attributes=True)

    class Config:
        orm_mode = True
