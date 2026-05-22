"""Pydantic schemas."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict
import uuid


def _id():
    return str(uuid.uuid4())


def _now():
    return datetime.utcnow().isoformat()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Literal["superadmin", "admin", "docente", "viewer"] = "viewer"
    facultad_id: Optional[str] = None
    programa_id: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[Literal["superadmin", "admin", "docente", "viewer"]] = None
    facultad_id: Optional[str] = None
    programa_id: Optional[str] = None
    active: Optional[bool] = None


class UserOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: EmailStr
    full_name: str
    role: str
    facultad_id: Optional[str] = None
    programa_id: Optional[str] = None
    active: bool = True
    must_change_password: bool = False
    created_at: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class CatalogItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_id)
    nombre: str
    codigo: Optional[str] = None
    facultad_id: Optional[str] = None
    programa_id: Optional[str] = None
    created_at: str = Field(default_factory=_now)


class CatalogIn(BaseModel):
    nombre: str
    codigo: Optional[str] = None
    facultad_id: Optional[str] = None
    programa_id: Optional[str] = None


class DocenteMateriaIn(BaseModel):
    docente_id: str
    facultad_id: Optional[str] = None
    programa_id: Optional[str] = None
    materia_id: str
    periodo: str


class FiltersIn(BaseModel):
    periodo: Optional[str] = None
    facultad: Optional[str] = None
    programa: Optional[str] = None
    materia: Optional[str] = None
    genero: Optional[str] = None
    estrato: Optional[str] = None
    sisben: Optional[str] = None
    etnia: Optional[str] = None
    discapacidad: Optional[bool] = None
    victima: Optional[bool] = None
    grupo_vulnerable: Optional[bool] = None
    tipo_ubicacion: Optional[str] = None
    estado_matricula: Optional[str] = None
    municipio_codigo: Optional[str] = None


class AIInsightIn(BaseModel):
    scope: Literal["ejecutivo", "academico", "territorial", "historico"] = "ejecutivo"
    filters: Optional[FiltersIn] = None
    question: Optional[str] = None
