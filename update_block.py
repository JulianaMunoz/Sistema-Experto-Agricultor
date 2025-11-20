from pathlib import Path
p = Path('backend/main.py')
lines = p.read_text(encoding='utf-8').splitlines()
start = None
for i, l in enumerate(lines):
    if l.strip().startswith('@app.get("/api/preguntas"'):
        start = i
        break
if start is None:
    raise SystemExit('start not found')
end = None
for i in range(start + 1, len(lines)):
    if lines[i].startswith('def evaluar_condicion'):
        end = i
        break
if end is None:
    raise SystemExit('end not found')
new_code = """@app.get('/api/preguntas')
def get_preguntas(altitud: str | None = None, db: Session = Depends(get_db)):
    """
    Flujo guiado:
    - Si no hay altitud seleccionada: solo pregunta "altitud".
    - Con altitud: filtra hechos que cumplen ese rango y arma preguntas
      para los factores presentes en esas reglas (clima, suelo, riego, etc.).
    """
    factors = db.query(Factor).order_by(Factor.id.asc()).all()
    alt_factor = next((f for f in factors if (f.nombre or '').lower() == 'altitud'), None)

    def build_altitude_question():
        if not alt_factor:
            return []
        fhs = (
            db.query(FactorHecho)
            .filter(FactorHecho.factor_id == alt_factor.id)
            .order_by(FactorHecho.id.asc())
            .all()
        )
        seen = set()
        options = []
        for fh in fhs:
            v_raw = (fh.valor or '').strip()
            if not v_raw:
                continue
            op = (fh.operador or '').strip() or '='
            value = v_raw if any(v_raw.startswith(prefix) for prefix in ('>=', '=>', '<=', '=<')) else v_raw
            if op in ('>=', '=>') and not value.startswith(('>=', '=>')):
                value = f'>={v_raw}'
            if op in ('<=', '=<') and not value.startswith(('<=', '=<')):
                value = f'<={v_raw}'
            if value in seen:
                continue
            seen.add(value)
            if '-' in v_raw:
                label = f"{v_raw} msnm"
            elif value.startswith('>=') or op in ('>=', '=>'):
                label = f">= {v_raw} msnm"
            elif value.startswith('<=') or op in ('<=', '=<'):
                label = f"<= {v_raw} msnm"
            else:
                label = f"{v_raw} msnm"
            options.append({'v': value, 't': label})
        return [{'id': 'altitud', 'text': alt_factor.nombre, 'options': options}] if options else []

    if not altitud:
        return build_altitude_question()

    hechos_validos = set()
    if alt_factor:
        alt_fhs = db.query(FactorHecho).filter(FactorHecho.factor_id == alt_factor.id).all()
        for fh in alt_fhs:
            if evaluar_condicion(fh.operador, fh.valor, altitud):
                hechos_validos.add(fh.hecho_id)
    if not hechos_validos:
        return build_altitude_question()

    factor_ids = [
        r[0]
        for r in db.query(FactorHecho.factor_id)
        .filter(FactorHecho.hecho_id.in_(hechos_validos))
        .filter(FactorHecho.factor_id != (alt_factor.id if alt_factor else None))
        .distinct()
        .all()
    ]
    orden_manual = [1, 5, 9, 8, 2, 7, 10, 11, 12, 13, 14, 15]
    factor_ids = sorted(factor_ids, key=lambda x: orden_manual.index(x) if x in orden_manual else x)

    fmap = {f.id: f for f in factors}
    preguntas = build_altitude_question()

    for fid in factor_ids:
        f = fmap.get(fid)
        if not f:
            continue
        fhs = (
            db.query(FactorHecho)
            .filter(FactorHecho.factor_id == f.id)
            .filter(FactorHecho.hecho_id.in_(hechos_validos))
            .order_by(FactorHecho.id.asc())
            .all()
        )
        if not fhs:
            continue
        seen = set()
        options = []
        fname = (f.nombre or '').lower()
        for fh in fhs:
            v_raw = (fh.valor or '').strip()
            if not v_raw:
                continue
            value = v_raw.lower()
            if value in seen:
                continue
            seen.add(value)
            options.append({'v': value, 't': v_raw})
        if options:
            preguntas.append({'id': fname, 'text': f.nombre or fname, 'options': options})

    return preguntas


def recomendar(respuestas: dict, db: Session = Depends(get_db)):
    """
    Calcula viabilidad: porcentaje de condiciones cumplidas por hecho.
    Devuelve ordenado desc por porcentaje.
    """
    resp = {k.lower(): (v or '').strip() for k, v in (respuestas or {}).items()}

    resultados = []
    hechos = db.query(Hecho).all()
    for hecho in hechos:
        condiciones = db.query(FactorHecho).filter(FactorHecho.hecho_id == hecho.id).all()
        if not condiciones:
            continue

        match = 0
        for c in condiciones:
            factor = db.query(Factor).filter(Factor.id == c.factor_id).first()
            fname = (factor.nombre or '').lower() if factor else None
            valor_usuario = resp.get(fname, '')
            if evaluar_condicion(c.operador, c.valor, valor_usuario):
                match += 1

        porcentaje = int(match * 100 / len(condiciones)) if condiciones else 0
        if porcentaje > 0:
            resultados.append({'descripcion': hecho.descripcion, 'porcentaje': porcentaje})

    resultados.sort(key=lambda x: x['porcentaje'], reverse=True)
    return {'count': len(resultados), 'recomendaciones': resultados if resultados else ['No hay recomendaciones para tu combinacion de respuestas.']}
"""
lines = lines[:start] + new_code.splitlines() + lines[end:]
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('updated block', start, end)
