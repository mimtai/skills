# Traspaso a la sesión local (teleport)

Estado al pasar de la nube a local, el 3 de noviembre de 2026. Todo lo anterior está en esta rama (`claude/midterms-foreign-policy-lobbies-fsds43`).

## Carpetas de salida (indicadas por el usuario)

- **Canal en español** → carpeta local **"proyecto canal"**
- **Canal árabe (Mizan)** → carpeta local **"canal arabe"**

Ahí van las imágenes generadas (miniaturas y fotogramas de control) y los Shorts montados. Antes de escribir, hay que localizar las rutas exactas en el equipo y confirmarlas con el usuario. Para montar: `--out-dir "<ruta>/proyecto canal"` o `--out-dir "<ruta>/canal arabe"` con `--lang ar`.

## Tarea en curso: Short nuevo a partir de 2 vídeos

1. https://youtu.be/Xu70SmXBwVA
2. https://youtube.com/shorts/-7kcH-ngq50

Pasos:
1. **Ver los vídeos.** Sacar título, canal, fecha y transcripción, por ejemplo con `yt-dlp --skip-download --write-auto-subs --sub-langs "es.*,en.*,ar.*" <url>` o con la transcripción que pegue el usuario. Desde la nube no se pudo porque YouTube estaba bloqueado.
2. **Comprobar los datos** con búsquedas y fuentes citables. Las cifras van con "según" cuando la fuente es secundaria.
3. **Escribir el guion en español y en árabe** (fusha), con el mismo formato que la serie: rótulo (titular de 20 caracteres como máximo y subtítulo), gancho, cuerpo, cierre en bucle si encaja, imágenes sugeridas y datos de subida. **Puede pasar de 60 s** si la información lo requiere. Añadirlo a `shorts.json` como `id: 11` con su bloque `ar`.
4. **⚠️ Enseñar los textos al usuario y esperar su aprobación antes de montar.**
5. **Montar con la skill `edicion-video-shorts`** usando `build_short.py` (español y `--lang ar`). Revisar los fotogramas de control y enviar los vídeos.
6. **Añadirlo a `calendario.md`.**

## Otros pendientes de la serie

- Short 0: publicar hoy, a las 19:00 en Mizan y a las 20:00 en el canal en español. Límite: 00:30, hora de España.
- Después de la elección hay que actualizar los cierres de los Shorts 1, 2, 3 y 10 (dicen "hoy"), y añadir al 4 el resultado de Rogers, en español y en árabe, manteniendo el bucle.
- Requisitos locales: ffmpeg con libass, Python 3, fuentes Inter / Inter Display y Noto Kufi Arabic (Bold y Black).
- Preferencias editoriales del usuario: ver `research/contraste-texto-externo.md` → "Decisiones editoriales finales". Se admiten frases cargadas si las respalda un dato; "guerra iniciada contra Irán"; MAGA dividido dicho claramente; megadonantes republicanos siempre con "según".
