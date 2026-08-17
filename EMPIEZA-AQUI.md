# Empieza aquí

Hola Adderly. Esto es el agente que responde automáticamente los mensajes de
tu bandeja de TikTok.

**No necesitas saber programar ni escribir comandos.** Todo se hace con doble
clic.

## Lo que vas a ver en la carpeta

Los archivos están numerados en el orden en que hay que abrirlos:

```
    1-Empezar-aqui
    2-Poner-mi-clave
    3-Conversar-con-el-bot
    4-Conectar-TikTok
    5-Revisar-bandeja

    Activar-el-bot        (solo cuando ya estés convencido)
    Estado                (el del día a día)
    Actualizar            (cuando te avise que hay versión nueva)
    Diagnostico           (solo si algo falla)
```

Empieza por el **1** y sigue en orden. No hace falta abrir nada más.

> Si usas Windows, los mismos programas están dentro de la carpeta
> `windows`. En Mac ignora esa carpeta por completo.

### Solo la primera vez en Mac

macOS bloquea los archivos descargados de internet. La primera vez que abras
cada uno:

1. **Clic derecho** sobre el archivo (o Control + clic)
2. Elige **Abrir**
3. Si pregunta si estás seguro, confirma **Abrir**

Después de hacerlo una vez, ya funciona con doble clic normal.

> Si haces doble clic directo, macOS te va a preguntar con qué programa
> abrirlo, o te va a decir que es de un desarrollador no identificado. Eso se
> resuelve con el clic derecho → Abrir de arriba. **No elijas ningún programa
> de la lista.**

---

## Paso 1 — Preparar el programa y ver tus tasas

Clic derecho → Abrir en **`1-Empezar-aqui.command`**

La primera vez se demora un par de minutos preparándose. Es normal y pasa una
sola vez. Cuando termine, te muestra tus tasas de hoy, leídas directamente de
tu hoja "TASAS FINALES", con ejemplos de cotización.

Si ves tus tasas ahí, el motor de cálculo está funcionando bien.

---

## Paso 2 — Tu clave de Claude

**No tienes que crear ni abrir ningún archivo.** El paso 1 te la pide en la
misma ventana:

```
  FALTA TU CLAVE DE CLAUDE

  Pega tu clave y presiona ENTER:
```

Copia tu clave de `console.anthropic.com` (Settings → API keys), pégala ahí con
**Command + V** y presiona ENTER. Se guarda sola y no te la vuelve a pedir.

Si te equivocas al pegarla, te avisa y te deja intentarlo otra vez.

> ¿Ya pasaste el paso 1 sin poner la clave? Abre **`2-Poner-mi-clave.command`**
> y te la vuelve a pedir. Puedes abrirlo las veces que quieras.

---

## Paso 3 — Conversar con el bot

Doble clic en **`3-Conversar-con-el-bot.command`**

Escríbele como si fueras un cliente tuyo:

- `a cuánto está el cambio?`
- `quiero cambiar 5000 bolivianos a soles`
- `y si son 300 mil?`
- `hasta qué hora atienden?`
- `me pueden llamar?`

En la última te va a pedir tu número de teléfono y recién ahí pasa la
conversación a un asesor.

---

## Paso 4 — Conectar tu cuenta de TikTok

Doble clic en **`4-Conectar-TikTok.command`**

Se abre una ventana de navegador. Ahí inicias sesión tú mismo, con tu cuenta
de siempre. TikTok te va a mandar un código a tu correo.

Esto se hace **una sola vez**. Tu contraseña no pasa por el programa.

---

## Paso 5 — Ver qué respondería, sin enviar nada

Doble clic en **`5-Revisar-bandeja.command`**

Lee tus mensajes reales y te muestra en pantalla qué le respondería a cada
uno. **No envía nada.** Tus clientes no reciben ningún mensaje.

Si algo no funciona, doble clic en **`Diagnostico.command`** y manda el archivo
`diagnostico_bandeja.txt` que queda en la carpeta.

---

## Paso 6 — Activarlo de verdad (solo cuando estés convencido)

Doble clic en **`Activar-el-bot.command`**

Te pide que escribas `SI` para confirmar, y a partir de ahí el bot revisa
tu bandeja cada 45 segundos y **responde de verdad** a tus clientes.

Para detenerlo: cierra la ventana, o presiona `Control + C`.

> ⚠️ El bot solo responde mientras esa ventana esté abierta y la computadora
> encendida. Si la apagas o se suspende, deja de responder hasta que la vuelvas
> a abrir. Conviene revisar que la computadora no se suspenda sola durante tu
> horario de atención.

---

## Cuando te avise que hay una versión nueva

Doble clic en **`Actualizar.command`**

Descarga la última versión y reemplaza solo los archivos del programa.
**No toca nada tuyo**: tu clave sigue ahí, tu sesión de TikTok sigue ahí (no
hay que volver a iniciar sesión), y el historial tampoco se pierde.

Después abre `1-Empezar-aqui.command` para dejar todo listo.

---

## El día a día

Doble clic en **`Estado.command`**

Te muestra de dónde salen las tasas hoy, cuántos mensajes se enviaron, y sobre
todo **quiénes están esperando que un asesor los llame**, con su teléfono y el
horario que prefieren.

---

## Lo que puedes cambiar tú mismo

Se editan con el Bloc de notas. Guardas y listo.

- **`config/negocio.yaml`** — horario, tono, preguntas frecuentes, cuándo pasar
  a una persona
- **`config/tasas.yaml`** — montos mínimos y de dónde salen las tasas
- **`config/live.yaml`** — palabras clave del Live y los mensajes que se envían

Cada archivo está comentado en español, línea por línea.

**Ejemplo:** para atender hasta las 6 de la tarde, en `config/negocio.yaml`
busca `cierre: "17:00"` y cámbialo por `"18:00"`.

### Las tasas se actualizan solas

El bot lee tu Google Sheet cada 5 minutos. **Si tú cambias una tasa en la hoja,
el bot ya responde con la nueva.** Nadie tiene que copiar nada a mano.

Si algún día la hoja no está disponible, usa una tasa de respaldo conservadora
y lo deja anotado, en vez de quedarse sin responder.

---

## Si quieres profundizar

- **`docs/INSTALACION.md`** — instalación paso a paso
- **`docs/USO.md`** — cómo cambiar cada cosa, con ejemplos
- **`docs/SEGURIDAD.md`** — riesgos, límites de envío y buenas prácticas

**Lee `docs/SEGURIDAD.md` antes de activar el envío real.** Explica de forma
directa el riesgo de que TikTok limite la cuenta y cómo lo reducimos.

---

## Si algo falla

Manda una captura de la ventana completa, con todo lo que aparezca en ella.
Con eso ubico el problema rápido.
