"""
RecuperaSalud — MVP
Auditoría asistida de débitos de obras sociales.

Ejecutar:  streamlit run app.py
"""

import base64
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.datos import generar_lote
from core.clasificador import (
    clasificar_lote, resumen, causas_frecuentes, hay_ia_disponible,
    VIA_REFACTURACION, VIA_AUDITORIA, VIA_SSSALUD, VIA_NINGUNA,
)
from core.descargo import generar_descargo

AQUI = Path(__file__).resolve().parent


def _primera(*rutas):
    """La primera ruta que exista. Permite que el mismo archivo funcione tanto
    dentro de la carpeta de trabajo del hackathon como en el repo publicado,
    donde los documentos viven al lado de la app."""
    for r in rutas:
        if r.exists():
            return r
    return rutas[0]


FORMULARIOS = _primera(
    AQUI / "documentos" / "formularios-ejemplo.html",
    AQUI.parent / "documentos-reales" / "formularios-ejemplo.html",
)
LOGO = AQUI / "assets" / "logo.png"
ISOTIPO = AQUI / "assets" / "isotipo.png"
# El lema vive en una sola constante: aparece en los tres puntos de identidad
# (barra lateral, encabezado y pie) y tiene que cambiar en un solo lugar.
LEMA = "Mismo recurso, mejor proceso."

st.set_page_config(page_title="RecuperaSalud", page_icon="🩺", layout="wide")

# Paleta clara, en la línea de las plataformas del rubro (RapidClaims, Adonis):
# fondo casi blanco y tarjetas blancas puras, que se recortan por borde y sombra
# en vez de por contraste de color. Los verdes y ámbares son más oscuros que en
# el tema anterior: sobre fondo blanco, un #10B981 se lee mal.
BG, CARD, BORDE, GREEN, AMBER, RED, TXT, MUT = (
    "#F6F8FB", "#FFFFFF", "#E2E8F0", "#047857", "#B45309", "#DC2626", "#0F172A", "#64748B",
)

st.markdown(f"""
<style>
  .stApp {{ background: {BG}; }}
  section[data-testid="stSidebar"] {{
    background: {CARD}; border-right: 1px solid {BORDE};
  }}
  h1, h2, h3, h4, p, label, span {{ color: {TXT}; }}
  .kpi {{
    background: {CARD}; border-radius: 12px; padding: 18px 20px;
    border: 1px solid {BORDE}; height: 100%;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .04), 0 1px 3px rgba(15, 23, 42, .06);
  }}
  /* Las filas de tarjetas se dibujan como un solo contenedor flex y no con
     st.columns. Streamlit no estira las columnas de una misma fila: cada una
     mide lo que mide su contenido, y una tarjeta con el pie en tres líneas
     quedaba mucho más alta que la de al lado. Acá el stretch es del flex y
     todas terminan con la altura de la más alta, sin números mágicos. */
  .tarjetas {{ display: flex; gap: 12px; flex-wrap: wrap; align-items: stretch; }}
  /* `height: auto` no es redundante: align-items:stretch solo estira al hijo
     cuyo alto computado es `auto`, y .kpi trae `height: 100%` para cuando la
     tarjeta se dibuja dentro de un st.columns. Un porcentaje no es `auto`, así
     que el stretch se salteaba y la tarjeta de pie más corto quedaba baja. */
  .tarjetas .kpi {{ flex: 1 1 0; min-width: 170px; height: auto; }}
  .kpi .lbl {{ color: {MUT}; font-size: 11px; letter-spacing: .09em;
              text-transform: uppercase; margin-bottom: 8px; }}
  /* El número manda y la etiqueta acompaña: peso 600 en vez de 700 y tracking
     apretado, que es lo que hace que un dato grande no se vea gritado. */
  .kpi .val {{ font-size: clamp(24px, 2.5vw, 39px); font-weight: 600;
               letter-spacing: -.022em; line-height: 1.1; white-space: nowrap; }}
  /* Variante para etiquetas de texto: los nombres largos tienen que envolver
     dentro de la tarjeta, no desbordarla como hacen los importes. */
  .kpi .val.txt {{ font-size: clamp(14px, 1.1vw, 18px); white-space: normal;
                   line-height: 1.25; overflow-wrap: anywhere; }}
  .kpi .sub {{ color: {MUT}; font-size: 12px; margin-top: 4px; }}
  .brand {{ font-size: 30px; font-weight: 700; }}
  .brand span {{ color: {GREEN}; }}
  /* Encabezado del cuerpo: isotipo y nombre en la misma línea. Con la barra
     lateral plegada, esto es lo único que identifica al producto. */
  .cab {{
    display: flex; align-items: center; justify-content: center;
    gap: 14px; margin-bottom: 6px;
  }}
  .cab img {{ height: 54px; width: auto; }}
  .cab .brand {{ line-height: 1.05; }}
  .cab .sub {{ color: {MUT}; font-size: 13px; margin-top: 2px; }}
  /* El lema es identidad, no dato. Se separa del subtítulo operativo por color
     de acento y espaciado, para que nadie lo lea como una métrica más. */
  .lema {{ color: {GREEN}; font-size: 15px; font-weight: 600;
           letter-spacing: .03em; margin-top: 4px; }}
  /* 15px es la medida para el encabezado, que es lo que se proyecta. En la
     barra lateral y en el pie el lema acompaña, no encabeza: a 15px pesaba
     demasiado y en la columna angosta se partía en dos líneas. */
  section[data-testid="stSidebar"] .lema {{ font-size: 13px; margin-top: 3px; }}
  .pie .lema {{ font-size: 13px; margin-top: 3px; }}

  /* Pie: cierra la página y sostiene lo que no puede quedar suelto — el
     origen de los datos y el respaldo normativo. */
  .pie {{ text-align: center; padding: 26px 12px 40px; }}
  .pie img {{ height: 40px; width: auto; opacity: .92; }}
  .pie .nom {{ font-size: 17px; font-weight: 700; margin-top: 6px; }}
  .pie .nom span {{ color: {GREEN}; }}
  .pie .ev {{ color: {MUT}; font-size: 12px; margin-top: 2px; }}
  .pie .reglas {{
    color: {MUT}; font-size: 12px; margin-top: 16px; line-height: 1.9;
  }}
  .pie .reglas b {{ color: {TXT}; font-weight: 600; }}
  .pie .norma {{
    display: inline-block; margin: 0 5px; padding: 3px 11px;
    border: 1px solid {BORDE}; border-radius: 999px; background: {CARD};
    font-size: 11px; color: {MUT}; white-space: nowrap;
  }}
  .tag {{ display:inline-block; padding: 3px 10px; border-radius: 999px;
          font-size: 11px; letter-spacing: .06em; }}
  .stDataFrame {{ border-radius: 10px; overflow: hidden; }}
  div[data-testid="stMetricValue"] {{ color: {TXT}; }}

  /* El botón que pliega la barra lateral aparece solo al pasar el mouse por
     encima. En una demo proyectada eso es un control invisible: nadie sabe que
     está ahí. Se fuerza visible siempre. */
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stSidebarCollapseButton"] button,
  [data-testid="stExpandSidebarButton"],
  [data-testid="stExpandSidebarButton"] button {{
    opacity: 1 !important; visibility: visible !important; transform: none !important;
  }}
  [data-testid="stSidebarHeader"] {{ opacity: 1 !important; }}
  [data-testid="stSidebarCollapseButton"] button,
  [data-testid="stExpandSidebarButton"] button {{
    border: 1px solid {BORDE} !important; background: {CARD} !important;
  }}

  /* --- Recorrido de las siete etapas -------------------------------------
     Cada etapa dice quién interviene. La única que interviene una persona va
     resaltada: es la prueba visual de la ordenanza municipal de IA. */
  .pipe {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 4px 0 2px; }}
  /* Las siete etapas tienen que leerse como una línea. Con base fija, una
     palabra larga ("Cuantificación") empuja y las últimas dos caen a un
     segundo renglón: por eso reparto a partes iguales con min-width 0. */
  .paso {{
    flex: 1 1 0; min-width: 0; background: {CARD}; border: 1px solid {BORDE};
    border-radius: 10px; padding: 10px 12px;
  }}
  .paso .n {{ color: {MUT}; font-size: 10px; letter-spacing: .1em; }}
  .paso .q {{ font-size: 14px; font-weight: 650; line-height: 1.2; margin: 2px 0 3px; }}
  .paso .w {{ color: {MUT}; font-size: 11px; }}
  .paso.humano {{
    border: 1.5px solid {GREEN}; background: #ECFDF5;
  }}
  .paso.humano .q, .paso.humano .w {{ color: {GREEN}; }}
  .paso.humano .w {{ font-weight: 650; }}

  .crudo {{
    background: #F1F5F9; border: 1px dashed #94A3B8; border-radius: 8px;
    padding: 12px 14px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px; color: #334155; overflow-wrap: anywhere;
  }}
  .limpio {{
    background: #ECFDF5; border: 1px solid {GREEN}; border-radius: 8px;
    padding: 12px 14px; font-size: 13px; color: #064E3B;
  }}
  .sello {{
    background: #ECFDF5; border-left: 4px solid {GREEN}; border-radius: 6px;
    padding: 10px 14px; font-size: 13px; color: #064E3B;
  }}
  .sello.rechazo {{
    background: #FEF2F2; border-left-color: {RED}; color: #7F1D1D;
  }}

  /* Franja de métricas: número grande arriba, etiqueta chica abajo, todo
     dentro de una sola caja gris dividida. */
  .franja {{
    display: flex; background: #F1F5F9; border: 1px solid {BORDE};
    border-radius: 10px; overflow: hidden; flex-wrap: wrap;
  }}
  .franja .m {{
    flex: 1 1 150px; padding: 14px 18px; border-right: 1px solid {BORDE};
  }}
  .franja .m:last-child {{ border-right: none; }}
  .franja .m .n {{
    font-size: clamp(20px, 2.1vw, 31px); font-weight: 600;
    letter-spacing: -.022em; line-height: 1.1;
  }}
  .franja .m .t {{ color: {MUT}; font-size: 11px; margin-top: 4px; }}
</style>
""", unsafe_allow_html=True)


def kpi(col, label, value, sub="", color=TXT, texto=False):
    """Tarjeta del tablero. `texto=True` para etiquetas largas que deben envolver."""
    clase = "val txt" if texto else "val"
    col.markdown(
        f'<div class="kpi"><div class="lbl">{label}</div>'
        f'<div class="{clase}" style="color:{color}">{value}</div>'
        f'<div class="sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def tarjetas(items):
    """Fila de tarjetas de altura pareja.

    `items` es una lista de (etiqueta, valor, pie, color) o
    (etiqueta, valor, pie, color, texto), donde texto=True achica el valor
    para que las etiquetas largas envuelvan dentro de la tarjeta.
    """
    bloques = []
    for it in items:
        label, value, sub, color = it[:4]
        clase = "val txt" if (len(it) > 4 and it[4]) else "val"
        bloques.append(
            f'<div class="kpi"><div class="lbl">{label}</div>'
            f'<div class="{clase}" style="color:{color}">{value}</div>'
            f'<div class="sub">{sub}</div></div>'
        )
    st.markdown(
        '<div class="tarjetas">' + "".join(bloques) + "</div>", unsafe_allow_html=True
    )


def franja(metricas):
    """Tira de métricas en una sola caja: número grande, etiqueta chica debajo."""
    st.markdown(
        '<div class="franja">'
        + "".join(
            f'<div class="m"><div class="n" style="color:{c}">{n}</div>'
            f'<div class="t">{t}</div></div>'
            for n, t, c in metricas
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def plazo(dias):
    """Un plazo vencido se dice vencido, no con un número negativo."""
    if dias > 0:
        return f"vence en {dias} d"
    if dias == 0:
        return "vence hoy"
    return f"venció hace {abs(dias)} d"


def pesos(x):
    return f"$ {x:,.0f}".replace(",", ".")


def duracion(seg):
    """Bajo el segundo, los milisegundos dicen más que un '0.00 s'."""
    return f"{seg * 1000:.0f} ms" if seg < 1 else f"{seg:.2f} s"


# ---------------------------------------------------------------- sidebar ---
with st.sidebar:
    # El logo va acá y no en el cuerpo: arriba a la izquierda, como en
    # cualquier producto. Si el archivo falta, el nombre en texto lo reemplaza
    # y la app funciona igual.
    if LOGO.exists():
        st.image(str(LOGO), use_container_width=True)
    else:
        st.markdown(
            '<div class="brand">Recupera<span>Salud</span></div>', unsafe_allow_html=True
        )
    st.markdown(
        f'<div class="lema" style="text-align:center">{LEMA}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Auditoría asistida de débitos · MVP")
    st.divider()

    n = st.slider("Débitos en el lote", 50, 500, 200, step=50)
    # 1812 no es arbitraria: es la semilla cuyo lote de 200 débitos da
    # $ 14.249.536 recuperable, el número que figura en la presentación.
    semilla = st.number_input("Semilla del lote", 1, 9999, 1812)

    ia_ok = hay_ia_disponible()
    usar_ia = st.toggle(
        "Usar IA para casos ambiguos",
        value=ia_ok, disabled=not ia_ok,
        help="Las reglas resuelven la mayoría sin conexión. La IA se reserva "
             "para los motivos que las reglas no reconocen.",
    )
    st.caption(
        f"{'🟢' if ia_ok else '⚪'} Motor IA "
        f"{'disponible' if ia_ok else 'no configurado — el sistema funciona igual con reglas'}"
    )

    st.divider()
    # La aprobación tiene que dejar constancia de quién firmó: sin un nombre
    # detrás, "la IA propone y una persona aprueba" es una frase, no un control.
    auditor = st.text_input("Auditor a cargo", value="M. Hulais · Facturación")

    st.divider()
    procesar = st.button("Procesar lote", type="primary", use_container_width=True)
    st.caption("Datos sintéticos. Sin información clínica ni datos reales de pacientes.")


# ------------------------------------------------------------------ estado ---
if procesar or "datos" not in st.session_state:
    t0 = time.perf_counter()
    lote = generar_lote(n=n, semilla=int(semilla))
    clasificados = clasificar_lote(lote, usar_ia=usar_ia)
    st.session_state["datos"] = clasificados
    # El lote sin clasificar se guarda aparte: es lo que permite reclasificar
    # el mismo conjunto con el reloj adelantado, sin volver a consultar la IA.
    st.session_state["lote_crudo"] = lote
    st.session_state["tiempo"] = time.perf_counter() - t0

datos = st.session_state["datos"]
tiempo = st.session_state["tiempo"]
r = resumen(datos)

# ------------------------------------------------------------------ header ---
# El isotipo va incrustado en el HTML y no con st.image() porque tiene que
# quedar en la misma línea que el nombre, no en una fila aparte.
if ISOTIPO.exists():
    b64 = base64.b64encode(ISOTIPO.read_bytes()).decode()
    st.markdown(
        f'<div class="cab"><img src="data:image/png;base64,{b64}" alt="RecuperaSalud">'
        f'<div><div class="brand">Recupera<span>Salud</span></div>'
        f'<div class="lema">{LEMA}</div>'
        f'<div class="sub">Lote de {len(datos)} débitos procesado en '
        f'{duracion(tiempo)}</div></div></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="brand">Recupera<span>Salud</span></div>'
        f'<div class="lema">{LEMA}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:{MUT};margin-top:-6px">'
        f'Lote de {len(datos)} débitos procesado en {duracion(tiempo)}</p>',
        unsafe_allow_html=True,
    )
st.write("")

# ============================================================================
# Recorrido: un débito atravesando el sistema, etapa por etapa.
#
# Las siete etapas y la columna "quién interviene" no son un invento de la
# interfaz: salen de la tabla 6 del documento conceptual del proyecto. El
# tablero agregado muestra CUÁNTO rinde el sistema; esta sección muestra QUÉ
# hace, que es lo que hay que entender primero.
# ============================================================================

ETAPAS = [
    ("1", "Ingesta", "Administración"),
    ("2", "Clasificación", "Motor de IA"),
    ("3", "Semáforo", "Motor de IA"),
    ("4", "Cuantificación", "Sistema"),
    ("5", "Descargo", "Motor de IA"),
    ("6", "Aprobación", "Auditor humano"),
    ("7", "Prevención", "Sistema"),
]

# Qué regla, aplicada en la ventanilla, hubiera evitado este débito.
# Es el puente entre recuperar (una vez) y prevenir (siempre).
PREVENCION = {
    "firma_sello": "Bloquear el cierre de la orden si el campo de firma y sello del "
                   "profesional está vacío o sin matrícula legible.",
    "datos_afiliado": "Validar el número de afiliado contra el padrón en el momento de la "
                      "admisión, antes de que el paciente se retire.",
    "diagnostico": "Exigir el diagnóstico codificado según CIE-10 como campo obligatorio "
                   "para poder cerrar la prestación.",
    "informe_medico": "No dar por cerrada la práctica sin el informe adjunto.",
    "enmienda": "Impedir la corrección manuscrita: si hay que enmendar, que el sistema "
                "obligue a salvar la enmienda con firma.",
    "documentacion": "Checklist de adjuntos obligatorios por tipo de práctica antes de "
                     "incorporar la orden al lote.",
    "conformidad": "Capturar la conformidad del afiliado en el momento de la atención, no "
                   "después.",
    "autorizacion": "Avisar en pantalla que la práctica requiere autorización previa antes "
                    "de realizarla, no al facturarla.",
    "no_validada": "Control de duplicados por número de orden antes de armar el lote.",
    "arancel": "Sincronizar el nomenclador vigente al momento de valorizar.",
    "error_calculo": "Validación aritmética y de códigos incluidos al cerrar la liquidación.",
    "derivacion": "Pedir la derivación como requisito para agendar la práctica.",
    "no_vigente": "Consultar el padrón en la admisión: si el afiliado no está vigente, el "
                  "circuito es otro desde el principio.",
    "no_cubierta": "Verificar cobertura del plan antes de realizar la práctica programada.",
    "fuera_plazo": "Alerta automática de cierre de lote a los 40 días, antes del vencimiento.",
}

st.session_state.setdefault("aprobaciones", {})

st.subheader("Cómo funciona: un débito de punta a punta")
st.caption(
    "El tablero de abajo dice cuánto rinde el sistema. Esta sección muestra qué hace con "
    "un caso concreto, etapa por etapa, y quién interviene en cada una."
)

st.markdown(
    '<div class="pipe">'
    + "".join(
        f'<div class="paso{" humano" if quien == "Auditor humano" else ""}">'
        f'<div class="n">ETAPA {n}</div>'
        f'<div class="q">{nombre}</div>'
        f'<div class="w">{quien}</div></div>'
        for n, nombre, quien in ETAPAS
    )
    + "</div>",
    unsafe_allow_html=True,
)
st.caption(
    "Siete etapas. La IA hace el trabajo pesado en cinco de ellas, pero **no decide en "
    "ninguna**: el expediente se detiene en la etapa 6 y solo avanza cuando una persona "
    "lo aprueba. Es la condición que fija la ordenanza municipal de IA de Salta "
    "(abril 2026)."
)

st.write("")

# --- el caso ---------------------------------------------------------------
casos = [d for d in datos if d["recuperabilidad"] != "ROJO"]
casos.sort(key=lambda d: (d["dias_restantes"], -d["monto"]))

if not casos:
    st.info("No hay débitos recuperables en este lote para recorrer.")
else:
    etiquetas_caso = [
        f'{d["id"]} · {pesos(d["monto"])} · {d["categoria_nombre"]} · '
        f'{plazo(d["dias_restantes"])}'
        for d in casos
    ]
    # La lista se ordena por urgencia, pero la demo no debería abrir con el caso
    # más chico y ya vencido. Arranca en el de mayor importe entre los que
    # todavía se resuelven mandando el papel corregido: es el que mejor explica
    # qué hace el sistema.
    faciles = [i for i, d in enumerate(casos) if d["via"] == VIA_REFACTURACION]
    inicial = max(faciles, key=lambda i: casos[i]["monto"]) if faciles else 0

    ic = st.selectbox(
        "Caso a recorrer (ordenados por urgencia de plazo)",
        range(len(casos)), index=inicial,
        format_func=lambda i: etiquetas_caso[i], key="caso_idx",
    )
    caso = casos[ic]

    # ETAPA 1 · Ingesta ------------------------------------------------------
    st.markdown("##### Etapa 1 · Ingesta — *Administración*")
    st.caption(
        "Así llega la fila, tal como la exporta hoy el hospital: sin categoría, sin plazo "
        "calculado y con el motivo escrito a mano por quien auditó del otro lado."
    )
    st.dataframe(
        pd.DataFrame([{
            "ID": caso["id"],
            "Obra social": caso["obra_social"],
            "Afiliado": caso["afiliado"],
            "Práctica": caso["practica"],
            "Fecha prestación": caso["fecha_prestacion"],
            "Fecha del débito": caso["fecha_debito"],
            "Monto": caso["monto"],
            "Motivo del rechazo": caso["motivo_texto"],
        }]),
        use_container_width=True, hide_index=True,
        column_config={"Monto": st.column_config.NumberColumn(format="$ %d")},
    )
    st.caption(
        "El sistema no pide un formato nuevo: **toma el lote como se carga hoy**. No exige "
        "columnas adicionales, ni códigos normalizados, ni que nadie cambie su planilla."
    )

    st.write("")

    # ETAPA 2 · Clasificación ------------------------------------------------
    st.markdown("##### Etapa 2 · Clasificación — *Motor de IA*")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Lo que llegó**")
        st.markdown(f'<div class="crudo">{caso["motivo_texto"]}</div>', unsafe_allow_html=True)
        st.caption("Texto libre. Sin formato, sin criterio uniforme, con abreviaturas.")
    with g2:
        st.markdown("**Lo que el sistema entendió**")
        st.markdown(
            f'<div class="limpio"><b>{caso["categoria_nombre"]}</b><br>'
            f'Re facturable: <b>{"Sí" if caso["refacturable"] else "No"}</b> · '
            f'Motor: <b>{caso["motor"]}</b> · Confianza: <b>{caso["confianza"]:.0%}</b>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Las reglas resuelven la mayoría sin conexión. La IA se reserva para lo que "
            "las reglas no reconocen."
        )

    st.write("")

    # ETAPA 3 · Semáforo -----------------------------------------------------
    st.markdown("##### Etapa 3 · Semáforo — *Motor de IA*")
    color_sem = {"VERDE": GREEN, "AMARILLO": AMBER, "ROJO": RED}[caso["recuperabilidad"]]
    icono_sem = {"VERDE": "🟢", "AMARILLO": "🟡", "ROJO": "🔴"}[caso["recuperabilidad"]]
    e1, e2 = st.columns([1, 2])
    kpi(e1, "Estado", f'{icono_sem} {caso["recuperabilidad"]}', caso["via"], color_sem, texto=True)
    with e2:
        st.markdown(f"**Acción que corresponde**")
        st.write(caso["accion"])
        st.caption(f'**Fundamento.** {caso["fundamento"]}')

    st.write("")

    # ETAPA 4 · Cuantificación ----------------------------------------------
    st.markdown("##### Etapa 4 · Cuantificación — *Sistema*")
    # Si el plazo de refacturación ya venció, el reloj que manda es el otro:
    # mostrar "-43 días para presentar" sería contar mal la única cuenta que
    # todavía importa.
    if caso["dias_restantes"] > 0:
        reloj = (f'{caso["dias_restantes"]} días',
                 f'para presentar · vence el {caso["fecha_vencimiento"]:%d/%m/%Y}',
                 AMBER if caso["urgente"] else TXT)
    else:
        reloj = (f'venció hace {abs(caso["dias_restantes"])} días',
                 f'el plazo de refacturación cerró el '
                 f'{caso["fecha_vencimiento"]:%d/%m/%Y}', RED)

    franja([
        (pesos(caso["monto"]), f'importe en juego · {caso["practica"]}', GREEN),
        reloj,
        (f'{caso["dias_sssalud"]} días', "hasta el aniversario de la prestación", MUT),
    ])
    if caso["urgente"]:
        st.warning(
            f'Este caso vence en {caso["dias_restantes"]} días. Sin acción, '
            f'{pesos(caso["monto"])} dejan de ser reclamables.'
        )

    st.write("")

    # ETAPA 5 · Descargo -----------------------------------------------------
    st.markdown("##### Etapa 5 · Descargo — *Motor de IA*")
    st.caption("El sistema redacta. Todavía no presentó nada: esto es un borrador editable.")
    clave_txt = f'texto_{caso["id"]}'
    texto = st.text_area(
        "Borrador del descargo", value=generar_descargo(caso), height=300, key=clave_txt
    )

    st.write("")

    # ETAPA 6 · Aprobación ---------------------------------------------------
    st.markdown("##### Etapa 6 · Aprobación — *Auditor humano*")
    st.caption(
        "Acá se corta la automatización. El sistema **no puede** presentar el descargo por "
        "su cuenta: necesita que una persona lo apruebe, y queda registrado quién y cuándo."
    )

    registro = st.session_state["aprobaciones"].get(caso["id"])
    b1, b2, b3 = st.columns(3)
    if b1.button("✔ Aprobar y firmar", type="primary", use_container_width=True):
        st.session_state["aprobaciones"][caso["id"]] = {
            "estado": "APROBADO", "quien": auditor,
            "cuando": datetime.now().strftime("%d/%m/%Y %H:%M"), "texto": texto,
        }
        st.rerun()
    if b2.button("✎ Devolver para corrección", use_container_width=True):
        st.session_state["aprobaciones"][caso["id"]] = {
            "estado": "EN CORRECCIÓN", "quien": auditor,
            "cuando": datetime.now().strftime("%d/%m/%Y %H:%M"), "texto": texto,
        }
        st.rerun()
    if b3.button("✕ Rechazar la propuesta", use_container_width=True):
        st.session_state["aprobaciones"][caso["id"]] = {
            "estado": "RECHAZADO", "quien": auditor,
            "cuando": datetime.now().strftime("%d/%m/%Y %H:%M"), "texto": texto,
        }
        st.rerun()

    if registro:
        rechazo = " rechazo" if registro["estado"] == "RECHAZADO" else ""
        st.markdown(
            f'<div class="sello{rechazo}"><b>{registro["estado"]}</b> — '
            f'{registro["quien"]} · {registro["cuando"]}<br>'
            f'Expediente {caso["id"]} · {pesos(caso["monto"])}</div>',
            unsafe_allow_html=True,
        )
        if registro["estado"] == "APROBADO":
            st.download_button(
                "Descargar el descargo aprobado",
                data=registro["texto"], file_name=f'descargo-{caso["id"]}.txt',
                mime="text/plain",
            )
    else:
        st.info(
            "Sin aprobación humana, el expediente queda detenido en esta etapa. "
            "Es el estado por defecto, no una excepción."
        )

    aprobados = [a for a in st.session_state["aprobaciones"].values()
                 if a["estado"] == "APROBADO"]
    if aprobados:
        st.caption(f"{len(aprobados)} descargo(s) aprobado(s) en esta sesión.")

    st.write("")

    # ETAPA 7 · Prevención ---------------------------------------------------
    st.markdown("##### Etapa 7 · Prevención — *Sistema*")
    regla = PREVENCION.get(
        caso["categoria"],
        "Revisar en qué punto del circuito se origina esta falla y corregirlo ahí.",
    )
    st.success(f"**La regla que hubiera evitado este débito:** {regla}")
    st.caption(
        "Recuperar sirve una vez. Esta etapa es la que convierte cada rechazo en una "
        "corrección del circuito, para que el próximo no nazca."
    )

st.divider()

# ============================================================================
# El lote completo: la consecuencia agregada de lo anterior.
# ============================================================================
st.subheader("El lote completo")
st.caption(f"Lo mismo, aplicado a los {len(datos)} débitos del lote.")
st.write("")

tarjetas([
    ("Recuperable identificado", pesos(r["recuperable"]),
     f'{r["pct_recuperable"]:.0f}% del total debitado', GREEN),
    ("Débitos analizados", f'{len(datos)}',
     f'{duracion(tiempo)} de procesamiento', TXT),
    ("Vencen en 15 días", f'{r["urgentes_cant"]}',
     f'{pesos(r["urgentes_monto"])} en riesgo', AMBER),
    ("Total debitado", pesos(r["total"]),
     f'{pesos(r["montos"]["ROJO"])} no recuperable', MUT),
])

st.write("")
st.divider()

# ---------------------------------------------------------------- semáforo ---
st.subheader("Semáforo de recuperabilidad")

tarjetas([
    (titulo, pesos(r["montos"][clave]),
     f'{r["cantidades"][clave]} débitos · {desc}', color)
    for clave, titulo, color, desc in [
        ("VERDE", "Recuperable ahora", GREEN, "Falla de forma. Se corrige y se refactura."),
        ("AMARILLO", "Recuperable con acción", AMBER, "Requiere una gestión previa."),
        ("ROJO", "No recuperable", RED, "Sin cobertura, sin plan o plazo vencido."),
    ]
])

st.write("")
st.caption(
    "El corte entre recuperable y no recuperable no es un criterio propio: los manuales de "
    "prestadores que publican las obras sociales ya dividen las causales en **débitos re "
    "facturables** y **no re facturables**. El semáforo refleja esa clasificación."
)

st.write("")

# --------------------------------------------------------- vías de recupero ---
st.subheader("Vías de recupero")
st.caption("Un débito no tiene un solo camino. Tiene tres, y son excluyentes en el tiempo.")

VIAS = [
    (VIA_REFACTURACION, GREEN, "Se corrige el defecto y se vuelve a presentar."),
    (VIA_AUDITORIA, AMBER, "Art. 18 Dec. 939/2000 y art. 14 Res. 487/2002 MS."),
    (VIA_SSSALUD, AMBER, "Venció la refacturación, no el aniversario de la prestación."),
    (VIA_NINGUNA, RED, "Sin camino disponible."),
]

tarjetas([
    (nombre, pesos(r["por_via"].get(nombre, {"monto": 0.0})["monto"]),
     f'{r["por_via"].get(nombre, {"cantidad": 0})["cantidad"]} débitos · {desc}', color)
    for nombre, color, desc in VIAS
])

sss = r["por_via"].get(VIA_SSSALUD)
if sss and sss["cantidad"]:
    st.write("")
    st.info(
        f'**{pesos(sss["monto"])} que un tablero común daría por perdidos.** '
        f'{sss["cantidad"]} débitos tienen vencido el plazo de refacturación, pero siguen '
        "dentro del año aniversario de la prestación: todavía se reclaman ante la "
        "Superintendencia por el Sistema de Débito Automático."
    )

st.write("")
st.divider()

# ============================================================================
# El costo de esperar.
#
# El mismo lote, con el reloj adelantado. No se genera un lote nuevo: se le
# restan días a los plazos de estos mismos débitos y se los vuelve a clasificar
# con el motor de reglas. Es la demostración de que el plazo no es un detalle
# del circuito, es el circuito.
# ============================================================================
st.subheader("El costo de esperar")
st.caption(
    "El mismo lote, con el reloj adelantado. Ningún débito se agrega ni se quita: "
    "solo pasa el tiempo."
)


def adelantar(lote_base, dias):
    """Los mismos débitos, con los plazos corridos hacia adelante."""
    movidos = []
    for d in lote_base:
        e = dict(d)
        e["dias_restantes"] = d["dias_restantes"] - dias
        e["dias_sssalud"] = d["dias_sssalud"] - dias
        movidos.append(e)
    return movidos


crudo = st.session_state.get("lote_crudo", [])

FACIL = "Se arregla con un papel"
AUDIT = "Va a auditoría conjunta"
DURO = "Reclamo ante la SSSalud"
MUERTO = "Ya no se recupera"


def foto(lote_base, dias):
    """Cuánta plata hay en cada camino, con el reloj adelantado `dias`."""
    v = resumen(clasificar_lote(adelantar(lote_base, dias), usar_ia=False))["por_via"]
    g = lambda k: v.get(k, {"monto": 0.0})["monto"]
    return {
        FACIL: g(VIA_REFACTURACION),
        AUDIT: g(VIA_AUDITORIA),
        DURO: g(VIA_SSSALUD),
        MUERTO: g(VIA_NINGUNA),
    }


if crudo:
    dias_adelante = st.slider(
        "Adelantar el reloj", min_value=0, max_value=360, value=0, step=30,
        format="+%d días",
        help="Cuánto tiempo pasa sin que nadie procese estos débitos.",
    )

    # Reclasificar 200 débitos cuesta milisegundos: la curva del año se calcula
    # entera, no de a un punto.
    curva = pd.DataFrame(
        [dict(Días=t, **foto(crudo, t)) for t in range(0, 361, 30)]
    ).set_index("Días")

    hoy_f = foto(crudo, 0)
    ahora = foto(crudo, dias_adelante)

    tarjetas([
        (FACIL, pesos(ahora[FACIL]), f'Eran {pesos(hoy_f[FACIL])} hoy',
         GREEN if ahora[FACIL] else MUT),
        (DURO, pesos(ahora[DURO]), "Vía lenta: hay que ir a la Superintendencia", AMBER),
        (MUERTO, pesos(ahora[MUERTO]),
         f'+{pesos(ahora[MUERTO] - hoy_f[MUERTO])} respecto de hoy',
         RED if ahora[MUERTO] > hoy_f[MUERTO] else MUT),
    ])

    st.write("")
    st.area_chart(curva, height=280, color=[GREEN, AMBER, "#A16207", RED])
    st.write("")

    # Dos muertes distintas, y la primera es la que nadie mira.
    if dias_adelante == 0:
        st.caption(
            "Mové el deslizador. Lo primero que se pierde no es la plata: **es el camino "
            "fácil**. La franja verde es lo que todavía se arregla mandando el papel "
            "corregido."
        )
    elif ahora[FACIL] == 0 and ahora[MUERTO] == hoy_f[MUERTO]:
        st.warning(
            f'**A los {dias_adelante} días no se perdió un peso — y sin embargo ya se '
            f'perdió casi todo.** No queda un solo débito que se resuelva mandando un '
            f'papel corregido: {pesos(ahora[DURO])} pasaron al reclamo ante la '
            f'Superintendencia, que es más lento, más caro y más incierto.'
        )
    elif ahora[MUERTO] > hoy_f[MUERTO]:
        st.error(
            f'**En {dias_adelante} días se pierden '
            f'{pesos(ahora[MUERTO] - hoy_f[MUERTO])} de forma definitiva.** No por una '
            f'decisión de la obra social ni por una discusión clínica: por vencimiento '
            f'de plazo. Ese dinero ya fue devengado por el hospital.'
        )
    else:
        st.info(
            f'A los {dias_adelante} días la plata sigue estando, pero cambió de camino: '
            f'{pesos(hoy_f[FACIL] - ahora[FACIL])} dejaron de resolverse con un papel.'
        )

st.write("")
st.divider()

# ------------------------------------------------------------------ tabla ---
st.subheader("Detalle del lote")

f1, f2, f3 = st.columns([1, 1, 2])
filtro = f1.selectbox("Filtrar por estado", ["Todos", "VERDE", "AMARILLO", "ROJO", "Solo urgentes"])
filtro_via = f2.selectbox(
    "Filtrar por vía",
    ["Todas", VIA_REFACTURACION, VIA_AUDITORIA, VIA_SSSALUD, VIA_NINGUNA],
)
buscar = f3.text_input("Buscar en el motivo de rechazo", placeholder="firma, afiliado, enmienda…")

vista = datos
if filtro == "Solo urgentes":
    vista = [d for d in vista if d["urgente"]]
elif filtro != "Todos":
    vista = [d for d in vista if d["recuperabilidad"] == filtro]
if filtro_via != "Todas":
    vista = [d for d in vista if d["via"] == filtro_via]
if buscar:
    q = buscar.lower()
    vista = [d for d in vista if q in d["motivo_texto"].lower() or q in d["categoria_nombre"].lower()]

if vista:
    df = pd.DataFrame([{
        "ID": d["id"],
        "Obra social": d["obra_social"],
        "Práctica": d["practica"],
        "Monto": d["monto"],
        "Motivo (texto original)": d["motivo_texto"],
        "Categoría detectada": d["categoria_nombre"],
        "Re facturable": "Sí" if d["refacturable"] else "No",
        "Vía": d["via"],
        "Estado": {"VERDE": "🟢", "AMARILLO": "🟡", "ROJO": "🔴"}[d["recuperabilidad"]],
        "Días": d["dias_restantes"],
        "Motor": d["motor"],
    } for d in vista])

    st.dataframe(
        df, use_container_width=True, hide_index=True, height=330,
        column_config={
            "Monto": st.column_config.NumberColumn(format="$ %d"),
            "Re facturable": st.column_config.TextColumn(
                help="Según la clasificación publicada en los manuales de prestadores "
                     "de las obras sociales"),
            "Vía": st.column_config.TextColumn(help="Camino de recupero que corresponde"),
            "Días": st.column_config.NumberColumn(help="Días restantes para presentar el descargo"),
        },
    )
    st.caption(f"{len(vista)} de {len(datos)} débitos")
else:
    st.info("Ningún débito coincide con el filtro.")

st.divider()

# -------------------------------------------------------------- prevención ---
st.subheader("Prevención")
st.caption("Recuperar sirve una vez. Corregir el origen sirve siempre.")

causas = causas_frecuentes(datos, top=5)
st.dataframe(
    pd.DataFrame([{
        "Causa del débito": c["causa"],
        "Casos": c["cantidad"],
        "Monto acumulado": c["monto"],
        "% del lote": c["monto"] / r["total"] * 100 if r["total"] else 0,
    } for c in causas]),
    use_container_width=True, hide_index=True,
    column_config={
        "Monto acumulado": st.column_config.NumberColumn(format="$ %d"),
        "% del lote": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=60),
    },
)

if causas:
    top = causas[0]
    st.success(
        f'**La causa más cara es «{top["causa"]}»**: {top["cantidad"]} casos por '
        f'{pesos(top["monto"])}. Corregir ese punto en el circuito de admisión y carga '
        f'evita la mayor parte de esta pérdida antes de que ocurra.'
    )

st.divider()

# ------------------------------------------------- documentos del circuito ---
st.subheader("Los documentos del circuito")
st.caption(
    "De dónde sale cada dato. Cinco formularios que reproducen la estructura real del papel "
    "que hoy circula entre un hospital público y una obra social."
)

tarjetas([
    (f"Paso {paso}", nombre, quien, GREEN if paso == "5" else TXT, True)
    for paso, nombre, quien in [
        ("1", "Orden de prestación", "Se firma en la ventanilla"),
        ("2", "Planilla de liquidación", "La arma el administrativo"),
        ("3", "Detalle de débitos", "Lo devuelve la auditoría"),
        ("4", "Acta de auditoría conjunta", "Art. 14 Res. 487/2002"),
        ("5", "Nota de descargo", "La genera este sistema"),
    ]
])

st.write("")

with st.expander("Ver los formularios completos"):
    if FORMULARIOS.exists():
        components.html(FORMULARIOS.read_text(encoding="utf-8"), height=700, scrolling=True)
        st.caption(
            "Datos 100 % ficticios. Lo tomado de la realidad es la estructura de cada "
            "formulario, los campos exigidos y las causales de débito, según normativa "
            "pública: Decreto 939/2000 PEN, Resolución 487/2002 MS y los manuales de "
            "prestadores de las obras sociales."
        )
    else:
        st.warning(
            "No se encontró `documentos-reales/formularios-ejemplo.html`. "
            "El resto del sistema funciona igual."
        )

st.divider()

# --------------------------------------------------------------------- pie ---
# Lo último que queda en pantalla si el recorrido termina acá: de dónde salen
# los datos, quién decide y sobre qué normas se apoya todo el circuito.
NORMAS = [
    "Ley Prov. N.º 8491 y Dec. N.º 31/26",
    "Decreto 939/2000 PEN",
    "Resolución 487/2002 MS",
    "Ordenanza municipal de IA · Salta, abril 2026",
]

st.markdown(
    '<div class="pie">'
    + (f'<img src="data:image/png;base64,{base64.b64encode(ISOTIPO.read_bytes()).decode()}"'
       f' alt="RecuperaSalud">' if ISOTIPO.exists() else "")
    + '<div class="nom">Recupera<span>Salud</span></div>'
    + f'<div class="lema">{LEMA}</div>'
    + '<div class="ev" style="margin-top:6px">Hackathon NOA Innova 2026 · Salta</div>'
    + '<div class="ev" style="margin-top:6px">'
      '<a href="https://github.com/hulais05/recuperasalud" target="_blank" '
      'style="color:inherit">Código abierto en GitHub</a></div>'
    + '<div class="reglas">'
      "<b>Datos sintéticos.</b> Sin datos clínicos ni información real de pacientes: "
      "solo campos administrativos.<br>"
      "<b>La IA propone, una persona aprueba.</b> Ningún descargo se presenta sin "
      "firma de un auditor."
      "</div>"
    + '<div style="margin-top:14px">'
    + "".join(f'<span class="norma">{n}</span>' for n in NORMAS)
    + "</div></div>",
    unsafe_allow_html=True,
)
