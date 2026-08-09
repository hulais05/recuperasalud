"""
Clasificador de motivos de débito.

Dos motores:
  - REGLAS: patrones sobre el texto. Offline, instantáneo, siempre disponible.
  - IA:     un LLM interpreta los casos que las reglas no resuelven.

El motor de reglas existe por una razón concreta: en una demo en vivo el wifi
se cae. El sistema tiene que seguir funcionando. Si hay API key, la IA se suma
para los casos ambiguos; si no la hay, las reglas sostienen todo el circuito.

Sobre la clasificación: el corte entre recuperable y no recuperable no es un
criterio propio. Los manuales de prestadores que publican las obras sociales ya
dividen las causales en "débitos re facturables" y "débitos no re facturables".
El campo `refacturable` de cada categoría refleja esa clasificación oficial;
`fundamento` deja asentado de dónde sale. Ver `documentos-reales/README.md`.
"""

import os
import re

# --- Vías de recupero -------------------------------------------------------
# Un débito no tiene un solo camino posible. Tiene tres, y son excluyentes en
# el tiempo: primero la refacturación, después la auditoría conjunta, y como
# última instancia el reclamo ante la Superintendencia.

VIA_REFACTURACION = "Refacturación"
VIA_AUDITORIA = "Auditoría conjunta"
VIA_SSSALUD = "Reclamo ante la SSSalud"
VIA_NINGUNA = "Sin acción"

# --- Catálogo de categorías -------------------------------------------------
# recuperabilidad: VERDE (se refactura corrigiendo la forma)
#                  AMARILLO (requiere una gestión previa)
#                  ROJO (no subsanable)

CATEGORIAS = {
    "firma_sello": {
        "nombre": "Falta firma o sello del profesional",
        "recuperabilidad": "VERDE",
        "refacturable": True,
        "via": VIA_REFACTURACION,
        "accion": "Recabar firma y sello del profesional actuante y refacturar.",
        "fundamento": "Listado como débito re facturable en los manuales de prestadores.",
    },
    "datos_afiliado": {
        "nombre": "Datos del afiliado erróneos o incompletos",
        "recuperabilidad": "VERDE",
        "refacturable": True,
        "via": VIA_REFACTURACION,
        "accion": "Corregir los datos contra el padrón y refacturar.",
        "fundamento": "Listado como débito re facturable en los manuales de prestadores.",
    },
    "diagnostico": {
        "nombre": "Diagnóstico ausente o mal codificado",
        "recuperabilidad": "VERDE",
        "refacturable": True,
        "via": VIA_REFACTURACION,
        "accion": "Completar el diagnóstico con codificación CIE-10 y refacturar.",
        "fundamento": "Listado como débito re facturable en los manuales de prestadores.",
    },
    "informe_medico": {
        "nombre": "Falta informe de la práctica realizada",
        "recuperabilidad": "VERDE",
        "refacturable": True,
        "via": VIA_REFACTURACION,
        "accion": "Recuperar el informe del servicio actuante y refacturar.",
        "fundamento": "Listado como débito re facturable en los manuales de prestadores.",
    },
    "enmienda": {
        "nombre": "Enmienda sin salvar",
        "recuperabilidad": "VERDE",
        "refacturable": True,
        "via": VIA_REFACTURACION,
        "accion": "Salvar la enmienda con firma del profesional actuante y refacturar.",
        "fundamento": "Listado como débito re facturable en los manuales de prestadores.",
    },
    "documentacion": {
        "nombre": "Documentación de respaldo incompleta",
        "recuperabilidad": "VERDE",
        "refacturable": True,
        "via": VIA_REFACTURACION,
        "accion": "Recuperar la documentación faltante del archivo del servicio y refacturar.",
        "fundamento": "Listado como débito re facturable en los manuales de prestadores.",
    },
    "conformidad": {
        "nombre": "Falta conformidad del afiliado",
        "recuperabilidad": "AMARILLO",
        "refacturable": False,
        "via": VIA_AUDITORIA,
        "accion": "No admite refacturación directa. Llevar a auditoría conjunta con la "
                  "historia clínica y el registro del servicio como respaldo.",
        "fundamento": "Los manuales lo listan entre los débitos NO re facturables. Para un "
                      "HPGD, sin embargo, el débito unilateral no es oponible: la vía es la "
                      "auditoría conjunta (art. 18 Dec. 939/2000 y art. 14 Res. 487/2002 MS).",
    },
    "autorizacion": {
        "nombre": "Sin autorización previa",
        "recuperabilidad": "AMARILLO",
        "refacturable": False,
        "via": VIA_AUDITORIA,
        "accion": "Solicitar convalidación en auditoría conjunta, acreditando la demanda "
                  "espontánea y la notificación cursada en término.",
        "fundamento": "Causal médico-administrativa de débito. En el régimen HPGD la demanda "
                      "espontánea y la notificación dentro de las 48 h hábiles sostienen el "
                      "reclamo (Res. 487/2002 MS).",
    },
    "no_validada": {
        "nombre": "Práctica no validada u orden adulterada",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Sin acción posible. Revisar el circuito de validación en admisión.",
        "fundamento": "Listado como débito NO re facturable en los manuales de prestadores.",
    },
    "arancel": {
        "nombre": "Diferencia de aranceles",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Sin acción posible sobre este lote. Revisar valores convenidos y nomenclador.",
        "fundamento": "Listado como débito NO re facturable en los manuales de prestadores.",
    },
    "error_calculo": {
        "nombre": "Error de suma o de codificación",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Sin acción posible. Corregir la liquidación en origen.",
        "fundamento": "Listado como débito NO re facturable en los manuales de prestadores.",
    },
    "derivacion": {
        "nombre": "Falta derivación médica",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Sin acción posible. Exigir derivación al momento de la admisión.",
        "fundamento": "Listado como débito NO re facturable en los manuales de prestadores.",
    },
    "no_vigente": {
        "nombre": "Afiliado sin cobertura vigente a la fecha",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Sin acción posible. Derivar a recupero por otra vía.",
        "fundamento": "La prestación no corresponde al agente del seguro observado.",
    },
    "no_cubierta": {
        "nombre": "Prestación no cubierta por el plan",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Sin acción posible. Revisar convenio vigente.",
        "fundamento": "La prestación queda fuera del convenio o del plan contratado.",
    },
    "fuera_plazo": {
        "nombre": "Presentación fuera de plazo",
        "recuperabilidad": "ROJO",
        "refacturable": False,
        "via": VIA_NINGUNA,
        "accion": "Plazo vencido. Analizar como pérdida y corregir el circuito.",
        "fundamento": "Listado como débito NO re facturable en los manuales de prestadores.",
    },
    "sin_clasificar": {
        "nombre": "Motivo no reconocido",
        "recuperabilidad": "AMARILLO",
        "refacturable": False,
        "via": VIA_AUDITORIA,
        "accion": "Requiere revisión manual del auditor.",
        "fundamento": "El sistema no reconoce el motivo. Deriva a una persona en vez de adivinar.",
    },
}

# --- Motor de reglas --------------------------------------------------------
# Orden importante: las categorías no subsanables se evalúan primero, porque
# un motivo como "afiliado no figura en padron" también menciona al afiliado
# y no debe confundirse con un simple error de tipeo en el número.

PATRONES = [
    ("no_vigente",     r"no\s*figura\s*en\s*padron|dado\s*de\s*baja|baja\s*de\s*afiliacion|sin\s*cobertura\s*vigente|no\s*vigente|carnet\s*vencido|no\s*coinciden?\s*con\s*(el\s*)?padron"),
    ("no_cubierta",    r"no\s*(esta\s*)?(incluid|cubiert)|fuera\s*de\s*(cobertura|plan)|no\s*corresponde\s*al\s*plan"),
    ("fuera_plazo",    r"fuera\s*de\s*(termino|plazo)|vencid[oa]\s*el\s*plazo|presentacion\s*tardia|plazo\s*convenido|practica\s*vencida"),
    ("no_validada",    r"no\s*validad|adulterad|duplicad"),
    ("arancel",        r"arancel|valor(es)?\s*convenid|nomenclador\s*vigente"),
    ("error_calculo",  r"error\s*en\s*la\s*suma|codigos?\s*incluid|excluida\s*de\s*modulo|ya\s*contemplada"),
    ("derivacion",     r"derivacion"),
    ("autorizacion",   r"autorizacion|autoriz|auditoria\s*previa"),
    ("enmienda",       r"enmienda|correccion\s*manuscrita|raspadura|sin\s*salvar|no\s*salvad"),
    ("conformidad",    r"conformidad|firma\s*del\s*(beneficiario|afiliado)"),
    ("firma_sello",    r"firma|sello|matricula"),
    ("informe_medico", r"informe|graficos"),
    ("diagnostico",    r"diagnostico|cie-?\s*10"),
    ("datos_afiliado", r"afiliad|beneficiari|carnet|nro\s*de?\s*af|numero\s*de\s*af"),
    ("documentacion",  r"documentacion|orden\s*medica|comprobante|protocolo|adjunt|epicrisis"),
]


def _normalizar(texto):
    """Minúsculas y sin tildes, para que los patrones no dependan de la ortografía."""
    t = texto.lower()
    for a, b in zip("áéíóúü", "aeiouu"):
        t = t.replace(a, b)
    return t


def clasificar_por_reglas(motivo_texto):
    """Devuelve (categoria, confianza). Confianza 0.0 si no reconoce el motivo."""
    t = _normalizar(motivo_texto)
    for categoria, patron in PATRONES:
        if re.search(patron, t):
            return categoria, 0.9
    return "sin_clasificar", 0.0


# --- Motor IA ---------------------------------------------------------------

_PROMPT = """Sos un asistente de auditoría administrativa de facturación médica.
Clasificá el motivo de rechazo en UNA de estas categorías:

{categorias}

Respondé únicamente con el identificador de la categoría, sin explicación.

Motivo de rechazo: "{motivo}"
"""


def hay_ia_disponible():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def clasificar_por_ia(motivo_texto, modelo="claude-sonnet-5"):
    """Clasifica con LLM. Devuelve (categoria, confianza) o (None, 0) si falla."""
    if not hay_ia_disponible():
        return None, 0.0
    try:
        import anthropic
        cliente = anthropic.Anthropic()
        listado = "\n".join(
            f"- {k}: {v['nombre']}" for k, v in CATEGORIAS.items() if k != "sin_clasificar"
        )
        resp = cliente.messages.create(
            model=modelo,
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": _PROMPT.format(categorias=listado, motivo=motivo_texto),
            }],
        )
        cat = resp.content[0].text.strip().lower()
        return (cat, 0.95) if cat in CATEGORIAS else ("sin_clasificar", 0.0)
    except Exception:
        return None, 0.0


# --- Orquestador ------------------------------------------------------------

def clasificar_lote(lote, usar_ia=False):
    """
    Clasifica cada débito y le agrega categoría, recuperabilidad, vía y acción.

    Estrategia: las reglas resuelven la mayoría al instante; la IA se reserva
    para lo que las reglas no reconocen, que es donde realmente aporta.
    """
    resultado = []
    for d in lote:
        categoria, confianza = clasificar_por_reglas(d["motivo_texto"])
        motor = "reglas"

        if categoria == "sin_clasificar" and usar_ia:
            cat_ia, conf_ia = clasificar_por_ia(d["motivo_texto"])
            if cat_ia:
                categoria, confianza, motor = cat_ia, conf_ia, "ia"

        meta = CATEGORIAS[categoria]
        recuperabilidad = meta["recuperabilidad"]
        via = meta["via"]
        accion = meta["accion"]

        # Vencido el plazo de refacturación, el débito no se apaga solo: mientras
        # no se cumpla el aniversario de la prestación todavía queda la vía del
        # reclamo ante la Superintendencia. Recién ahí se pierde de verdad.
        if recuperabilidad != "ROJO" and d["dias_restantes"] <= 0:
            if d.get("dias_sssalud", 0) > 0:
                recuperabilidad = "AMARILLO"
                via = VIA_SSSALUD
                accion = (
                    "Venció el plazo de refacturación. Queda la vía del reclamo ante la "
                    f"SSSalud: restan {d['dias_sssalud']} días hasta el aniversario de la "
                    "prestación (Res. 487/2002 MS)."
                )
            else:
                recuperabilidad = "ROJO"
                via = VIA_NINGUNA
                accion = "Plazo vencido y aniversario cumplido. Ya no admite reclamo."

        item = dict(d)
        item.update({
            "categoria": categoria,
            "categoria_nombre": meta["nombre"],
            "recuperabilidad": recuperabilidad,
            "refacturable": meta["refacturable"],
            "via": via,
            "accion": accion,
            "fundamento": meta["fundamento"],
            "confianza": confianza,
            "motor": motor,
            "urgente": recuperabilidad != "ROJO" and 0 < d["dias_restantes"] <= 15,
        })
        resultado.append(item)
    return resultado


def resumen(clasificados):
    """Totales por semáforo, más los indicadores que van al tablero."""
    tot = {"VERDE": 0.0, "AMARILLO": 0.0, "ROJO": 0.0}
    cant = {"VERDE": 0, "AMARILLO": 0, "ROJO": 0}
    for d in clasificados:
        tot[d["recuperabilidad"]] += d["monto"]
        cant[d["recuperabilidad"]] += 1

    urgentes = [d for d in clasificados if d["urgente"]]
    total = sum(d["monto"] for d in clasificados)
    recuperable = tot["VERDE"] + tot["AMARILLO"]

    # Reparto por vía: qué parte se resuelve con papeles, qué parte hay que ir
    # a discutir a la auditoría y qué parte ya solo se reclama ante la SSSalud.
    por_via = {}
    for d in clasificados:
        e = por_via.setdefault(d["via"], {"cantidad": 0, "monto": 0.0})
        e["cantidad"] += 1
        e["monto"] += d["monto"]

    return {
        "montos": tot,
        "cantidades": cant,
        "total": total,
        "recuperable": recuperable,
        "pct_recuperable": (recuperable / total * 100) if total else 0.0,
        "urgentes_cant": len(urgentes),
        "urgentes_monto": sum(d["monto"] for d in urgentes),
        "sin_clasificar": sum(1 for d in clasificados if d["categoria"] == "sin_clasificar"),
        "por_via": por_via,
        "refacturable_monto": sum(d["monto"] for d in clasificados if d["via"] == VIA_REFACTURACION),
        "refacturable_cant": sum(1 for d in clasificados if d["via"] == VIA_REFACTURACION),
    }


def causas_frecuentes(clasificados, top=5):
    """Ranking de causas por monto — el insumo para pasar del recupero a la prevención."""
    acum = {}
    for d in clasificados:
        k = d["categoria_nombre"]
        e = acum.setdefault(k, {"cantidad": 0, "monto": 0.0, "recuperabilidad": d["recuperabilidad"]})
        e["cantidad"] += 1
        e["monto"] += d["monto"]
    orden = sorted(acum.items(), key=lambda kv: kv[1]["monto"], reverse=True)
    return [{"causa": k, **v} for k, v in orden[:top]]
