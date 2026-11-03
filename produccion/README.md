# Kit de producción · Shorts "Midterms 2026"

Todo lo necesario para montar los 11 Shorts con la skill **edicion-video-shorts** cuando nos conectemos al ordenador.

## Qué hay aquí

| Archivo | Para qué |
|---|---|
| `shorts.json` | **Fuente única**: rótulos, guion, imágenes y datos de subida de cada Short |
| `guiones.md` | Los guiones para leer y grabar (se genera desde el JSON) |
| `textos/NN_*.txt` | Guion de cada Short, una frase por línea (teleprompter) |
| `build_short.py` | Monta el Short con los módulos 0, 2, 3, 4, 5 y 7 de la skill |
| `add_voice_notes.py` | Módulo 6: notas de voz al inicio y al final |
| `make_guiones.py` | Regenera `guiones.md` y `textos/` si cambias el JSON |

## Lo que tienes que preparar (checklist)

Crea esta estructura junto a los scripts:

```
produccion/
  clips/   00.mp4 … 10.mp4   ← un clip de imágenes por Short (horizontal o vertical)
  voces/   00.mp3 … 10.mp3   ← tu voz leyendo GANCHO + CUERPO + CIERRE
```

**Al grabar la voz**
- [ ] Lee el texto **exacto** de `textos/NN_*.txt`: los subtítulos salen de ese texto.
- [ ] Haz una **pausa clara en cada punto** (medio segundo). Así se sincronizan los subtítulos.
- [ ] Ritmo natural, unos 16 caracteres por segundo, lo que da unos 35–42 s por Short.
- [ ] En un lugar silencioso, con el móvil a un palmo. Vale mp3, m4a o wav.
- [ ] Si cambias una palabra al grabar, cámbiala también en `shorts.json`.

**Al preparar los clips**
- [ ] Que duren al menos tanto como la voz (si son más cortos, se congela el último fotograma).
- [ ] Si quieres saltar el principio del clip, usa `--ss` con los segundos.
- [ ] Apunta el crédito de cada imagen (p. ej. "Imágenes: AP / C-SPAN") para la descripción.

**En el ordenador**
- [ ] `ffmpeg` instalado (con libass) y Python 3.
- [ ] Fuentes **Inter / Inter Display** instaladas (gratuitas, rsms.me/inter). Si faltan, se usará otra fuente.

## Comandos

```bash
# Montar un Short (voz completa + rótulo + subtítulos)
python3 build_short.py --id 2 --video clips/02.mp4 --voz voces/02.mp3

# Opciones útiles
#   --ss 2            salta 2 s del inicio del clip
#   --fondo negro     franjas negras en lugar de fondo desenfocado (también: recorte)
#   --original 0      quita el sonido original del clip (por defecto queda al 18 % bajo la voz)
#   --umbral -35      si los subtítulos se desincronizan, prueba -35 o -40

# Sin narración: solo rótulo y subtítulos repartidos por longitud
python3 build_short.py --id 2 --video clips/02.mp4 --sin-voz --t 40

# Módulo 6: solo notas de voz al inicio (gancho) y al final (cierre)
python3 add_voice_notes.py salida/short_02_el_sayed_30_millones.mp4 salida/short_02_final.mp4 \
  --intro voces/02_gancho.m4a --outro voces/02_cierre.m4a

# Montar todos los que tengan clip y voz
for i in $(seq 0 10); do n=$(printf %02d $i); \
  [ -f clips/$n.mp4 ] && [ -f voces/$n.mp3 ] && python3 build_short.py --id $i --video clips/$n.mp4 --voz voces/$n.mp3; done
```

El resultado queda en `salida/`: el `.mp4`, el `.ass` del rótulo y subtítulos, y 3 fotogramas de control (`_inicio`, `_medio`, `_final`). Revisa los fotogramas antes de subir.

## Bucle (Shorts 0, 1, 2, 3, 4 y 7)

La última frase enlaza con el gancho, así que al reiniciarse el Short la frase se completa sola.
- **Graba el cierre completo**, con entonación de que la frase sigue (p. ej. "…Porque Trump hizo campaña…").
- El script **corta el audio justo después** de las palabras de `bucle.corte_tras` (en el hueco entre palabras más cercano), con un microfundido de 30 ms para que no haya clic.
- El rótulo queda **fijo, sin animación de entrada**, para que el salto del final al principio no se note.
- Si el corte se come media palabra o deja aire: `--corte 41.85` (segundos exactos). Para desactivarlo: `--sin-bucle`.
- Consejo visual: que el final del clip se parezca al primer fotograma (mismo plano o misma persona).

| Short | Corte tras… | Enlaza con… |
|---|---|---|
| 0 | "Porque hay" | "Tres preguntas. Una noche…" |
| 1 | "Ya que" | "Prometió no empezar guerras…" |
| 2 | "Volveremos a decir que" | "Le lanzaron treinta millones…" |
| 3 | "¿Acaso" | "¿Lo que empezó en Nueva York…?" |
| 4 | "Porque" | "Republicano y pro-israelí…" |
| 7 | "Porque" | "Trump hizo campaña…" |

## Estado de revisión

- ✅ Revisados: 0, 1, 2, 3, 4 y 7
- ⏳ **Pendientes: 5 y 6**, y después 8, 9 y 10

## Diseño (skill, módulo 5)

- Titular en franja roja `#D7141A` (y 300–412), Inter Display Black 86, en mayúsculas, entrando desde la izquierda.
- Subtítulo en caja blanca (y 420–500), Inter Display ExtraBold 56.
- Fecha arriba a la derecha, Inter SemiBold 40.
- Vídeo centrado (y 520–1128) con línea roja debajo.
- Subtítulos en y=1185, centrados en x=480 para no tapar los botones de Shorts, con la palabra activa en amarillo.

## Probado

Se probó con un clip sintético 1920×1080 y una voz de 9 tramos (Short 4): salida 1080×1920 de 39 s, −13,1 LUFS, pico −3,2 dBFS. El rótulo y los subtítulos se ven bien y respetan las zonas seguras.
