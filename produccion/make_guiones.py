#!/usr/bin/env python3
"""Genera guiones.md (para leer y grabar) y textos/NN_*.txt (para el teleprompter) desde shorts.json."""
import json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(AQUI, "shorts.json"), encoding="utf-8"))
os.makedirs(os.path.join(AQUI, "textos"), exist_ok=True)

L = [f"# Guiones · {d['serie']}", "",
     "Generado desde `shorts.json`, así que edita ese archivo y vuelve a ejecutar `python3 make_guiones.py`.", "",
     "Para cada Short: **titular / subtítulo** del rótulo, **gancho, cuerpo y cierre** para grabar seguidos en `voces/NN.mp3`, "
     "y los datos de subida. Duración estimada a 16 caracteres por segundo.", "",
     "**Estado**: ✅ revisados " + ", ".join(str(x["id"]) for x in d["shorts"] if x.get("estado") == "revisado")
     + " · ⏳ pendientes " + ", ".join(str(x["id"]) for x in d["shorts"] if x.get("estado") != "revisado"), ""]
for s in d["shorts"]:
    texto = " ".join([s["gancho"], s["cuerpo"], s["cierre"]])
    nn = f"{s['id']:02d}"
    open(os.path.join(AQUI, "textos", f"{nn}_{s['slug']}.txt"), "w", encoding="utf-8").write(
        s["gancho"] + "\n\n" + s["cuerpo"].replace(". ", ".\n") + "\n\n" + s["cierre"] + "\n")
    marca = "✅" if s.get("estado") == "revisado" else "⏳"
    L += ["---", "", f"## {marca} SHORT {s['id']} · {s['tema']}", "",
          f"**Rótulo** · `{s['titular']}` / `{s['subtitulo']}` · Fecha: `{s.get('fecha', d['fecha_por_defecto'])}`  ",
          f"**Duración estimada**: ~{len(texto) / 16:.0f} s · Archivos: `clips/{nn}.mp4` + `voces/{nn}.mp3`", "",
          f"**GANCHO (0–3 s)**  ", s["gancho"], "",
          f"**CUERPO**  ", s["cuerpo"], "",
          f"**CIERRE**  ", s["cierre"], "",
          *( [f"**🔁 Bucle**: corto el audio tras «{s['bucle']['corte_tras']}», que enlaza con «{s['bucle']['retoma']}».", ""] if s.get("bucle") else [] ),
          f"**Imágenes**: {s['imagenes']}", "",
          "**Subida**",
          f"- Título: `{s['titulo_subida']}`",
          f"- Descripción: {s['descripcion']} {s['hashtags']}",
          f"- Etiquetas: {s['etiquetas']}", ""]
open(os.path.join(AQUI, "guiones.md"), "w", encoding="utf-8").write("\n".join(L))
print("OK guiones.md +", len(d["shorts"]), "textos")
