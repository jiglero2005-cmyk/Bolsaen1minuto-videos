#!/usr/bin/env python3
# Plantilla "Bolsa en 1 Minuto": python3 plantilla.py spec.json salida.mp4
# Requiere: Pillow, ffmpeg, fuente Inter Display (/usr/share/fonts/opentype/inter/) o DejaVu como reserva.
import sys, json, math, os, subprocess, tempfile
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BG = (11, 15, 20); FG = (255, 255, 255); GREEN = (34, 197, 94); RED = (239, 68, 68)
GREY = (148, 163, 184); CARD = (22, 30, 42); TRACK = (30, 41, 59)
FD = "/usr/share/fonts/opentype/inter/"
_fc = {}
def F(w, s):
    k = (w, s)
    if k not in _fc:
        p = FD + f"InterDisplay-{w}.otf"
        if not os.path.exists(p):
            p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if w in ("Bold", "Black", "SemiBold") else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        _fc[k] = ImageFont.truetype(p, s)
    return _fc[k]
def col(c): return {"rojo": RED, "verde": GREEN, "gris": GREY, "blanco": FG}.get(c, FG)
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3

def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def block(im, d, t, t0, y, text, font, color, maxw=880, lh=1.12):
    p = ease((t - t0) / 0.45)
    lines = wrap(d, text, font, maxw)
    h = int(font.size * lh) * len(lines)
    if p <= 0: return y + h
    off, a = int((1 - p) * 40), int(255 * p)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    yy = y
    for ln in lines:
        ld.text((W // 2, yy + off), ln, font=font, fill=color + (a,), anchor="mt"); yy += int(font.size * lh)
    im.alpha_composite(lay)
    return y + h

# ---- tipos de escena (todas las claves de texto en español; sin emojis: la fuente no los dibuja) ----
def e_gancho(im, d, t, s):
    y = block(im, d, t, 0.0, 420, s["linea1"], F("Black", 120), FG)
    if s.get("linea2"): y = block(im, d, t, 0.25, y + 10, s["linea2"], F("Black", 120), FG)
    if t > 0.6:
        p = ease((t - 0.6) / 0.35); pulse = 1 + 0.03 * math.sin(t * 6)
        d.text((W // 2, 1030), s["cifra"], font=F("Black", int(240 * (0.7 + 0.3 * p) * pulse)), fill=col(s.get("color", "rojo")), anchor="mm")
    if s.get("sub"): block(im, d, t, 1.4, 1250, s["sub"], F("Bold", 64), GREY)

def e_texto(im, d, t, s):
    y = block(im, d, t, 0.0, 370, s["titulo"], F("Black", 92), GREEN)
    if s.get("antes"): y = block(im, d, t, 0.5, y + 60, s["antes"], F("Bold", 64), GREY); y -= 40
    y = block(im, d, t, 1.0 if s.get("antes") else 0.5, y + 60, s["cuerpo"], F("Black", 76), FG)
    if s.get("despues"): block(im, d, t, s.get("t_despues", 2.6), y + 70, s["despues"], F("Bold", 58), GREY, maxw=860)

def e_grafico(im, d, t, s):
    block(im, d, t, 0.0, 330, s["titulo"], F("Bold", 58), GREY)
    vals = s["valores"]; color = col(s.get("color", "rojo"))
    lo, hi = min(vals), max(vals); pad = (hi - lo) * 0.25 or 1; lo -= pad; hi += pad
    x0, x1, ytop, ybot = 160, 940, 520, 1300
    Y = lambda v: ybot - (v - lo) / (hi - lo) * (ybot - ytop)
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        d.line([x0, Y(v), x1, Y(v)], fill=TRACK, width=2)
        d.text((x0 - 18, Y(v)), s.get("formato", "{:.0f}").format(v), font=F("Medium", 30), fill=GREY, anchor="rm")
    n = len(vals); upto = 1 + ease((t - 0.4) / 2.2) * (n - 1)
    X = lambda i: x0 + i * (x1 - x0) / (n - 1)
    pts = [(X(i), Y(vals[i])) for i in range(n) if i <= upto]
    k = int(upto)
    if k < n - 1 and upto > k:
        fr = upto - k; pts.append((X(k) + (X(k+1) - X(k)) * fr, Y(vals[k]) + (Y(vals[k+1]) - Y(vals[k])) * fr))
    if len(pts) > 1:
        d.line(pts, fill=color, width=12, joint="curve")
        ex, ey = pts[-1]; d.ellipse([ex-16, ey-16, ex+16, ey+16], fill=color)
        v = vals[0] + (vals[-1] - vals[0]) * ease((t - 1.2) / 1.4) if t > 1.2 else vals[0]
        lab = s.get("etiqueta", "{:.1f}").format(v).replace(".", ",")
        d.text((ex - 10, ey - 70) if vals[-1] <= vals[0] else (ex - 10, ey + 90), lab, font=F("Black", 64), fill=FG, anchor="rs")
    d.text((x0, 1340), s.get("inicio", ""), font=F("Medium", 32), fill=GREY, anchor="lt")
    d.text((x1, 1340), s.get("fin", ""), font=F("Medium", 32), fill=GREY, anchor="rt")

def e_lista(im, d, t, s):
    y = block(im, d, t, 0.0, 360, s["titulo"], F("Black", 92), GREEN) + 60
    for i, tx in enumerate(s["items"][:3]):
        p = ease((t - (0.6 + i * 1.1)) / 0.45)
        if p <= 0: continue
        off = int((1 - p) * 60)
        d.rounded_rectangle([90 - off, y, 990 - off, y + 210], radius=28, fill=CARD)
        d.ellipse([125 - off, y + 55, 225 - off, y + 155], fill=GREEN)
        d.text((175 - off, y + 105), str(i + 1), font=F("Black", 54), fill=BG, anchor="mm")
        lines = wrap(d, tx, F("Bold", 50), 680)[:3]; yy = y + 105 - (len(lines) * 60) // 2
        for ln in lines: d.text((265 - off, yy), ln, font=F("Bold", 50), fill=FG, anchor="lt"); yy += 60
        y += 240

def e_tabla(im, d, t, s):
    y = block(im, d, t, 0.0, 380, s["titulo"], F("Black", 84), FG) + 70
    for i, (nombre, valor, c) in enumerate(s["filas"][:4]):
        p = ease((t - (0.5 + i * 0.5)) / 0.4)
        if p <= 0: y += 180; continue
        a = int(255 * p); lay = Image.new("RGBA", (W, H), (0,0,0,0)); ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle([90, y, 990, y + 150], radius=24, fill=CARD + (a,))
        ld.text((140, y + 75), nombre, font=F("Bold", 60), fill=FG + (a,), anchor="lm")
        ld.text((940, y + 75), valor, font=F("Black", 68), fill=col(c) + (a,), anchor="rm")
        im.alpha_composite(lay); y += 180
    if s.get("nota"): block(im, d, t, 2.4, y + 40, s["nota"], F("Bold", 50), GREY, maxw=860)

def e_leccion(im, d, t, s):
    y = block(im, d, t, 0.0, 360, "LA LECCIÓN", F("Black", 92), GREEN)
    y = block(im, d, t, 0.5, y + 60, s["texto"], F("Black", 76), FG)
    block(im, d, t, 3.2, y + 90, "Sígueme para entender la bolsa en 1 minuto", F("Bold", 56), GREEN, maxw=860)
    d.text((W // 2, 1430), "Contenido informativo, no es asesoramiento financiero", font=F("Medium", 28), fill=GREY, anchor="mm")

TIPOS = {"gancho": e_gancho, "texto": e_texto, "grafico": e_grafico, "lista": e_lista, "tabla": e_tabla, "leccion": e_leccion}

def frame(spec, idx, t):
    escenas = spec["escenas"]; s = escenas[idx]
    start = sum(e["dur"] for e in escenas[:idx]); total = sum(e["dur"] for e in escenas)
    im = Image.new("RGBA", (W, H), BG + (255,)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 10], fill=TRACK); d.rectangle([0, 0, int(W * min(1, (start + t) / total)), 10], fill=GREEN)
    tag = s.get("etiqueta_superior", ""); f = F("Bold", 34)
    if tag:
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle([W//2 - tw/2 - 28, 150, W//2 + tw/2 + 28, 214], radius=32, fill=TRACK)
        d.text((W // 2, 182), tag, font=f, fill=GREY, anchor="mm")
    d.text((W // 2, 1500), spec.get("handle", "@bolsaen1minuto"), font=F("SemiBold", 36), fill=GREY, anchor="mm")
    TIPOS[s["tipo"]](im, d, t, s)
    fade = min(1, (s["dur"] - t) / 0.2) if idx == 0 else min(1, t / 0.2, (s["dur"] - t) / 0.2)
    if fade < 1: im = Image.blend(Image.new("RGBA", (W, H), BG + (255,)), im, max(0, fade))
    return im.convert("RGB")

def render_escena(args):
    spec, idx, out = args
    n = int(round(spec["escenas"][idx]["dur"] * FPS)); tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(frame(spec, idx, i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError("ffmpeg falló en escena %d" % idx)
    os.rename(tmp, out); return out

if __name__ == "__main__":
    if sys.argv[1] == "--still":  # --still spec.json idx t salida.png
        spec = json.load(open(sys.argv[2])); frame(spec, int(sys.argv[3]), float(sys.argv[4])).save(sys.argv[5]); sys.exit()
    spec = json.load(open(sys.argv[1])); out = sys.argv[2]
    tmpd = tempfile.mkdtemp()
    jobs = [(spec, i, os.path.join(tmpd, f"s{i}.mp4")) for i in range(len(spec["escenas"]))]
    with ProcessPoolExecutor() as ex: files = list(ex.map(render_escena, jobs))
    lst = os.path.join(tmpd, "l.txt"); open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
    j = os.path.join(tmpd, "j.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", j], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", j, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", out], check=True)
    print("OK", out)
