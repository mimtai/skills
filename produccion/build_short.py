#!/usr/bin/env python3
"""Monta un Short vertical 1080x1920 siguiendo la skill edicion-video-shorts.

Módulos aplicados:
  0  análisis previo (dimensiones, ¿audio real?)
  2  horizontal -> 9:16 con fondo desenfocado (o escala si ya es vertical)
  3  narración completa + recorte a su duración + mejora de voz
  4  subtítulos sincronizados por pausas con palabra resaltada
  5  rótulo tipo noticia (titular, subtítulo, fecha, línea roja)
  7  comprobación final (ffprobe, sonoridad, 3 fotogramas)
El módulo 6 (notas de voz) está en add_voice_notes.py.

BUCLE: si el Short tiene "bucle" en shorts.json, se graba el cierre COMPLETO y el script corta el audio
justo después de "corte_tras" (en el valle de energía más cercano), para que el final enlace con el gancho.
El rótulo queda fijo (sin animación) para que el reinicio no se note. --corte T fuerza el corte en T s; --sin-bucle lo desactiva.

Uso:
  python3 build_short.py --id 2 --video clips/02.mp4 --voz voces/02.mp3 [--ss 2]
  python3 build_short.py --id 2 --video clips/02.mp4 --sin-voz --t 45   (rótulo + subtítulos por longitud)
Opciones: --fondo blur|negro|recorte  --original 0.18 (volumen del sonido original bajo la voz; 0 = quitar)
"""
import argparse, json, os, re, subprocess, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
VOZ_FX = ("highpass=f=80,lowpass=f=12000,afftdn=nf=-25,"
          "acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,"
          "loudnorm=I=-14:TP=-1.5:LRA=7")
AMARILLO, BLANCO, ROJO = "&H00D4FF&", "&HFFFFFF&", "&H1A14D7&"


def run(cmd, capture=False):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERROR en {' '.join(cmd[:3])}…\n{r.stderr[-1500:]}")
    return r.stdout + r.stderr if capture else None


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
               "-show_entries", "format=duration", "-of", "json", path], True)
    j = json.loads(out[out.index("{"):])
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    has_a = any(s["codec_type"] == "audio" for s in j["streams"])
    return (v or {}).get("width"), (v or {}).get("height"), float(j["format"]["duration"]), has_a


def max_volume(path):
    out = run(["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"], True)
    m = re.search(r"max_volume: (-?[\d.]+) dB", out)
    return float(m.group(1)) if m else -91.0


def tramos_de_voz(path, dur, umbral=-38, d=0.18):
    out = run(["ffmpeg", "-i", path, "-af", f"silencedetect=n={umbral}dB:d={d}", "-f", "null", "-"], True)
    ev = re.findall(r"silence_(start|end): ([\d.]+)", out)
    tramos, cur = [], 0.0
    for kind, t in ev:
        t = float(t)
        if kind == "start":
            if t - cur > 0.05:
                tramos.append((cur, t))
        else:
            cur = t
    if dur - cur > 0.05 and (not ev or ev[-1][0] == "end"):
        tramos.append((cur, dur))
    return tramos or [(0.0, dur)]


NUM_RE = re.compile(r"\d")


def peso(palabra):
    w = re.sub(r"[^\wáéíóúüñÁÉÍÓÚÜÑ]", "", palabra)
    n = len(w)
    if NUM_RE.search(w):            # cifras: se pronuncian más largas
        n = len(w) * 4
    elif w.isupper() and 1 < len(w) <= 5:  # siglas: letra a letra
        n = len(w) * 2
    return n + 1.5


def tiempos_palabras(palabras, tramos):
    """Reparte las palabras en el tiempo hablado (tramos con voz), proporcional a su peso.
    Las pausas de puntuación se alinean con los silencios reales."""
    total_voz = sum(e - s for s, e in tramos)
    total_peso = sum(peso(p) for p in palabras)

    def a_real(x):  # x = segundos de voz acumulados -> tiempo real
        for s, e in tramos:
            if x <= e - s:
                return s + x
            x -= e - s
        return tramos[-1][1]

    out, acc = [], 0.0
    for p in palabras:
        dv = peso(p) / total_peso * total_voz
        out.append((a_real(acc), a_real(acc + dv)))
        acc += dv
    return out


def bloques(palabras, max_chars=22, max_lineas=2):
    """Agrupa palabras en bloques de hasta 2 líneas de ~22 caracteres; corta tras puntuación fuerte."""
    res, cur, lineas, linea = [], [], [], ""
    for i, p in enumerate(palabras):
        if linea and len(linea) + 1 + len(p) > max_chars:
            lineas.append(linea); linea = ""
            if len(lineas) == max_lineas:
                res.append(cur); cur, lineas = [], []
        linea = (linea + " " + p).strip()
        cur.append(i)
        if re.search(r"[.?!:]$", p):
            res.append(cur); cur, lineas, linea = [], [], ""
    if cur:
        res.append(cur)
    # evita huérfanas: bloque final de 1 palabra corta -> se une al anterior
    fixed = []
    for b in res:
        if fixed and len(b) == 1 and len(palabras[b[0]]) <= 4 and not re.search(r"[.?!:]$", palabras[fixed[-1][-1]]):
            fixed[-1] += b
        else:
            fixed.append(b)
    return fixed


def ts(t):
    t = max(0, t)
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def esc(t):
    return t.replace("{", "(").replace("}", ")")


def ass_doc(sh, fecha, dur, palabras, tiempos, con_subs=True, bucle=False):
    fin = ts(dur)
    fad1, fad2 = ("", "") if bucle else ("\\fad(250,0)", "\\fad(400,0)")
    mov = "\\pos(540,356)" if bucle else "\\move(-540,356,540,356,0,350)"
    tit = sh["titular"].upper()
    h1 = 86 if len(tit) <= 17 else int(86 * 17 / len(tit))
    L = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "",
         "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         "Style: Box,Arial,10,&H001A14D7,&H001A14D7,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
         f"Style: H1,Inter Display Black,{h1},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,0,0,5,0,0,0,1",
         "Style: H2,Inter Display ExtraBold,56,&H00111111,&H00111111,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,0,0,0,1",
         "Style: Date,Inter SemiBold,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,1,0,0,9,0,0,0,1",
         "Style: Sub,Inter Display ExtraBold,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,2,0,1,6,4,8,0,0,0,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
         f"Dialogue: 0,0:00:00.00,{fin},Date,,0,0,0,,{{\\an9\\pos(1030,190)\\bord0\\shad0}}{esc(fecha)}",
         f"Dialogue: 1,0:00:00.00,{fin},Box,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\c{ROJO}{fad1}}}m 40 300 l 1040 300 l 1040 412 l 40 412{{\\p0}}",
         f"Dialogue: 2,0:00:00.00,{fin},H1,,0,0,0,,{{\\an5{mov}}}{esc(tit)}",
         f"Dialogue: 1,0:00:00.00,{fin},Box,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\c&HFFFFFF&{fad2}}}m 150 420 l 930 420 l 930 500 l 150 500{{\\p0}}",
         f"Dialogue: 2,0:00:00.00,{fin},H2,,0,0,0,,{{\\an5\\pos(540,461){fad2}}}{esc(sh['subtitulo'].upper())}",
         f"Dialogue: 1,0:00:00.00,{fin},Box,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\c{ROJO}}}m 0 1128 l 1080 1128 l 1080 1136 l 0 1136{{\\p0}}"]
    if con_subs:
        bl = bloques(palabras)
        for k, b in enumerate(bl):
            fin_b = tiempos[b[-1]][1]
            sig = tiempos[bl[k + 1][0]][0] if k + 1 < len(bl) else dur
            fin_b = sig if sig - fin_b < 0.8 else min(fin_b + 0.3, sig)
            # partir el bloque en líneas
            lineas, linea = [], []
            for i in b:
                if linea and len(" ".join(palabras[j] for j in linea + [i])) > 22 and len(lineas) < 2:
                    lineas.append(linea); linea = []
                linea.append(i)
            lineas.append(linea)
            for n, i in enumerate(b):
                ini = tiempos[i][0]
                end = tiempos[b[n + 1]][0] if n + 1 < len(b) else fin_b
                txt = "\\N".join("  ".join(
                    (f"{{\\c{AMARILLO}}}{esc(palabras[j])}{{\\c{BLANCO}}}" if j == i else esc(palabras[j]))
                    for j in ln) for ln in lineas)
                L.append(f"Dialogue: 3,{ts(ini)},{ts(end)},Sub,,0,0,0,,{{\\an8\\pos(480,1185)}}{txt}")
    return "\n".join(L) + "\n"


def indice_corte(sh, palabras):
    """Índice de la última palabra de bucle.corte_tras dentro del cierre."""
    obj = sh["bucle"]["corte_tras"].split()
    ini = len(sh["gancho"].split()) + len(sh["cuerpo"].split())
    for i in range(len(palabras) - len(obj), ini - 1, -1):
        if palabras[i:i + len(obj)] == obj:
            return i + len(obj) - 1
    sys.exit(f"ERROR: no encuentro '{sh['bucle']['corte_tras']}' en el cierre del Short {sh['id']}")


def valle_energia(path, est, ventana=0.3):
    """Busca el instante de menor energía (hueco entre palabras) cerca de est."""
    import array, math
    sr = 16000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = array.array("h"); x.frombytes(raw[:len(raw) // 2 * 2])
    hop = sr // 100  # 10 ms
    best, bt = None, est
    t = max(0.0, est - ventana)
    while t <= est + ventana:
        i = int(t * sr); seg = x[i:i + hop * 2]
        if len(seg) < hop:
            break
        e = math.sqrt(sum(v * v for v in seg) / len(seg))
        if best is None or e < best:
            best, bt = e, t + 0.01
        t += 0.01
    return bt


def cadena_video(w, h, fondo):
    if w and h and h > w:  # ya vertical
        return "[0:v]tpad=stop_mode=clone:stop_duration=120,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"
    if fondo == "negro":
        return "[0:v]tpad=stop_mode=clone:stop_duration=120,scale=1080:-2,pad=1080:1920:0:520:black,setsar=1"
    if fondo == "recorte":
        return "[0:v]tpad=stop_mode=clone:stop_duration=120,scale=-2:1920,crop=1080:1920,setsar=1"
    return ("[0:v]tpad=stop_mode=clone:stop_duration=120,split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=40:2,eq=brightness=-0.22[bg];"
            "[b]scale=1080:-2[fg];[bg][fg]overlay=0:520,setsar=1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--video", required=True)
    ap.add_argument("--voz")
    ap.add_argument("--sin-voz", action="store_true")
    ap.add_argument("--t", type=float, help="duración si no hay voz")
    ap.add_argument("--ss", type=float, default=0, help="segundos a saltar al inicio del vídeo")
    ap.add_argument("--fondo", default="blur", choices=["blur", "negro", "recorte"])
    ap.add_argument("--original", type=float, default=0.18)
    ap.add_argument("--umbral", type=float, default=-38)
    ap.add_argument("--corte", type=float, help="fuerza el punto de corte del bucle (s)")
    ap.add_argument("--sin-bucle", action="store_true")
    ap.add_argument("--json", default=os.path.join(AQUI, "shorts.json"))
    ap.add_argument("--out-dir", default=os.path.join(AQUI, "salida"))
    a = ap.parse_args()

    data = json.load(open(a.json, encoding="utf-8"))
    sh = next(s for s in data["shorts"] if s["id"] == a.id)
    fecha = sh.get("fecha", data["fecha_por_defecto"])
    os.makedirs(a.out_dir, exist_ok=True)
    base = os.path.join(a.out_dir, f"short_{a.id:02d}_{sh['slug']}")

    # Paso 0
    w, h, vdur, has_a = probe(a.video)
    mv = max_volume(a.video) if has_a else -91
    silencioso = mv <= -90
    print(f"[0] vídeo {w}x{h}, {vdur:.1f}s, audio={'sí' if has_a else 'no'}, max_volume={mv} dB"
          + ("  -> el vídeo NO tiene sonido real" if has_a and silencioso else ""))

    texto = " ".join([sh["gancho"], sh["cuerpo"], sh["cierre"]])
    palabras = texto.split()

    if a.voz and not a.sin_voz:
        dur = probe(a.voz)[2]
        if vdur - a.ss < dur:
            print(f"AVISO: el vídeo ({vdur - a.ss:.1f}s útiles) es más corto que la voz ({dur:.1f}s); se repetirá el último fotograma.")
        tramos = tramos_de_voz(a.voz, dur, a.umbral)
        tiempos = tiempos_palabras(palabras, tramos)
        cps = len(texto) / sum(e - s for s, e in tramos)
        print(f"[4] {len(tramos)} tramos de voz, {cps:.1f} caracteres/s hablados"
              + ("  (fuera de 15–19: revisa la lectura o el umbral)" if not 13 <= cps <= 21 else ""))
    else:
        dur = a.t or min(vdur - a.ss, 59)
        tramos = [(0.3, dur - 0.5)]
        tiempos = tiempos_palabras(palabras, tramos)

    bucle = bool(sh.get("bucle")) and not a.sin_bucle
    if bucle:
        k = indice_corte(sh, palabras)
        con_voz = a.voz and not a.sin_voz
        if a.corte:
            corte = a.corte
        elif con_voz:
            corte = valle_energia(a.voz, tiempos[k][1])
        else:
            corte = tiempos[k][1] + 0.1
        palabras, tiempos = palabras[:k + 1], [(s0, min(e0, corte)) for s0, e0 in tiempos[:k + 1]]
        dur = corte
        print(f"[bucle] corte tras «{sh['bucle']['corte_tras']}» en {corte:.2f}s -> enlaza con «{sh['bucle']['retoma']}»"
              + ("" if a.corte else "  (si se oye media palabra, ajusta con --corte)"))

    ass = base + ".ass"
    open(ass, "w", encoding="utf-8").write(ass_doc(sh, fecha, dur, palabras, tiempos, bucle=bucle))

    vf = cadena_video(w, h, a.fondo) + f",ass='{ass}',format=yuv420p[v]"
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a.ss), "-t", str(dur), "-i", a.video]
    fc = [vf]
    if a.voz and not a.sin_voz:
        cmd += ["-i", a.voz]
        fade = f",afade=t=out:st={dur - 0.03:.3f}:d=0.03" if bucle else ""
        fc.append(f"[1:a]{VOZ_FX},aresample=44100,aformat=channel_layouts=stereo[vo]")
        if has_a and a.original > 0:
            og = "aresample=44100,aformat=channel_layouts=stereo" if silencioso else \
                 f"loudnorm=I=-16:TP=-2,aresample=44100,aformat=channel_layouts=stereo,volume={a.original}"
            fc.append(f"[0:a]{og}[og]")
            fc.append("[og][vo]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.9" + fade + "[aout]")
        else:
            fc.append("[vo]alimiter=limit=0.9" + fade + "[aout]")
        amap = ["-map", "[aout]"]
    else:
        amap = ["-map", "0:a?", "-c:a", "copy"] if has_a else []
    cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", *amap, "-r", "25",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19"]
    if a.voz and not a.sin_voz:
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    cmd += ["-t", f"{dur:.3f}", "-movflags", "+faststart", base + ".mp4"]
    print("[2-5] renderizando…")
    run(cmd)

    # Paso 7
    w2, h2, d2, _ = probe(base + ".mp4")
    print(f"[7] salida {w2}x{h2}, {d2:.2f}s -> {base}.mp4")
    if a.voz and not a.sin_voz:
        out = run(["ffmpeg", "-i", base + ".mp4", "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"], True)
        I = re.findall(r"I:\s+(-?[\d.]+) LUFS", out)
        P = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)
        print(f"    sonoridad {I[-1] if I else '?'} LUFS (objetivo ≈ -14), pico {P[-1] if P else '?'} dBFS (< -1)")
    for t, n in [(0.15, "inicio"), (d2 / 2, "medio"), (max(0, d2 - 1), "final")]:
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", base + ".mp4", "-frames:v", "1", f"{base}_{n}.jpg"])
    print(f"    fotogramas de control: {base}_inicio.jpg / _medio.jpg / _final.jpg")
    print("    Nota: sincronización por pausas; las frases van exactas y el resaltado palabra a palabra es aproximado.")


if __name__ == "__main__":
    main()
