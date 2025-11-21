from fastapi import Depends, FastAPI, HTTPException, status, Request, Form, Body
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles  # ← AGREGAR ESTE IMPORT
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from typing import List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import psycopg2
from psycopg2 import OperationalError

import os
from pathlib import Path

# ---- Configuración base ----
from core.config import settings
from core.session import engine
from core.base_class import Base
from core.deps import get_db

# ---- Modelos ----
from db.models.factor import Factor
from db.models.hecho import Hecho
from db.models.factor_hecho import FactorHecho
from db.models.usuario import Usuario
from db.models.empleado import Empleado

# ---- Schemas ----
from db.schemas.empleado import EmpleadoRead, EmpleadoCreate
from db.schemas.factor import FactorCreate, FactorResponse
from db.schemas.hecho import HechoCreate, HechoResponse
from db.schemas.factor_hecho import FactorHechoCreate, FactorHechoResponse
from db.schemas.usuario import CrearUsuario, LeerUsuario, ActualizarUsuario


# ============================================================
#              INICIALIZACIÓN Y ARRANQUE DE APP
# ============================================================
def test_connection():
    print("🧠 Probando conexión a la base de datos...")
    print("🔗 URL:", repr(settings.DATABASE_URL))
    try:
        conn = psycopg2.connect(settings.DATABASE_URL, sslmode="require", connect_timeout=5)
        print("✅ Conexión exitosa a la base de datos!")
        conn.close()
    except OperationalError as e:
        print("❌ Error al conectar con la base de datos:")
        print(e)

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("🧱 Tablas creadas correctamente")

def start_application():
    app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
    test_connection()
    create_tables()
    return app

# Configuración de directorios
BASE_DIR = Path(__file__).resolve().parent.parent  
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"  # ← AGREGAR ESTA LÍNEA

app = start_application()
templates = Jinja2Templates(directory=str(FRONTEND_DIR))

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")  # ← AGREGAR ESTA LÍNEA

# ============================================================
#                     VISTAS HTML
# ============================================================
@app.get("/", response_model=None)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "title": "Sistema Experto para Asistencia en la Elección de Cultivos"}
    )

@app.get("/register", response_model=None)
def register_page(request: Request):
    return templates.TemplateResponse("usuarios/register.html", {"request": request, "title": "Crear cuenta"})

@app.get("/home", response_model=None)
def home_page(request: Request):
    return templates.TemplateResponse("usuarios/home_users.html", {"request": request, "title": "Inicio"})

@app.get("/vista/recomendaciones", response_model=None)
def vista_recomendaciones(request: Request):
    return templates.TemplateResponse("usuarios/recomendaciones.html", {"request": request, "title": "Recomendaciones"})

@app.get("/vista/reglas", response_model=None)
def vista_reglas(request: Request):
    return templates.TemplateResponse("administradores/consultar_reglas.html", {"request": request, "title": "Reglas"})

@app.get("/admin", response_model=None)
def admin_page(request: Request):
    return templates.TemplateResponse("administradores/home_admins.html", {"request": request, "title": "Admin"})

@app.get("/admin/consulReglas", response_model=None)
def admin_consul_reglas_page(request: Request):
    return templates.TemplateResponse("administradores/consultar_reglas.html", {"request": request, "title": "Consultar Reglas"})

# ============================================================
#                     ENDPOINTS DE NEGOCIO
# ============================================================
@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"ok": True, "db": "up"}

# ---------- FACTORES ----------
@app.post("/factores/", response_model=FactorResponse)
def create_factor(factor: FactorCreate, db: Session = Depends(get_db)):
    new_factor = Factor(nombre=factor.nombre, categoria=factor.categoria)
    db.add(new_factor)
    db.commit()
    db.refresh(new_factor)
    return new_factor

#consulta de todos los factores
@app.get("/factores/")
def list_factores(db: Session = Depends(get_db)):
    factores = db.query(Factor).order_by(Factor.id.asc()).all()
    return [{"id": f.id, "nombre": (f.nombre or "").lower()} for f in factores]

#consulta de un solo factor
@app.get("/factores/{factor_id}", response_model=FactorResponse)
def get_factor(factor_id: int, db: Session = Depends(get_db)):
    factor = db.query(Factor).filter(Factor.id == factor_id).first()
    if not factor:
        raise HTTPException(status_code=404, detail="Factor no encontrado")
    return factor

#Creando Hechos
# ---------- HECHOS ----------
@app.post("/hechos/", response_model=HechoResponse)
def create_hecho(hecho: HechoCreate, db: Session = Depends(get_db)):
    new_hecho = Hecho(descripcion=hecho.descripcion)
    db.add(new_hecho)
    db.commit()
    db.refresh(new_hecho)
    return new_hecho

#consulta de todos los hechos
@app.get("/hechos/", response_model=List[HechoResponse])
def get_hechos(db: Session = Depends(get_db)):
    hechos = db.query(Hecho).all()
    return hechos

#consulta de un solo hecho
@app.get("/hechos/{hecho_id}", response_model=HechoResponse)
def get_hecho(hecho_id: int, db: Session = Depends(get_db)):
    hecho = db.query(Hecho).filter(Hecho.id == hecho_id).first()
    if not hecho:
        raise HTTPException(status_code=404, detail="Hecho no encontrado")
    return hecho

#Creando Reglas
# ---------- FACTOR-HECHO ----------
@app.post("/reglas/", response_model=FactorHechoResponse)
def create_regla(fh: FactorHechoCreate, db: Session = Depends(get_db)):
    new_regla = FactorHecho(
        factor_id=fh.factor_id, hecho_id=fh.hecho_id, operador=fh.operador, valor=fh.valor
    )
    db.add(new_regla)
    db.commit()
    db.refresh(new_regla)
    return new_regla

#consulta de todas las reglas
@app.get("/reglas/")
def list_reglas(db: Session = Depends(get_db)):
    reglas = db.query(FactorHecho).order_by(FactorHecho.id.asc()).all()
    return [
        {"id": r.id, "factor_id": r.factor_id, "hecho_id": r.hecho_id, "operador": r.operador, "valor": r.valor}
        for r in reglas
    ]

#consulta una sola regla
@app.get("/reglas/{regla_id}", response_model=FactorHechoResponse)
def get_regla(regla_id: int, db: Session = Depends(get_db)):
    regla = db.query(FactorHecho).filter(FactorHecho.id == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return regla
@app.put("/reglas/{regla_id}", response_model=FactorHechoResponse)
def update_regla(regla_id: int, fh: FactorHechoCreate, db: Session = Depends(get_db)):
    regla = db.query(FactorHecho).filter(FactorHecho.id == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    regla.factor_id = fh.factor_id
    regla.hecho_id = fh.hecho_id
    regla.operador = fh.operador
    regla.valor = fh.valor
    db.commit()
    db.refresh(regla)
    return regla
@app.delete("/reglas/{regla_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_regla(regla_id: int, db: Session = Depends(get_db)): 
    regla = db.query(FactorHecho).filter(FactorHecho.id == regla_id).first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    db.delete(regla)
    db.commit()
    return None

# -------------------- GESTIÓN DE USUARIOS --------------------
# Configuración de contraseñas (bcrypt con fallback)

# ============================================================
#            NUEVA RUTA: FACTORES + VALORES (hechos)
# ============================================================
@app.get("/factors-values")
def get_factors_values(db: Session = Depends(get_db)):
    """
    Devuelve [{nombre: "clima", valores: ["húmedo", "seco", ...]}, ...]
    Extrae valores únicos de FactorHecho para cada Factor.
    """
    factors = db.query(Factor).order_by(Factor.nombre.asc()).all()
    
    result = []
    for factor in factors:
        # Obtener valores únicos para este factor
        valores = db.query(FactorHecho.valor).filter(
            FactorHecho.factor_id == factor.id
        ).distinct().all()
        
        # Normalizar: valores es lista de tuplas, extraer strings
        valores_list = [v[0] for v in valores if v[0]]  # Filtrar None/vacíos
        
        result.append({
            "nombre": factor.nombre.lower(),
            "valores": valores_list
        })
    
    return result


# ============================================================
#              AUTENTICACIÓN Y GESTIÓN DE USUARIOS
# ============================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
try:
    _ = pwd_context.hash("probe")
except Exception as e:
    print("⚠️ bcrypt falló, usando sha256_crypt:", repr(e))
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def create_user_core(payload: CrearUsuario, db: Session) -> Usuario:
    exists = db.query(Usuario).filter(
        (Usuario.email == payload.email) | (Usuario.name == payload.name)
    ).first()
    if exists:
        raise HTTPException(status_code=400, detail="Usuario ya existe (email o name)")

    user = Usuario(
        name=payload.name,
        email=payload.email,
        password=get_password_hash(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/users", response_model=LeerUsuario, status_code=status.HTTP_201_CREATED)
def create_user(payload: CrearUsuario, db: Session = Depends(get_db)):
    try:
        return create_user_core(payload, db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Violación de integridad (duplicado).")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error de base de datos.")


@app.post("/users-form", response_model=LeerUsuario, status_code=status.HTTP_201_CREATED)
def create_user_form(
    name: str = Form(...),
    email: EmailStr = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        payload = CrearUsuario(name=name, email=email, password=password)
        return create_user_core(payload, db)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Violación de integridad (duplicado).")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error de base de datos.")


@app.post("/login", response_model=LeerUsuario)
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    return user


@app.patch("/users/{user_id}", response_model=LeerUsuario)
def update_user(user_id: int, payload: ActualizarUsuario, db: Session = Depends(get_db)):
    user = db.query(Usuario).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if payload.email and db.query(Usuario).filter(Usuario.email == payload.email, Usuario.id != user_id).first():
        raise HTTPException(status_code=400, detail="Email ya en uso")

    if payload.name and db.query(Usuario).filter(Usuario.name == payload.name, Usuario.id != user_id).first():
        raise HTTPException(status_code=400, detail="Nombre ya en uso")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password = get_password_hash(payload.password)

    db.commit()
    db.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(Usuario).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()
    return None
@app.post("/empleados", response_model=EmpleadoRead, status_code=status.HTTP_201_CREATED)
def create_empleado(payload: EmpleadoCreate, db: Session = Depends(get_db)):
    exists = db.query(Empleado).filter(Empleado.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Empleado ya existe (email)")

    emp = Empleado(
        nombre=payload.nombre,
        email=payload.email,
        password=get_password_hash(payload.password),
        es_admin=payload.es_admin if payload.es_admin is not None else True,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

@app.post("/empleado/login", response_model=EmpleadoRead)
def login_empleado(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    emp = db.query(Empleado).filter(Empleado.email == email).first()
    if not emp or not verify_password(password, emp.password):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return emp


@app.get("/api/preguntas")
def get_preguntas(altitud: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Provee el flujo de preguntas ordenado: primero altitud, luego factores compatibles.
    Solo pregunta altitud, clima y suelo en ese orden.
    - Sin altitud => solo pregunta inicial.
    - Con altitud => factores de los hechos que cumplen esa condicion.
    """
    factors = db.query(Factor).order_by(Factor.id.asc()).all()
    name_map = {(f.nombre or "").lower(): f for f in factors}
    alt_factor = name_map.get("altitud")
    clima_factor = name_map.get("clima")
    suelo_factor = name_map.get("suelo")

    def build_altitud_question() -> List[dict]:
        if not alt_factor:
            return []
        registros = (
            db.query(FactorHecho)
            .filter(FactorHecho.factor_id == alt_factor.id)
            .order_by(FactorHecho.id.asc())
            .all()
        )
        seen = set()
        options = []
        for row in registros:
            raw_value = (row.valor or "").strip()
            if not raw_value:
                continue
            op = (row.operador or "").strip() or "="
            normalized = raw_value if any(raw_value.startswith(prefix) for prefix in (">=", "=>", "<=", "=<")) else raw_value
            if op in (">=", "=>") and not normalized.startswith((">=", "=>")):
                normalized = f">={raw_value}"
            if op in ("<=", "=<") and not normalized.startswith(("<=", "=<")):
                normalized = f"<={raw_value}"
            if normalized in seen:
                continue
            seen.add(normalized)

            if "-" in raw_value:
                label = f"{raw_value} msnm"
            elif normalized.startswith(">=") or op in (">=", "=>"):
                label = f">= {raw_value} msnm"
            elif normalized.startswith("<=") or op in ("<=", "=<"):
                label = f"<= {raw_value} msnm"
            else:
                label = f"{raw_value} msnm"
            options.append({"v": normalized, "t": label})

        if not options:
            return []
        return [{"id": "altitud", "text": alt_factor.nombre or "Altitud", "options": options}]

    preguntas = build_altitud_question()
    if not altitud or not alt_factor:
        return preguntas

    hechos_validos = set()
    alt_rules = db.query(FactorHecho).filter(FactorHecho.factor_id == alt_factor.id).all()
    for rule in alt_rules:
        if evaluar_condicion(rule.operador, rule.valor, altitud):
            hechos_validos.add(rule.hecho_id)

    if not hechos_validos:
        return preguntas

    ordered_factors = [f for f in (clima_factor, suelo_factor) if f]

    factor_lookup = {f.id: f for f in factors}
    for factor in ordered_factors:
        if not factor:
            continue
        registros = (
            db.query(FactorHecho)
            .filter(FactorHecho.factor_id == factor.id)
            .filter(FactorHecho.hecho_id.in_(hechos_validos))
            .order_by(FactorHecho.id.asc())
            .all()
        )
        nombre_factor = (factor.nombre or "").lower()
        opciones = []
        vistos = set()
        for row in registros:
            valor = (row.valor or "").strip()
            if not valor:
                continue
            normalized = valor.lower()
            if normalized in vistos:
                continue
            vistos.add(normalized)
            opciones.append({"v": normalized, "t": valor})

        # si hay pocas opciones por el filtro, agregar valores de todas las reglas de ese factor
        if len(opciones) < 2:
            extra_vals = (
                db.query(FactorHecho.valor)
                .filter(FactorHecho.factor_id == factor.id)
                .distinct()
                .all()
            )
            for (val_extra,) in extra_vals:
                v = (val_extra or "").strip()
                if not v:
                    continue
                norm = v.lower()
                if norm in vistos:
                    continue
                vistos.add(norm)
                opciones.append({"v": norm, "t": v})

        if opciones:
            opciones = sorted(opciones, key=lambda o: (o.get("t") or o.get("v") or "").lower())
            preguntas.append({
                "id": nombre_factor,
                "text": factor.nombre or nombre_factor,
                "options": opciones,
            })

    return preguntas


def recomendar(respuestas: dict, db: Session = Depends(get_db)):
    """Calcula porcentaje de viabilidad por hecho."""
    resp = {k.lower(): (v or "").strip() for k, v in (respuestas or {}).items()}
    resultados = []
    hechos = db.query(Hecho).all()
    for hecho in hechos:
        condiciones = db.query(FactorHecho).filter(FactorHecho.hecho_id == hecho.id).all()
        if not condiciones:
            continue
        cumplidas = 0
        for condicion in condiciones:
            factor = db.query(Factor).filter(Factor.id == condicion.factor_id).first()
            fname = (factor.nombre or "").lower() if factor else None
            if not fname:
                continue
            valor_usuario = resp.get(fname, "")
            if evaluar_condicion(condicion.operador, condicion.valor, valor_usuario):
                cumplidas += 1
        porcentaje = int((cumplidas * 100) / len(condiciones)) if condiciones else 0
        if porcentaje > 0:
            resultados.append({"descripcion": hecho.descripcion, "porcentaje": porcentaje})

    resultados.sort(key=lambda x: x["porcentaje"], reverse=True)
    if resultados:
        top = resultados[:5]  # mostrar solo las 5 mejores
        return {"count": len(top), "recomendaciones": top}
    return {"count": 0, "recomendaciones": [], "message": "No hay recomendaciones para tu combinacion de respuestas."}


@app.post("/api/recomendar")
def recomendar_endpoint(respuestas: dict = Body(...), db: Session = Depends(get_db)):
    return recomendar(respuestas, db)


@app.post("/api/pregunta-siguiente")
def pregunta_siguiente(respuestas: dict = Body(...), db: Session = Depends(get_db)):
    """
    Devuelve solo la siguiente pregunta necesaria, filtrando factores
    por los hechos que aun son compatibles con las respuestas actuales.
    Solo considera altitud, clima y suelo en ese orden.
    """
    resp = {k.lower(): (v or "").strip() for k, v in (respuestas or {}).items()}
    factors = db.query(Factor).order_by(Factor.id.asc()).all()
    name_map = {(f.nombre or "").lower(): f for f in factors}
    factor_lookup = {f.id: f for f in factors}
    alt_factor = name_map.get("altitud")
    allowed = [alt_factor, name_map.get("clima"), name_map.get("suelo")]

    def build_altitud_question():
        if not alt_factor:
            return None
        registros = (
            db.query(FactorHecho)
            .filter(FactorHecho.factor_id == alt_factor.id)
            .order_by(FactorHecho.id.asc())
            .all()
        )
        seen = set()
        options = []
        for row in registros:
            raw_value = (row.valor or "").strip()
            if not raw_value:
                continue
            op = (row.operador or "").strip() or "="
            normalized = raw_value if any(raw_value.startswith(prefix) for prefix in (">=", "=>", "<=", "=<")) else raw_value
            if op in (">=", "=>") and not normalized.startswith((">=", "=>")):
                normalized = f">={raw_value}"
            if op in ("<=", "=<") and not normalized.startswith(("<=", "=<")):
                normalized = f"<={raw_value}"
            if normalized in seen:
                continue
            seen.add(normalized)

            if "-" in raw_value:
                label = f"{raw_value} msnm"
            elif normalized.startswith(">=") or op in (">=", "=>"):
                label = f">= {raw_value} msnm"
            elif normalized.startswith("<=") or op in ("<=", "=<"):
                label = f"<= {raw_value} msnm"
            else:
                label = f"{raw_value} msnm"
            options.append({"v": normalized, "t": label})

        if not options:
            return None
        return {"id": "altitud", "text": alt_factor.nombre or "Altitud", "options": options}

    if not resp.get("altitud"):
        alt_q = build_altitud_question()
        return {"pregunta": alt_q, "pendientes": 1 if alt_q else 0}

    hechos = db.query(Hecho).all()
    hechos_candidatos = []
    for hecho in hechos:
        condiciones = db.query(FactorHecho).filter(FactorHecho.hecho_id == hecho.id).all()
        cumple = True
        for cond in condiciones:
            factor = factor_lookup.get(cond.factor_id)
            fname = (factor.nombre or "").lower() if factor else None
            if fname and fname in resp:
                if not evaluar_condicion(cond.operador, cond.valor, resp[fname]):
                    cumple = False
                    break
        if cumple:
            hechos_candidatos.append(hecho.id)

    if not hechos_candidatos:
        return {"pregunta": None, "pendientes": 0, "message": "No quedan hechos compatibles con tus respuestas."}

    pendientes = []
    for f in allowed:
        if not f or f == alt_factor:
            continue
        fname = (f.nombre or "").lower()
        if fname not in resp:
            pendientes.append(f)
    if not pendientes:
        return {"pregunta": None, "pendientes": 0}

    factor = pendientes[0]
    registros = (
        db.query(FactorHecho.valor)
        .filter(FactorHecho.factor_id == factor.id)
        .filter(FactorHecho.hecho_id.in_(hechos_candidatos))
        .distinct()
        .all()
    )
    options = []
    seen = set()
    for (valor,) in registros:
        val = (valor or "").strip()
        if not val:
            continue
        norm = val.lower()
        if norm in seen:
            continue
        seen.add(norm)
        options.append({"v": norm, "t": val})

    if len(options) < 2:
        extra_registros = (
            db.query(FactorHecho.valor)
            .filter(FactorHecho.factor_id == factor.id)
            .distinct()
            .all()
        )
        for (valor,) in extra_registros:
            val = (valor or "").strip()
            if not val:
                continue
            norm = val.lower()
            if norm in seen:
                continue
            seen.add(norm)
            options.append({"v": norm, "t": val})

    options = sorted(options, key=lambda o: (o.get("t") or o.get("v") or "").lower())
    if not options:
        return {"pregunta": None, "pendientes": 0}

    nombre_factor = (factor.nombre or "").lower()
    return {
        "pregunta": {"id": nombre_factor, "text": factor.nombre or nombre_factor, "options": options},
        "pendientes": len(pendientes),
    }

def evaluar_condicion(operador, valor_regla, valor_respuesta):
    """
    Evalua si la respuesta del usuario coincide con la condicion de la regla.
    Soporta '=' y comparadores numericos '<=' '>=' y rangos tipo '1000-2000' o '>=3000'.
    """
    if not valor_respuesta:
        return False

    val_resp = str(valor_respuesta).strip().lower()
    val_regla = str(valor_regla).strip().lower()
    op = (operador or "").strip() or "="

    # igualdad textual (incluye rangos exactos)
    if op in ("=", "==") and not val_regla.startswith((">=", "=>", "<=", "=<")) and "-" not in val_regla:
        return val_resp == val_regla

    try:
        # regla como rango "a-b"
        if "-" in val_regla:
            parts_regla = [int("".join(ch for ch in p if ch.isdigit())) for p in val_regla.split("-") if any(ch.isdigit() for ch in p)]
            if len(parts_regla) == 2:
                low_r, high_r = parts_regla
                if "-" in val_resp:
                    parts_resp = [int("".join(ch for ch in p if ch.isdigit())) for p in val_resp.split("-") if any(ch.isdigit() for ch in p)]
                    if len(parts_resp) == 2:
                        low_u, high_u = parts_resp
                        return low_u >= low_r and high_u <= high_r
                if val_resp.isdigit():
                    num_resp = int(val_resp)
                    return low_r <= num_resp <= high_r
                if val_resp.startswith(">=") or val_resp.startswith("=>"):
                    num_resp = int("".join(ch for ch in val_resp if ch.isdigit()))
                    return num_resp >= low_r
                if val_resp.startswith("<=") or val_resp.startswith("=<"):
                    num_resp = int("".join(ch for ch in val_resp if ch.isdigit()))
                    return num_resp <= high_r

        # regla >=X (por valor o por operador)
        if val_regla.startswith(">=") or val_regla.startswith("=>") or op in (">=", "=>"):
            num_regla = int("".join(ch for ch in val_regla if ch.isdigit())) if any(ch.isdigit() for ch in val_regla) else None
            if num_regla is not None:
                if val_resp.isdigit():
                    return int(val_resp) >= num_regla
                if val_resp.startswith(">=") or val_resp.startswith("=>"):
                    return int("".join(ch for ch in val_resp if ch.isdigit())) >= num_regla
                if "-" in val_resp:
                    parts_resp = [int("".join(ch for ch in p if ch.isdigit())) for p in val_resp.split("-") if any(ch.isdigit() for ch in p)]
                    if len(parts_resp) == 2:
                        low_u, _ = parts_resp
                        return low_u >= num_regla

        # regla <=X
        if val_regla.startswith("<=") or val_regla.startswith("=<") or op in ("<=", "=<"):
            num_regla = int("".join(ch for ch in val_regla if ch.isdigit())) if any(ch.isdigit() for ch in val_regla) else None
            if num_regla is not None:
                if val_resp.isdigit():
                    return int(val_resp) <= num_regla
                if val_resp.startswith("<=") or val_resp.startswith("=<"):
                    return int("".join(ch for ch in val_resp if ch.isdigit())) <= num_regla
                if "-" in val_resp:
                    parts_resp = [int("".join(ch for ch in p if ch.isdigit())) for p in val_resp.split("-") if any(ch.isdigit() for ch in p)]
                    if len(parts_resp) == 2:
                        _, high_u = parts_resp
                        return high_u <= num_regla

        # ultima opcion: comparar texto
        return val_resp == val_regla
    except Exception:
        return False