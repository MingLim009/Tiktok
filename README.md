# Agente de IA para TikTok — Ragnar Capital

Atención automática de clientes en TikTok para una casa de cambio, en dos fases:

- **Fase 1 · Bandeja de mensajes** — lee los DMs, entiende la intención,
  responde con IA usando las tasas del momento y deriva a una persona cuando
  el cliente pide una llamada o una reunión.
- **Fase 2 · TikTok Live** — escucha los comentarios de la transmisión, detecta
  palabras clave (`yo`, `info`, …) y le envía un DM automático a quien comentó.

---

## Arranque rápido

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

copy .env.example .env          # y pegar la ANTHROPIC_API_KEY

python -m ragnar_agent.cli.demo --tasas   # tasas de hoy (sin API key)
python -m ragnar_agent.cli.demo           # probar la conversación
python -m ragnar_agent.cli.login          # conectar TikTok (una sola vez)
python -m ragnar_agent.cli.run_dm         # bot de bandeja, sin enviar
```

Guía completa: **[docs/INSTALACION.md](docs/INSTALACION.md)**

---

## Qué se edita sin tocar código

| Archivo | Contenido |
|---|---|
| [`config/negocio.yaml`](config/negocio.yaml) | Horario, tono, FAQs, cuándo pasar a un humano |
| [`config/tasas.yaml`](config/tasas.yaml) | Fuente de tasas, tramos por monto, mínimos |
| [`config/live.yaml`](config/live.yaml) | Palabras clave, plantillas de DM, límites de envío |
| `.env` | API keys y modo de operación |

Cómo cambiar cada cosa: **[docs/USO.md](docs/USO.md)**

---

## Cómo está armado

```
config/                  ← lo que edita el cliente
src/ragnar_agent/
  rates/                 motor de tasas (Google Sheet · Odoo · manual)
    engine.py            tramos por monto y fórmulas de cotización
    sheet.py             lee el Google Sheet publicado
    odoo.py              lectura por API (pendiente de accesos)
  ai/                    agente de Claude
    prompts.py           prompt de sistema desde negocio.yaml
    tools.py             herramientas: cotizar y derivar
    agent.py             bucle de conversación
  tiktok/                conexión con TikTok
    session.py           sesión de navegador (login guiado)
    dm.py                leer y responder la bandeja
    live.py              comentarios del live y keywords
  safety/limiter.py      límites de envío, esperas, deduplicación
  store/db.py            SQLite: conversaciones, derivaciones, envíos
  cli/                   comandos ejecutables
tests/                   pruebas automáticas
docs/                    instalación, uso y seguridad
```

Cada capa es independiente: cambiar la fuente de tasas de Google Sheet a Odoo,
o el modelo de IA, no obliga a tocar el resto.

---

## Decisiones de diseño

**Las tasas se leen en vivo, no se copian a mano.** El motor toma el último
valor cargado de cada columna del Google Sheet publicado y lo relee cada 5
minutos. Si el Sheet se actualiza, el bot ya responde con la tasa nueva. Si la
fuente falla, usa un respaldo y lo avisa en el log. Odoo queda listo para
enchufarse cuando lleguen los accesos.

**El bot nunca calcula una tasa por su cuenta.** La IA está obligada a llamar
a la herramienta `cotizar_cambio`; los números salen siempre del motor, no del
modelo. Es la única forma de garantizar que no invente un tipo de cambio.

**La contraseña de TikTok no se guarda.** El login se hace una vez a mano en
una ventana de navegador y sólo se conserva la sesión.

**Modo prueba por defecto.** Con `DRY_RUN=true` el bot muestra en pantalla lo
que respondería sin enviar nada. Es lo primero que se corre contra la cuenta
real.

---

## Pruebas

```bash
python -m pytest tests -q
```

77 pruebas: cotizaciones y tramos por monto, respaldo ante caída de la hoja,
detección de palabras clave y falsos positivos, captura de teléfono al agendar
un Meet, y la lectura y respuesta de la bandeja contra una página local que
imita la de TikTok (`tests/fixtures/`).

Esa última tanda necesita Chromium:

```bash
playwright install chromium
```

La prueba más importante es `test_sin_arbitraje`: verifica que un ida y vuelta
BOB → PEN → BOB siempre devuelva menos de lo que entró. Si alguien invierte las
columnas de tasas por error, la casa perdería dinero en cada ciclo y esa prueba
falla antes de que llegue a producción.

---

## Antes de activar el envío real

Lee **[docs/SEGURIDAD.md](docs/SEGURIDAD.md)**. En resumen: TikTok no tiene API
oficial de mensajes y sus términos no permiten el acceso automatizado, así que
existe un riesgo real de restricción de la cuenta. El sistema aplica límites de
volumen, esperas aleatorias y plantillas variadas para reducirlo, pero no puede
eliminarlo.

---

## Pendientes

| Tema | Estado |
|---|---|
| Escala de tramos por monto | ✅ Se lee de la hoja "TASAS FINALES"; 26 tramos en 4 tablas |
| Convención `BOB/PEN` / `PEN/BOB` | ✅ Confirmada por los intervalos de la hoja |
| BOB → USD en Perú | ✅ Cotiza automático (11 tramos) |
| BOB → USD por SWIFT | ✅ Cotiza automático (4 tramos) |
| Conexión con la bandeja de TikTok | Pendiente de una sesión con la cuenta real |
| Odoo | Estructura lista; faltan URL, base, usuario y API key |
