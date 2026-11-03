#!/usr/bin/env python3
"""Módulo 6 de la skill edicion-video-shorts: notas de voz al inicio y al final.
Uso: python3 add_voice_notes.py video.mp4 salida.mp4 --intro nota_inicio.m4a --outro nota_final.m4a [--duck 0.18]
"""
import argparse, subprocess, json

def dur(p):
    return float(json.loads(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","json",p]))["format"]["duration"])

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--intro"); ap.add_argument("--outro")
ap.add_argument("--duck", type=float, default=0.18)
ap.add_argument("--voice-lufs", type=float, default=-14); ap.add_argument("--bg-lufs", type=float, default=-16)
a = ap.parse_args()

D = dur(a.video); R = 0.15
inputs = ["-i", a.video]; chains = []; mix = ["[bg]"]
VOICE = "highpass=f=80,lowpass=f=12000,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,loudnorm=I={L}:TP=-1.5:LRA=7,aresample=44100,aformat=channel_layouts=stereo"
windows = []; idx = 1
if a.intro:
    di = dur(a.intro); inputs += ["-i", a.intro]; windows.append((0, di))
    chains.append(f"[{idx}:a]{VOICE.format(L=a.voice_lufs)}[vi]"); mix.append("[vi]"); idx += 1
if a.outro:
    do = dur(a.outro); st = max(0, D - do); inputs += ["-i", a.outro]; windows.append((st, D))
    ms = int(st * 1000)
    chains.append(f"[{idx}:a]{VOICE.format(L=a.voice_lufs)},adelay={ms}|{ms}[vo]"); mix.append("[vo]"); idx += 1

d = a.duck; terms = []
for s, e in windows:
    terms.append(f"if(between(t,{s},{e}),{d},if(between(t,{s-R},{s}),1-(t-({s-R}))/{R}*{1-d},if(between(t,{e},{e+R}),{d}+(t-{e})/{R}*{1-d},1)))")
env = "*".join(terms) if terms else "1"
chains.insert(0, f"[0:a]loudnorm=I={a.bg_lufs}:TP=-2,aresample=44100,volume='{env}':eval=frame[bg]")
fc = ";".join(chains) + f";{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.9[aout]"
subprocess.check_call(["ffmpeg","-v","error","-y",*inputs,"-filter_complex",fc,"-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(D),a.out])
print("OK", a.out, round(D,2), [(round(s,2),round(e,2)) for s,e in windows])
