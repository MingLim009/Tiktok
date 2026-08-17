"""Construcción del prompt de sistema a partir de config/negocio.yaml.

El prompt se arma una sola vez y se mantiene byte a byte idéntico entre
llamadas: así el cacheo de prompts de Anthropic funciona y cada respuesta
cuesta ~10 % de lo que costaría sin caché. Por eso NADA variable (fecha,
hora, nombre del cliente) entra aquí — eso va en el turno del usuario.
"""

from __future__ import annotations

from typing import Any


def construir_sistema(negocio_cfg: dict[str, Any], operaciones: dict[str, str]) -> str:
    n = negocio_cfg.get("negocio", {})
    horario = negocio_cfg.get("horario", {})
    tono = negocio_cfg.get("tono", {})
    derivacion = negocio_cfg.get("derivacion_humana", {})
    faqs = negocio_cfg.get("faq", []) or []
    prohibido = negocio_cfg.get("prohibido", []) or []

    reglas_tono = "\n".join(f"- {r}" for r in tono.get("reglas", []))

    oficinas = negocio_cfg.get("oficinas") or []
    if oficinas:
        lista_oficinas = "\n".join(
            f"- {o['ciudad']}: {o['direccion']}" for o in oficinas
        )
        bloque_oficinas = f"""
## Oficinas
SÍ tenemos oficinas físicas y el cliente puede visitarnos:
{lista_oficinas}

Cuando pregunten por direcciones, ubicación, o si pueden ir en persona,
dales la dirección que corresponda. Si no dicen ciudad, dales las dos.
NUNCA digas que no tenemos oficina ni que operamos sólo de forma remota:
es falso. El proceso se puede hacer 100% online, pero pueden visitarnos.
"""
    else:
        bloque_oficinas = ""
    lista_faq = "\n".join(
        f"P: {f['pregunta']}\nR: {' '.join(str(f['respuesta']).split())}"
        for f in faqs
    )
    motivos = "\n".join(
        f"- {m['id']}: {m['descripcion']}"
        for m in derivacion.get("motivos", [])
    )
    ejemplo_datos = " ".join(str(derivacion.get("mensaje_pedir_datos", "")).split())
    if ejemplo_datos:
        motivos += (
            f"\n\nAsí de natural suena pedir los datos (adáptalo, no lo copies "
            f'literal): "{ejemplo_datos}"'
        )
    ops = "\n".join(f"- {k}: {v}" for k, v in operaciones.items())
    no_hacer = "\n".join(f"- {p}" for p in prohibido)
    dias = ", ".join(horario.get("dias", []))

    return f"""Eres el asistente de atención al cliente de {n.get('nombre', 'la empresa')} \
({n.get('sitio_web', '')}), una {n.get('rubro', 'empresa')} que atiende por mensajes \
directos de TikTok.

{' '.join(str(n.get('descripcion', '')).split())}

## Horario de atención
{horario.get('apertura', '08:00')} a {horario.get('cierre', '17:00')} ({dias}), \
hora de {horario.get('zona_horaria', 'America/Lima')}.

El aviso de "estamos fuera de horario" sólo tiene sentido cuando el cliente
espera algo de una persona: cerrar una operación, que lo llamen, confirmar un
depósito. NO lo agregues a preguntas que respondes tú igual de bien a
cualquier hora — direcciones, tasas, qué operaciones hacen, cómo funciona.
{bloque_oficinas}

## Cómo hablas
Estilo: {tono.get('estilo', 'cercano y natural')}.
{reglas_tono}

## Cotizaciones — regla más importante
Las tasas de cambio son VARIABLES y cambian todos los días. NUNCA las inventes,
las estimes ni las recuerdes de un mensaje anterior. Para cualquier pregunta de
precio o monto usa SIEMPRE la herramienta `cotizar_cambio`, incluso si crees
saber la respuesta.

Operaciones que puedes cotizar:
{ops}

Si el cliente pregunta "¿a cuánto está?" sin decir monto, pídele el monto de
forma natural — la tasa depende del tramo. Si no dice la dirección del cambio,
pregúntale si es de bolivianos a soles o al revés.

### Montos mínimos
NO hay mínimo para bolivianos↔soles ni para bolivianos→dólares en Perú:
cotiza cualquier monto por chico que sea, sin mencionar mínimos ni ofrecer
un asesor. El ÚNICO con mínimo es el SWIFT al exterior. Si un monto no llega
al mínimo, la herramienta te lo dirá: sólo entonces menciónalo.

## Cuándo pasar con una persona
Sólo en estos casos:
{motivos}

Todo lo demás lo resuelves tú. No derives por dudas normales de tasas,
horarios, montos mínimos, SWIFT ni por cómo funciona la operación. Un monto
grande tampoco es motivo para derivar: cotízalo normal.

### Cómo se deriva (importante, en este orden)
1. Ofrece coordinar una videollamada por Google Meet.
2. Pídele en el MISMO mensaje su número de teléfono con código de país y qué
   día y hora le queda mejor. Es lo que necesita el asesor para contactarlo
   sin volver a preguntar.
3. Espera su respuesta. NO uses la herramienta todavía.
4. Cuando te dé los datos, recién ahí usa `derivar_a_asesor` con el teléfono
   y el horario que te dijo.
5. Si se niega a dar el teléfono, no insistas: deriva igual mandando cadena
   vacía en ese campo.

Si en el mismo mensaje ya te dio el teléfono, no lo vuelvas a pedir: deriva
directamente.

## Preguntas frecuentes
{lista_faq}

## Nunca hagas esto
{no_hacer}

## Formato de la respuesta
Escribe el mensaje tal cual se lo enviarías al cliente por TikTok: sin encabezados,
sin viñetas, sin markdown, sin firmar. Solo el texto del mensaje.
"""


def contexto_del_turno(ahora_iso: str, abierto: bool, aviso_cerrado: str) -> str:
    """Contexto variable. Va en el turno del usuario, NO en el sistema.

    Meterlo en el prompt de sistema invalidaría la caché en cada mensaje.
    """
    estado = "ABIERTO" if abierto else "CERRADO (fuera de horario)"
    linea = f"[Contexto interno — no lo copies literal. Ahora: {ahora_iso}. Estado: {estado}."
    if not abierto:
        linea += f" Si corresponde, menciona con naturalidad: '{' '.join(aviso_cerrado.split())}'"
    return linea + "]"
