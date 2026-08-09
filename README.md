# RecuperaSalud

**Auditoría asistida de débitos de obras sociales al sistema público de salud.**

Cuando un hospital público atiende a una persona con obra social, tiene derecho a facturarle esa
atención. Una parte importante de ese dinero nunca se cobra, y el motivo casi nunca es médico ni
legal: la obra social rechaza la factura porque falta una firma, un sello o un número de afiliado.
Millones de pesos se pierden por campos vacíos.

RecuperaSalud lee esos rechazos tal como llegan —texto libre, escrito a mano, sin formato—, los
clasifica por recuperabilidad, calcula cuánto dinero hay en juego, redacta el descargo formal y
**se detiene hasta que una persona lo aprueba**.

Prototipo desarrollado durante el **Hackathon NOA Innova 2026** (Salta, 7–9 de agosto de 2026).

---

## ⚠️ Sobre los datos

**Este prototipo funciona íntegramente con datos sintéticos.** No contiene ni procesa información
real de pacientes.

Trabaja únicamente con campos administrativos: identificador de afiliado, prestación, fecha, monto
y motivo de rechazo. **No procesa diagnósticos, historias clínicas ni datos de salud.** La decisión
no es solo ética: reduce la superficie de riesgo y simplifica el marco legal aplicable.

Los motivos de rechazo **no están inventados**: son las causales que las propias obras sociales
publican en sus manuales de prestadores, reescritas con la suciedad de tipeo con la que llegan en
la vida real.

---

## Cómo correrlo

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`. No necesita base de datos, ni credenciales, ni conexión a
internet.

### El motor de IA es opcional

El clasificador tiene dos motores:

| Motor | Cuándo actúa | Por qué |
|---|---|---|
| **Reglas** | Siempre | En una demostración en vivo el wifi se cae. El sistema no puede depender de una API. |
| **IA** | Solo sobre lo que las reglas no reconocen | Es donde un modelo de lenguaje aporta: interpretar lo no previsto. |

El motor de IA se activa solo si existe la variable de entorno `ANTHROPIC_API_KEY`. **Sin ella
todo funciona igual.** La clave nunca se guarda en el repositorio: en local va como variable de
entorno y en Streamlit Cloud, en el gestor de secretos.

---

## Las siete etapas

El recorrido de un débito, y quién interviene en cada paso:

| Etapa | Qué hace | Quién interviene |
|---|---|---|
| 1 · Ingesta | Toma la planilla de rechazos como se carga hoy | Administración |
| 2 · Clasificación | Agrupa los motivos dispersos en categorías comparables | Motor de IA |
| 3 · Semáforo | Recuperable ahora · con acción · perdido | Motor de IA |
| 4 · Cuantificación | Traduce cada categoría a pesos y ordena por urgencia | Sistema |
| 5 · Descargo | Redacta el texto formal de refacturación o recurso | Motor de IA |
| **6 · Aprobación** | **Revisión, edición y firma del reclamo** | **Auditor humano** |
| 7 · Prevención | Devuelve la regla que hubiera evitado el rechazo | Sistema |

**La IA no decide en ninguna etapa.** El expediente se detiene en la etapa 6 y solo avanza cuando
una persona lo aprueba, dejando registro de quién firmó y cuándo.

---

## Las tres vías de recupero

Un débito no tiene un solo camino. Tiene tres, y son excluyentes en el tiempo:

| Vía | Cuándo corresponde | Fundamento |
|---|---|---|
| **Refacturación** | El defecto es de forma y el plazo sigue abierto | Se corrige y se vuelve a presentar |
| **Auditoría conjunta** | El débito no admite refacturación directa | Art. 18 Dec. 939/2000 · art. 14 Res. 487/2002 MS |
| **Reclamo ante la SSSalud** | Venció la refacturación, no el aniversario de la prestación | Res. 487/2002 MS |

Esa tercera vía es la que un tablero común da por perdida. No lo está: mientras no se cumpla el
año aniversario de la prestación, el reclamo sigue vivo.

---

## Estructura

```
app.py                          Interfaz (recorrido de 7 etapas, tablero, semáforo, prevención)
core/datos.py                   Generador de débitos sintéticos con motivos en texto libre sucio
core/clasificador.py            Motor de reglas + motor IA opcional, semáforo, vías, causas
core/descargo.py                Plantillas del descargo formal, según la vía que corresponda
documentos/                     Formularios de ejemplo del circuito (datos 100 % ficticios)
```

---

## Marco normativo

El proyecto no propone una política nueva: ofrece la herramienta para decisiones ya tomadas.

- **Ley Provincial N.º 8491** (Salta, sancionada 01/04/2025) y su **Decreto reglamentario
  N.º 31/26** (BO 27/01/2026) — régimen de recupero de costos sanitarios. Fija 60 días corridos
  desde la facturación y da al certificado de deuda carácter de título ejecutivo.
- **Decreto 939/2000 PEN** — régimen de Hospitales Públicos de Gestión Descentralizada.
- **Resolución 487/2002 MS** — procedimiento, comprobante de atención y auditoría conjunta.
- **Ordenanza municipal de IA** (Salta, abril 2026) — habilita pilotos con IA en la gestión
  pública *"sin sustituir la intervención humana"*.

---

## Alcance y límites

**Dentro del alcance:** la fuga 2 del circuito, la única que puede resolverse con software sin
modificar la conducta de ningún actor — se factura, la obra social audita y rechaza por fallas de
forma.

**Fuera del alcance, declarado:** integración con sistemas reales, datos de pacientes, gestión de
usuarios y permisos, reglas particulares por obra social y validación de padrón en tiempo real.

Sobre la precisión del clasificador: acierta el 100 % sobre el lote sintético, **y eso no es un
resultado**. Los motivos salen de un catálogo conocido y los patrones fueron escritos para él. Es
verificación del circuito, no medición de calidad.

---

Hackathon NOA Innova 2026 · Salta
