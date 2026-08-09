"""
Generación del descargo formal.

El sistema PROPONE el texto; una persona lo revisa, lo edita y lo firma.
Nunca se presenta solo. Es la condición que fija la ordenanza municipal de IA
de Salta: "sin sustituir la intervención humana".

El documento no es siempre el mismo. Según la vía que corresponda, cambia el
destinatario, el petitorio y el fundamento normativo:

  · Refacturación      → nota al agente del seguro, se acompaña lo que subsana.
  · Auditoría conjunta → se solicita la auditoría en terreno, en el hospital.
  · Reclamo SSSalud    → se presenta ante la Superintendencia.

Las citas normativas salen de las fuentes relevadas en
`documentos-reales/README.md`.
"""

from datetime import date

from .clasificador import VIA_REFACTURACION, VIA_AUDITORIA, VIA_SSSALUD

# --- Lo que subsana cada tipo de observación --------------------------------

PLANTILLAS = {
    "firma_sello": (
        "Se acompaña la orden con la firma, el sello y el número de matrícula del "
        "profesional actuante, subsanando la observación formal que motivó el débito. "
        "La prestación fue efectivamente realizada y se encuentra respaldada en el "
        "registro del servicio."
    ),
    "datos_afiliado": (
        "Se rectifican los datos identificatorios del beneficiario conforme al padrón "
        "vigente a la fecha de la prestación. El error consignado es de índole formal y "
        "no altera la procedencia de la prestación facturada."
    ),
    "diagnostico": (
        "Se completa el diagnóstico con su correspondiente codificación CIE-10, "
        "subsanando la observación formal. La prestación resulta pertinente al cuadro "
        "consignado en el registro asistencial."
    ),
    "informe_medico": (
        "Se acompaña el informe de la práctica realizada, suscripto por el profesional "
        "actuante, obrante en el archivo del servicio."
    ),
    "enmienda": (
        "Se acompaña la documentación con la enmienda salvada y refrendada por el "
        "profesional actuante, subsanando la observación formal."
    ),
    "documentacion": (
        "Se acompaña la documentación de respaldo requerida, obrante en el archivo del "
        "servicio, que acredita la efectiva realización de la prestación facturada."
    ),
    "conformidad": (
        "Este Hospital deja constancia de que la prestación fue efectivamente realizada, "
        "conforme surge de la historia clínica y del registro del servicio actuante, que "
        "se ponen a disposición para su compulsa en los términos del artículo 14 de la "
        "Resolución 487/2002 MS."
    ),
    "autorizacion": (
        "Se solicita la convalidación de la prestación efectuada. Atento al carácter de "
        "demanda espontánea de la atención brindada y a la imposibilidad material de "
        "gestionar la autorización en forma previa, se requiere su auditoría conforme al "
        "régimen aplicable, dejándose constancia de la notificación cursada en término."
    ),
}

FALLBACK = (
    "Se solicita la revisión del débito aplicado. La prestación fue efectivamente "
    "realizada y se encuentra respaldada en el registro del servicio."
)

# --- Fundamento normativo por vía -------------------------------------------

FUNDAMENTOS = {
    VIA_REFACTURACION: (
        "Se acompaña copia de los motivos del débito que originan la presente, junto con "
        "la documentación respaldatoria, conforme a las normas de facturación vigentes. "
        "La presentación se formula dentro del plazo previsto para la refacturación."
    ),
    VIA_AUDITORIA: (
        "Se solicita la realización de Auditoría Conjunta en los términos del artículo 18 "
        "del Decreto 939/2000 PEN y del artículo 14 de la Resolución 487/2002 del "
        "Ministerio de Salud, a llevarse a cabo en la sede de este Hospital, labrándose "
        "acta en tres ejemplares con constancia del objeto, los motivos y las conclusiones. "
        "Se deja expresa constancia de que, tratándose de un Hospital Público de Gestión "
        "Descentralizada, los débitos unilaterales no resultan oponibles sin el "
        "cumplimiento del procedimiento previsto."
    ),
    VIA_SSSALUD: (
        "Habiendo vencido el plazo para la refacturación sin que mediara acuerdo entre las "
        "partes, se deja constancia de que este Hospital se encuentra en condiciones de "
        "reclamar el pago ante la Superintendencia de Servicios de Salud, conforme al "
        "Sistema de Débito Automático previsto en los artículos 15 a 18 del Decreto "
        "939/2000 PEN y reglamentado por la Resolución 487/2002 del Ministerio de Salud, "
        "acompañando los Anexos I y II con carácter de declaración jurada."
    ),
}

ENCABEZADOS = {
    VIA_REFACTURACION: "Nota de descargo y solicitud de refacturación",
    VIA_AUDITORIA: "Solicitud de Auditoría Conjunta",
    VIA_SSSALUD: "Reclamo ante la Superintendencia de Servicios de Salud",
}

DESTINATARIOS = {
    VIA_REFACTURACION: "{obra_social}\nDepartamento de Auditoría Médica",
    VIA_AUDITORIA: "{obra_social}\nGerencia de Auditoría Médica",
    VIA_SSSALUD: (
        "Superintendencia de Servicios de Salud\n"
        "Gerencia de Control Prestacional — Departamento HPGD\n"
        "Ref. agente del seguro: {obra_social}"
    ),
}

PETITORIOS = {
    VIA_REFACTURACION: (
        "En virtud de lo expuesto, solicitamos dejar sin efecto el débito aplicado y "
        "proceder a la liquidación del importe correspondiente."
    ),
    VIA_AUDITORIA: (
        "En virtud de lo expuesto, solicitamos se sirvan designar auditor y fijar fecha "
        "para la realización de la Auditoría Conjunta, dentro del plazo previsto."
    ),
    VIA_SSSALUD: (
        "En virtud de lo expuesto, solicitamos se proceda conforme al Sistema de Débito "
        "Automático sobre la cuenta del agente del seguro de salud individualizado."
    ),
}

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _fecha_larga(d):
    """'8 de agosto de 2026' — strftime('%B') depende del locale del sistema."""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def generar_descargo(debito, institucion="Hospital Público de Gestión Descentralizada", hoy=None):
    """Devuelve el texto del descargo listo para revisión humana."""
    if debito["recuperabilidad"] == "ROJO":
        return None

    hoy = hoy or date.today()
    via = debito.get("via", VIA_REFACTURACION)
    cuerpo = PLANTILLAS.get(debito["categoria"], FALLBACK)
    fundamento = FUNDAMENTOS.get(via, FUNDAMENTOS[VIA_REFACTURACION])
    encabezado = ENCABEZADOS.get(via, ENCABEZADOS[VIA_REFACTURACION])
    destinatario = DESTINATARIOS.get(via, DESTINATARIOS[VIA_REFACTURACION]).format(
        obra_social=debito["obra_social"]
    )
    petitorio = PETITORIOS.get(via, PETITORIOS[VIA_REFACTURACION])

    if via == VIA_SSSALUD:
        plazo = (
            f"Aniversario de la prestación: {debito['fecha_limite_sssalud'].strftime('%d/%m/%Y')} "
            f"({debito['dias_sssalud']} días restantes)"
        )
    else:
        plazo = (
            f"Vencimiento del plazo: {debito['fecha_vencimiento'].strftime('%d/%m/%Y')} "
            f"({debito['dias_restantes']} días restantes)"
        )

    return f"""Salta, {_fecha_larga(hoy)}

Señores
{destinatario}
S                     /                     D

Ref.: {encabezado} — débito {debito['id']}

De nuestra consideración:

Nos dirigimos a ustedes en relación con el débito aplicado sobre la prestación
detallada a continuación, a fin de presentar el correspondiente descargo.

    Prestación .......... {debito['practica']}
    Beneficiario ........ {debito['afiliado']}
    Fecha de prestación . {debito['fecha_prestacion'].strftime('%d/%m/%Y')}
    Fecha del débito .... {debito['fecha_debito'].strftime('%d/%m/%Y')}
    Importe debitado .... $ {debito['monto']:,.2f}
    Motivo del débito ... {debito['motivo_texto']}
    {plazo}

{cuerpo}

{fundamento}

{petitorio}

Sin otro particular, saludamos a ustedes atentamente.


                                        ______________________________
                                        {institucion}
                                        Departamento de Facturación y Recupero

---
Borrador generado automáticamente. Requiere revisión, edición y firma
de un responsable antes de su presentación.
Fundamento: Decreto 939/2000 PEN · Resolución 487/2002 MS · RG AFIP 4540/2019.
"""
