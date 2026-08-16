# Uso diario y personalización

Todo lo que se cambia con frecuencia está en la carpeta `config/`, en archivos
de texto. **No hace falta tocar el código.** Guarda el archivo y reinicia el
bot (`Ctrl + C` y volver a ejecutarlo).

---

## Comandos

| Qué quieres hacer | Comando |
|---|---|
| **Ver el estado y quién espera atención** | `python -m ragnar_agent.cli.estado` |
| Ver las tasas de hoy | `python -m ragnar_agent.cli.demo --tasas` |
| Probar respuestas en la terminal | `python -m ragnar_agent.cli.demo` |
| Conectar / reconectar TikTok | `python -m ragnar_agent.cli.login` |
| Bot de bandeja, sin enviar | `python -m ragnar_agent.cli.run_dm` |
| Bot de bandeja, enviando | `python -m ragnar_agent.cli.run_dm --enviar` |
| Revisar la bandeja una vez | `python -m ragnar_agent.cli.run_dm --una-vez` |
| Ver qué está pasando en pantalla | agregar `--ver` |
| Diagnosticar la bandeja | `python -m ragnar_agent.cli.run_dm --diagnostico` |
| Probar una palabra clave | `python -m ragnar_agent.cli.run_live --probar "yo"` |
| Bot de Live, enviando | `python -m ragnar_agent.cli.run_live --enviar` |

`Ctrl + C` detiene cualquiera de ellos.

---

## `config/negocio.yaml` — qué sabe y cómo habla el bot

### Cambiar el horario

```yaml
horario:
  apertura: "08:00"
  cierre: "17:00"
  dias: [lunes, martes, miercoles, jueves, viernes, sabado]
```

El bot responde siempre, pero fuera de horario agrega el aviso de
`aviso_fuera_de_horario`.

### Cambiar el tono

```yaml
tono:
  estilo: "cercano, cálido y natural — nada formal ni robótico"
  reglas:
    - "Tutea siempre al cliente. Nada de 'usted'."
    - "Respuestas cortas, de 1 a 3 frases."
```

Se puede escribir en lenguaje normal. Ejemplos de reglas que funcionan bien:

- `"Si el cliente escribe en quechua o aymara, responde en español simple."`
- `"Nunca uses más de un emoji por mensaje."`
- `"Si preguntan por la competencia, no la menciones."`

### Agregar una pregunta frecuente

```yaml
faq:
  - pregunta: "¿Aceptan pagos con QR?"
    respuesta: >
      Sí, aceptamos QR de bancos bolivianos. Te pasamos el código al confirmar
      la operación.
```

### Cambiar cuándo se pasa a una persona

```yaml
derivacion_humana:
  motivos:
    - id: llamada
      descripcion: "El cliente pide una llamada telefónica"
```

Para que el bot derive también cuando alguien reclama, agrega:

```yaml
    - id: reclamo
      descripcion: "El cliente tiene un reclamo o dice que no le llegó el dinero"
      ejemplos: ["no me llegó", "reclamo", "me estafaron"]
```

> Cuando el bot deriva, esa conversación queda marcada y **el bot ya no vuelve
> a responderla**. La atiende una persona. Para devolvérsela al bot, ver
> "Reactivar una conversación" más abajo.

---

## `config/tasas.yaml` — el motor de cotización

### De dónde salen las tasas

Por defecto se leen del Google Sheet publicado ("Tasas de cambio 2026 R.C."),
tomando siempre el último valor cargado de cada columna. Se releen cada 5
minutos. **Si actualizas el Sheet, el bot lo toma solo.**

### Cambiar los tramos por monto

**No se tocan aquí: se editan en la hoja.** El bot lee los bloques de la hoja
"TASAS FINALES" y sigue lo que diga:

| Bloque en la hoja | Operación | El intervalo está en |
|---|---|---|
| `BOB/PEN` | bolivianos → soles | bolivianos |
| `PEN/BOB` | soles → bolivianos | soles |
| `BOB/USD` | bolivianos → dólares en Perú | bolivianos |
| `BOB/USD INTERNACIONAL` | bolivianos → dólares por SWIFT | bolivianos |

Cada bloque tiene esta forma, y puedes agregar o quitar filas libremente:

```
BOB/PEN
Intervalos en Bolivianos,,Tasa
0,583,3.49
584,1155,3.48
17186,Superiores,3.43
```

Cambias una tasa en la hoja y, como máximo 5 minutos después, el bot ya cotiza
con la nueva. No hay que reiniciar nada.

> ⚠️ Lo único que **no** hay que cambiar son los títulos de los bloques
> (`BOB/PEN`, `PEN/BOB`, `BOB/USD`, `BOB/USD INTERNACIONAL`): son los que el
> bot busca. Si hay que renombrarlos, se ajusta la lista `tablas:` en
> `config/tasas.yaml`.

### Cambiar el monto mínimo

```yaml
bob_a_pen:
  monto_minimo: 100     # en bolivianos
```

### SWIFT

Ya cotiza automático con la tabla `BOB/USD INTERNACIONAL` de la hoja. No hay
que hacer nada: para cambiar sus tasas se editan los tramos de ese bloque,
igual que los demás.

### Pasar de Google Sheet a Odoo

Cuando estén los accesos de Odoo:

1. Completa `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME` y `ODOO_API_KEY` en `.env`
2. En `config/tasas.yaml` cambia `fuente: sheet_tramos` por `fuente: odoo`
3. Completa `odoo.campos` con el modelo y campo donde viven las tasas

El resto del sistema no cambia: el motor de cotización usa la misma interfaz.

### Si se cae la fuente de tasas

El bot usa automáticamente los valores de la sección `manual:` y avisa en el
log. Conviene actualizar esos valores de vez en cuando como red de seguridad.

---

## `config/live.yaml` — palabras clave y plantillas

### Agregar una palabra clave

```yaml
reglas:
  - id: interes_general
    activa: true
    palabras_clave: ["yo", "yoo", "info", "interesado", "interesada"]
    exacta: true
```

- `exacta: true` → el comentario debe **ser** la palabra ("yo", "¡Yo!", "yo...")
  No dispara con "yo ya cambié ayer". Ideal para palabras cortas.
- `exacta: false` → basta con que la contenga. Úsalo para palabras largas
  ("interesado", "cotización"), nunca para "yo".

No hace falta escribir mayúsculas ni tildes: `"informacion"` ya detecta
"Información", "INFORMACIÓN" e "informacion".

Comprueba siempre una palabra clave nueva antes de usarla en vivo:

```bash
python -m ragnar_agent.cli.run_live --probar "yo ya cambié ayer"
```

### Cambiar las plantillas del DM

```yaml
    plantillas:
      - "¡Hola {nombre}! 👋 Vi tu comentario en el live..."
      - "Hola {nombre} 🙌 Gracias por comentar..."
```

`{nombre}` se reemplaza por el nombre del espectador.

> **Deja siempre 3 o más plantillas.** Se elige una al azar en cada envío.
> Mandar el mismo texto idéntico a 50 personas seguidas es lo que más rápido
> hace que TikTok marque la cuenta como spam.

### Ajustar los límites de envío

```yaml
limites:
  dm_por_hora: 25
  dm_por_dia: 150
  espera_entre_dm: [35, 95]   # segundos, al azar entre esos dos
  no_repetir_horas: 72
```

Los valores por defecto son conservadores a propósito. Subirlos aumenta el
riesgo de restricción de la cuenta — ver [SEGURIDAD.md](SEGURIDAD.md).

---

## El comando del día a día

```bash
python -m ragnar_agent.cli.estado
```

Muestra en una pantalla: de dónde salen las tasas hoy, cuántos mensajes se
enviaron en la última hora y en el día, y **qué clientes están esperando a que
una persona los atienda**, con el resumen de lo que necesita cada uno.

```
  CLIENTES ESPERANDO A UNA PERSONA (1)

    @maria_lp  ·  pide una llamada
      2026-08-15 13:23
      Quiere cambiar 40 mil Bs a soles y pide que la llamen.
```

Cuando un asesor ya atendió a esa persona, devuélvele la conversación al bot:

```bash
python -m ragnar_agent.cli.estado --reactivar maria_lp
```

Mientras una conversación está marcada para atención humana, el bot no
responde ahí — para que no le escriba encima al asesor.

---

## Dónde queda todo

> ⚠️ **No corras el bot de bandeja y el de Live al mismo tiempo.** Comparten
> el mismo navegador y se corrompe la sesión de TikTok. El sistema lo impide
> solo: el segundo avisa que hay otro proceso usando la sesión y no arranca.
> Si alguno se cerró de golpe y quedó trabado, borra `.session/sesion.lock`.

| Archivo | Qué guarda |
|---|---|
| `ragnar_agent.sqlite3` | Conversaciones, mensajes, derivaciones, envíos |
| `.session/sesion.lock` | Marca de "hay un bot corriendo" |
| `.session/tiktok/` | La sesión de TikTok (tratar como una contraseña) |
| `.env` | API keys y configuración privada |
| `diagnostico_bandeja.html` | Sólo si corriste `--diagnostico` |

Para empezar de cero, borra `ragnar_agent.sqlite3`. Se vuelve a crear solo
(se pierde el historial, no la sesión de TikTok).
