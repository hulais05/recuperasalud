"""
Generador de débitos sintéticos.

IMPORTANTE: todo lo que produce este módulo es ficticio. No hay ni puede haber
datos reales de pacientes en el prototipo. Los campos son exclusivamente
administrativos (afiliado, prestación, fecha, monto, motivo de rechazo);
no existe ningún dato clínico.

Los motivos de rechazo NO están inventados: son las causales de débito que las
propias obras sociales publican en sus manuales de prestadores, reescritas con
la suciedad de tipeo con la que llegan en la vida real. Ver
`documentos-reales/README.md` para las fuentes.
"""

import random
from datetime import date, timedelta

OBRAS_SOCIALES = [
    "Obra Social A", "Obra Social B", "Obra Social C",
    "Obra Social D", "Obra Social E",
]

PRESTACIONES = [
    ("Consulta en guardia", 18_500, 42_000),
    ("Radiografía simple", 22_000, 55_000),
    ("Análisis de laboratorio", 15_000, 48_000),
    ("Ecografía", 38_000, 95_000),
    ("Sutura simple", 26_000, 60_000),
    ("Internación 24 h", 180_000, 420_000),
    ("Electrocardiograma", 19_000, 44_000),
    ("Nebulización", 12_000, 28_000),
    ("Tomografía", 210_000, 480_000),
    ("Curación y control", 14_000, 33_000),
]

# Motivos de rechazo tal como llegan en la vida real: texto libre, sin criterio
# uniforme, con abreviaturas, mayúsculas inconsistentes y errores de tipeo.
# Esta suciedad es el problema que el clasificador tiene que resolver.
#
# Las causales están tomadas de las listas publicadas en manuales de prestadores
# de agentes del seguro de salud, que las agrupan textualmente en "débitos re
# facturables" y "débitos no re facturables".
MOTIVOS = [
    # --- falta firma o sello del profesional (re facturable) ---
    ("FALTA FIRMA Y SELLO DEL PROFESIONAL ACTUANTE", "firma_sello"),
    ("s/firma medico", "firma_sello"),
    ("no consta sello aclaratorio del profesional", "firma_sello"),
    ("Sello ilegible. No se puede identificar matricula.", "firma_sello"),
    ("falta firma prof.", "firma_sello"),
    ("ausencia firma y sello del profesional en consultas y practicas", "firma_sello"),
    # --- datos del afiliado (re facturable) ---
    ("nro afiliado erroneo", "datos_afiliado"),
    ("NUMERO DE AFILIADO INCOMPLETO", "datos_afiliado"),
    ("Datos del beneficiario ilegibles", "datos_afiliado"),
    ("falta apellido y nombre del afiliado en la orden", "datos_afiliado"),
    ("ausencia de datos del afiliado", "datos_afiliado"),
    # --- diagnóstico (re facturable) ---
    ("falta diagnostico", "diagnostico"),
    ("DIAGNOSTICO NO CODIFICADO SEGUN CIE-10", "diagnostico"),
    ("diagnostico incompleto/ilegible", "diagnostico"),
    ("ausencia de diagnostico presuntivo o codificado legible", "diagnostico"),
    # --- informe médico de la práctica (re facturable) ---
    ("falta informe medico de la practica realizada", "informe_medico"),
    ("AUSENCIA DE INFORME TEXTUAL Y GRAFICOS DE LA PRACTICA", "informe_medico"),
    ("s/informe en mas de 4 consultas del mismo paciente en el mes", "informe_medico"),
    # --- enmienda sin salvar (re facturable) ---
    ("enmienda sin salvar en la fecha de realizacion", "enmienda"),
    ("ORDEN CON CORRECCION MANUSCRITA NO SALVADA", "enmienda"),
    ("raspadura en el nro de orden, sin salvar", "enmienda"),
    # --- documentación de respaldo (re facturable) ---
    ("documentacion incompleta - falta orden medica", "documentacion"),
    ("NO SE ADJUNTA COMPROBANTE DE PRESTACION", "documentacion"),
    ("falta protocolo del estudio", "documentacion"),
    ("ausencia de protocolo quirurgico y anatomia patologica", "documentacion"),
    ("falta epicrisis con dx de ingreso y egreso", "documentacion"),
    # --- conformidad del afiliado (NO re facturable según manual: vía auditoría) ---
    ("falta conformidad del afiliado", "conformidad"),
    ("SIN FIRMA DEL BENEFICIARIO", "conformidad"),
    ("no se adjunta conformidad de atencion", "conformidad"),
    ("ausencia de firma y conformidad del afiliado", "conformidad"),
    # --- autorización previa (vía auditoría conjunta) ---
    ("SIN AUTORIZACION PREVIA - PRACTICA PROGRAMADA", "autorizacion"),
    ("no se solicito autorizacion", "autorizacion"),
    ("Practica requiere auditoria previa. No consta.", "autorizacion"),
    ("falta nro de autorizacion", "autorizacion"),
    ("prestaciones no convenidas y SIN AUTORIZACION PREVIA", "autorizacion"),
    # --- práctica no validada / orden adulterada (no re facturable) ---
    ("practica no validada", "no_validada"),
    ("ORDEN ADULTERADA Y/O DUPLICADA", "no_validada"),
    ("orden duplicada, ya liquidada en periodo anterior", "no_validada"),
    # --- aranceles (no re facturable) ---
    ("diferencias de aranceles segun valores convenidos", "arancel"),
    ("VALOR FACTURADO NO COINCIDE CON NOMENCLADOR VIGENTE", "arancel"),
    # --- error de cálculo o codificación (no re facturable) ---
    ("error en la suma de la facturacion", "error_calculo"),
    ("FACTURACION DE CODIGOS INCLUIDOS EN OTROS", "error_calculo"),
    ("practica excluida de modulo, ya contemplada", "error_calculo"),
    # --- falta de derivación (no re facturable) ---
    ("falta de derivacion medica", "derivacion"),
    ("SIN DERIVACION - KINESIOLOGIA", "derivacion"),
    # --- afiliación (no subsanable) ---
    ("afiliado no figura en padron a la fecha de prestacion", "no_vigente"),
    ("BENEFICIARIO DADO DE BAJA CON ANTERIORIDAD", "no_vigente"),
    ("baja de afiliacion previa a la atencion", "no_vigente"),
    ("carnet vencido / datos no coinciden con padron", "no_vigente"),
    # --- cobertura (no subsanable) ---
    ("practica no incluida en plan contratado", "no_cubierta"),
    ("PRESTACION NO CUBIERTA POR EL PLAN", "no_cubierta"),
    # --- plazo (no subsanable) ---
    ("presentacion fuera de termino", "fuera_plazo"),
    ("LOTE PRESENTADO VENCIDO EL PLAZO CONVENIDO", "fuera_plazo"),
    ("de consulta y practica vencida", "fuera_plazo"),
]

# Peso relativo de cada familia de motivos. Refleja el patrón real: la mayor
# parte de los rechazos son fallas de forma perfectamente subsanables.
PESOS = {
    "firma_sello": 20, "datos_afiliado": 15, "diagnostico": 10,
    "informe_medico": 7, "enmienda": 6, "documentacion": 9,
    "conformidad": 8, "autorizacion": 10,
    "no_validada": 4, "arancel": 3, "error_calculo": 3, "derivacion": 2,
    "no_vigente": 5, "no_cubierta": 4, "fuera_plazo": 3,
}

# --- Plazos del circuito, según normativa -----------------------------------
# No son números elegidos por conveniencia: salen del régimen de Hospitales
# Públicos de Gestión Descentralizada y de las normas de facturación que las
# obras sociales publican para sus prestadores.

DIAS_PAGO_OBRA_SOCIAL = 60      # Dec. 939/2000: plazo para saldar lo facturado
DIAS_REFACTURACION = 90         # 3 meses desde la notificación del débito
DIAS_ANIVERSARIO_SSSALUD = 365  # Res. 487/2002 MS: 1 año aniversario de la prestación


def generar_lote(n=200, semilla=1812, hoy=None):
    """Devuelve una lista de n débitos sintéticos."""
    rnd = random.Random(semilla)
    hoy = hoy or date.today()

    familias = list(PESOS.keys())
    pesos = [PESOS[f] for f in familias]

    por_familia = {}
    for texto, fam in MOTIVOS:
        por_familia.setdefault(fam, []).append(texto)

    lote = []
    for i in range(n):
        familia = rnd.choices(familias, weights=pesos, k=1)[0]
        motivo = rnd.choice(por_familia[familia])
        practica, pmin, pmax = rnd.choice(PRESTACIONES)

        # La prestación ocurrió entre 30 y 160 días atrás.
        dias_atras = rnd.randint(30, 160)
        f_prest = hoy - timedelta(days=dias_atras)
        # El débito llegó entre 20 y 60 días después de la prestación.
        f_debito = f_prest + timedelta(days=rnd.randint(20, 60))
        # Desde el débito corre el plazo para presentar la refacturación.
        f_vence = f_debito + timedelta(days=DIAS_REFACTURACION)
        # En paralelo corre el aniversario de la prestación: mientras no se
        # cumpla, todavía queda la vía del reclamo ante la Superintendencia.
        f_sssalud = f_prest + timedelta(days=DIAS_ANIVERSARIO_SSSALUD)

        lote.append({
            "id": f"DEB-{2026}-{i+1:04d}",
            "obra_social": rnd.choice(OBRAS_SOCIALES),
            "afiliado": f"{rnd.randint(10,99)}-{rnd.randint(10_000_000, 45_000_000)}-{rnd.randint(0,9)}",
            "practica": practica,
            "fecha_prestacion": f_prest,
            "fecha_debito": f_debito,
            "fecha_vencimiento": f_vence,
            "dias_restantes": (f_vence - hoy).days,
            "fecha_limite_sssalud": f_sssalud,
            "dias_sssalud": (f_sssalud - hoy).days,
            "monto": float(rnd.randint(pmin, pmax)),
            "motivo_texto": motivo,
            "_familia_real": familia,   # solo para medir precisión, no se muestra
        })
    return lote
