from fastapi import Depends, FastAPI, HTTPException, status, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import EmailStr
from typing import List
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import psycopg2
from psycopg2 import OperationalError

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

# ---- Schemas ----
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

app = start_application()
templates = Jinja2Templates(directory="../templates")


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
    return templates.TemplateResponse("register.html", {"request": request, "title": "Crear cuenta"})

@app.get("/home", response_model=None)
def home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "title": "Inicio"})

@app.get("/vista/recomendaciones", response_model=None)
def vista_recomendaciones(request: Request):
    return templates.TemplateResponse("recomendaciones.html", {"request": request, "title": "Recomendaciones"})

@app.get("/vista/reglas", response_model=None)
def vista_recomendaciones(request: Request):
    return templates.TemplateResponse("reglas.html", {"request": request, "title": "Reglas"})


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

@app.get("/api/preguntas")
def get_preguntas(db: Session = Depends(get_db)):
    """
    Devuelve preguntas ordenadas empezando por 'altitud' y luego por
    aparición en las reglas (FactorHecho). Para 'altitud' incluye operador+valor.
    Estructura devuelta: [{id, text, options: [{v,t}, ...]}, ...]
    """
    #vfvgvgvgvgvgvS
    # traer todos los factores, pero forzar altitud al inicio si existe
    factors = db.query(Factor).order_by(Factor.id.asc()).all()
    # buscar factor 'altitud' (case-insensitive)
    alt_factor = next((f for f in factors if (f.nombre or "").lower() == "altitud"), None)
    ordered = []
    if alt_factor:
        ordered.append(alt_factor)
    # ahora ordenar los restantes según la primera aparición en FactorHecho (min id)
    first = (
        db.query(FactorHecho.factor_id, func.min(FactorHecho.id).label("minid"))
        .group_by(FactorHecho.factor_id)
        .order_by("minid")
        .all()
    )
    order_ids = [r.factor_id for r in first if r.factor_id != (alt_factor.id if alt_factor else None)]
    fmap = {f.id: f for f in factors}
    ordered += [fmap[i] for i in order_ids if i in fmap and fmap[i] not in ordered]
    # añadir los que no aparecen en reglas
    ordered += [f for f in factors if f not in ordered]

    preguntas = []
    for f in ordered:
        fhs = (
            db.query(FactorHecho)
            .filter(FactorHecho.factor_id == f.id)
            .order_by(FactorHecho.id.asc())
            .all()
        )
        seen = set()
        options = []
        fname = (f.nombre or "").lower()

        for fh in fhs:
            v_raw = (fh.valor or "").strip()
            if not v_raw:
                continue

            # altitud: construir valor con operador para que frontend lo use (ej. "<=1000")
            if fname == "altitud":
                op = (fh.operador or "").strip()
                value = f"{op}{v_raw}"
                if value in seen:
                    continue
                seen.add(value)

                # etiqueta legible
                if op in ("<=", "=<"):
                    label = f"≤ {v_raw} msnm"
                elif op in (">=", "=>"):
                    label = f"≥ {v_raw} msnm"
                elif op == "=":
                    label = f"{v_raw} msnm"
                else:
                    label = f"{op} {v_raw}".strip()
                options.append({"v": value, "t": label})
            else:
                value = v_raw.lower()
                if value in seen:
                    continue
                seen.add(value)
                options.append({"v": value, "t": v_raw})

        preguntas.append({"id": fname, "text": f.nombre or fname, "options": options})

    return preguntas

@app.post("/api/recomendar")
def recomendar(respuestas: dict, db: Session = Depends(get_db)):
    """
    Evalúa dinámicamente las reglas: para cada Hecho, verifica que todas las condiciones
    (FactorHecho) asociadas se cumplan con las respuestas del usuario.
    Devuelve la lista de hecho.descripcion que cumplen todas sus condiciones.
    """
    # normalizar respuestas: claves en minúscula y strip
    resp = {k.lower(): (v or "").strip() for k, v in (respuestas or {}).items()}

    recomendaciones = []
    hechos = db.query(Hecho).all()
    for hecho in hechos:
        condiciones = db.query(FactorHecho).filter(FactorHecho.hecho_id == hecho.id).all()
        if not condiciones:
            continue

        todas = True
        for c in condiciones:
            # obtener nombre del factor asociado
            factor = db.query(Factor).filter(Factor.id == c.factor_id).first()
            fname = (factor.nombre or "").lower() if factor else None
            valor_usuario = resp.get(fname, "")
            if not evaluar_condicion(c.operador, c.valor, valor_usuario):
                todas = False
                break
        if todas:
            recomendaciones.append(hecho.descripcion)

    recomendaciones = list(dict.fromkeys(recomendaciones))

    return {
        "count": len(recomendaciones),
        "recomendaciones": recomendaciones if recomendaciones else ["No hay recomendaciones para tu combinación de respuestas."]
    }

def evaluar_condicion(operador, valor_regla, valor_respuesta):
    """
    Evalúa si la respuesta del usuario coincide con la condición de la regla.
    Soporta '=' y comparadores numéricos '<=' '>='.
    """
    if not valor_respuesta:
        return False

    val_resp = str(valor_respuesta).strip().lower()
    val_regla = str(valor_regla).strip().lower()
    op = (operador or "").strip()

    # igualdad textual
    if op in ("=", "=="):
        return val_resp == val_regla

    # comparadores numéricos (usualmente para altitud)
    try:
        # intentar extraer número de la regla
        num_regla = int(''.join(ch for ch in val_regla if ch.isdigit()))
    except Exception:
        num_regla = None

    # normalizar respuesta numérica si viene como "<=1000" o "1000-2000" o "1000"
    try:
        if val_resp.startswith("<=") or val_resp.startswith("=<"):
            num_resp = int(''.join(ch for ch in val_resp if ch.isdigit()))
            if op in ("<=", "=<"):
                return num_resp <= (num_regla if num_regla is not None else num_resp)
            if op in (">=", "=>"):
                return num_resp >= (num_regla if num_regla is not None else num_resp)
        if val_resp.startswith(">=") or val_resp.startswith("=>"):
            num_resp = int(''.join(ch for ch in val_resp if ch.isdigit()))
            if op in (">=", "=>"):
                return num_resp >= (num_regla if num_regla is not None else num_resp)
            if op in ("<=", "=<"):
                return num_resp <= (num_regla if num_regla is not None else num_resp)

        # si respuesta es rango "1000-2000", tratar como rango
        if "-" in val_resp:
            parts = [int(''.join(ch for ch in p if ch.isdigit())) for p in val_resp.split("-") if any(ch.isdigit() for ch in p)]
            if len(parts) == 2 and num_regla is not None:
                low, high = parts
                if op in ("<=", "=<"):
                    # regla p.e. <=1000: verdadero si upper bound <= regla
                    return high <= num_regla
                if op in (">=", "=>"):
                    return low >= num_regla

        # si la regla es numérica y la respuesta es número simple
        if val_resp.isdigit() and num_regla is not None:
            num_resp = int(val_resp)
            if op in ("<=", "=<"):
                return num_resp <= num_regla
            if op in (">=", "=>"):
                return num_resp >= num_regla
    except Exception:
        pass

    # fallback: comparación textual exacta
    return val_resp == val_regla
