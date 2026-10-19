#!/usr/bin/env python3
"""TAPE DECK 90: многооконный кассетный магнитофон (tkinter, без обязательных зависимостей).

Запуск:  python tape_deck.py
Звук:    музыка синтезируется на лету, ничего скачивать не нужно.
         Если установлен pygame (pip install pygame), звук идёт через него (громкость
         меняется без пауз). Иначе используются winsound / afplay / paplay / aplay / ffplay.

Окна:    ПЛЕЕР (кассета с живыми катушками, VU-метры, клавиши), БИБЛИОТЕКА (8 кассет),
         ПЛЕЙЛИСТ (треки стороны A/B), МИКШЕР (ручки Volume/Tone и анализатор спектра).
Клавиши: Space пуск/пауза, S стоп, N/P трек, <-/-> перемотка (зажать), Up/Down громкость,
         F перевернуть кассету, E извлечь, L/T/M окна библиотеки/плейлиста/микшера.
"""
import array
import math
import os
import queue
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
import zlib
import tkinter as tk

try:
    import audioop
except Exception:                                  # Python 3.13+: модуля нет
    audioop = None

# =====================================================================
#                          СИНТЕЗАТОР МУЗЫКИ
# =====================================================================
SR = 16000
SIN = [math.sin(2 * math.pi * i / 1024) for i in range(1024)]
ENV_FPS = 20


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def deg_note(sc, root, d):
    o, i = divmod(d, len(sc))
    return root + sc[i] + 12 * o


def tone(buf, s, n, f, amp, dec, wave_t, att=0):
    """Один голос: 0 пила, 1 меандр, 2 треугольник, 3 синус, 4 пульс 25%."""
    e = min(len(buf), s + n)
    if e <= s:
        return
    inc, ph, k, a = f / SR, 0.0, math.exp(-dec / SR), amp
    for i in range(s, e):
        ph += inc
        q = ph - int(ph)
        if wave_t == 0:
            v = 2 * q - 1
        elif wave_t == 1:
            v = 1.0 if q < .5 else -1.0
        elif wave_t == 2:
            v = 4 * abs(q - .5) - 1
        elif wave_t == 3:
            v = SIN[int(q * 1024)]
        else:
            v = 1.0 if q < .25 else -1.0
        j = i - s
        if att and j < att:
            v *= j / att
        r = e - i
        if r < 80:
            v *= r / 80
        buf[i] += v * a
        a *= k


def kick(buf, s):
    ph, a = 0.0, .95
    for i in range(int(.22 * SR)):
        if s + i >= len(buf):
            break
        ph += (45 + 110 * math.exp(-i / SR * 28)) / SR
        buf[s + i] += SIN[int((ph % 1) * 1024)] * a
        a *= .9992


def snare(buf, s):
    a = 1.0
    for i in range(int(.16 * SR)):
        if s + i >= len(buf):
            break
        nz = random.random() * 2 - 1
        buf[s + i] += (nz * .5 + SIN[int(((190 * i / SR) % 1) * 1024)] * .35) * a
        a *= .9975


def hat(buf, s, open_hat=False):
    last, a = 0.0, .22
    k = .9988 if open_hat else .992
    for i in range(int((.22 if open_hat else .05) * SR)):
        if s + i >= len(buf):
            break
        nz = random.random() * 2 - 1
        buf[s + i] += (nz - last) * a * .5
        last = nz
        a *= k


# стили: темп, лад, аккорды, партии бас/лид/аккомпанемент/пэд, ударные (строки на 16 шагов)
STY = {
    "synthwave": dict(label="Synthwave", bpm=104, sc=[0, 2, 3, 5, 7, 8, 10], prog=[0, 5, 2, 6],
                      bass=dict(w=0, pat="x.x.x.x.x.x.x.x.", a=.20, dec=7, ln=.9),
                      lead=dict(w=4, pat="x.xxx.xxx.xxx.xx", a=.09, dec=8, mode="arp", oc=12),
                      pad=dict(w=0, a=.035, att=3000),
                      dr=dict(k="x...x...x...x...", s="....x.......x...", h="x.x.x.x.x.x.x.x.", o="")),
    "lofi": dict(label="Lo-Fi", bpm=78, sc=[0, 2, 4, 5, 7, 9, 11], prog=[1, 4, 0, 5], sw=.22,
                 bass=dict(w=3, pat="x.....x...x.....", a=.30, dec=4, ln=1.6),
                 comp=dict(w=2, pat="x.....x...x.....", a=.12, dec=3, ln=3, n=4),
                 lead=dict(w=3, pat="..x...x.....x...", a=.12, dec=4, mode="mel", oc=12),
                 dr=dict(k="x.....x...x.....", s="....x.......x...", h="x.xxx.xxx.xxx.xx", o="")),
    "funk": dict(label="Funk", bpm=100, sc=[0, 2, 3, 5, 7, 9, 10], prog=[0, 0, 3, 4],
                 bass=dict(w=1, pat="x..x..x.x..xx.x.", a=.18, dec=10, ln=.8),
                 comp=dict(w=4, pat="..x...x...x..x..", a=.09, dec=16, ln=.9, n=3),
                 lead=dict(w=2, pat="x.x..x.x..x.x...", a=.16, dec=7, mode="mel", oc=12),
                 dr=dict(k="x..x..x...x.x...", s="....x.......x..x", h="xxxxxxxxxxxxxxxx", o="")),
    "ambient": dict(label="Ambient", bpm=58, sc=[0, 2, 3, 7, 8], prog=[0, 2, 1, 3],
                    bass=dict(w=3, pat="x...............", a=.30, dec=.7, ln=15),
                    lead=dict(w=3, pat="x.......x.......", a=.12, dec=1.2, mode="mel", oc=24),
                    pad=dict(w=2, a=.07, att=16000), dr=dict(k="", s="", h="", o="")),
    "chip": dict(label="Chiptune", bpm=140, sc=[0, 2, 4, 5, 7, 9, 11], prog=[0, 4, 5, 3],
                 bass=dict(w=2, pat="x.x.x.x.x.x.x.x.", a=.26, dec=8, ln=.9),
                 lead=dict(w=4, pat="xxxxxxxxxxxxxxxx", a=.10, dec=6, mode="arp", oc=12),
                 dr=dict(k="x...x...x...x...", s="....x.......x...", h="..x...x...x...x.", o="")),
    "disco": dict(label="Disco", bpm=118, sc=[0, 2, 3, 5, 7, 8, 10], prog=[0, 3, 6, 4],
                  bass=dict(w=2, pat="x.xxx.xxx.xxx.xx", a=.30, dec=8, ln=.8, oj=True),
                  comp=dict(w=4, pat="..x...x...x...x.", a=.08, dec=12, ln=1.2, n=3),
                  lead=dict(w=0, pat="x..x..x...x.x...", a=.07, dec=6, mode="mel", oc=12),
                  dr=dict(k="x...x...x...x...", s="....x.......x...", h="xxxxxxxxxxxxxxxx",
                          o="..x...x...x...x.")),
}


def step_n(st):
    return int(SR * 60 / st["bpm"] / 4)


def make_spec(cid, side, i, style):
    seed = zlib.crc32(f"{cid}|{side}|{i}".encode())
    rng, st = random.Random(seed), STY[style]
    bars = max(4, round(rng.randint(26, 34) * st["bpm"] / 240))
    return dict(style=style, seed=seed, root=rng.choice([43, 45, 46, 48, 50, 52]), bars=bars,
                dur=(bars * 16 * step_n(st) + int(1.2 * SR)) / SR)


def render_track(spec):
    """Возвращает (samples int16, длительность, огибающие 6 полос по 20 кадров/с)."""
    st, rng = STY[spec["style"]], random.Random(spec["seed"])
    sn, bars, sc, prog, root = step_n(st), spec["bars"], st["sc"], st["prog"], spec["root"]
    buf = [0.0] * (bars * 16 * sn + int(1.2 * SR))
    swing, m, arp_i, hits = int(sn * st.get("sw", 0)), 4, 0, 0
    for b in range(bars):
        ch = [deg_note(sc, root, prog[b % len(prog)] + k) for k in (0, 2, 4, 6)]
        base = b * 16 * sn
        if "pad" in st:
            p = st["pad"]
            for k in (0, 1, 2):
                tone(buf, base, 16 * sn + 2 * sn, mf(ch[k] + 12), p["a"], .4, p["w"], p["att"])
        for s in range(16):
            t0 = base + s * sn + (swing if s % 2 else 0)
            if "bass" in st and st["bass"]["pat"][s] == "x":
                p = st["bass"]
                up = 12 if p.get("oj") and hits % 2 else 0
                tone(buf, t0, int(sn * p["ln"]), mf(ch[0] - 12 + up), p["a"], p["dec"], p["w"])
                hits += 1
            if "comp" in st and st["comp"]["pat"][s] == "x":
                p = st["comp"]
                for k in range(p["n"]):
                    tone(buf, t0, int(sn * p["ln"]), mf(ch[k]), p["a"], p["dec"], p["w"])
            if "lead" in st and st["lead"]["pat"][s] == "x":
                p = st["lead"]
                if p["mode"] == "arp":
                    nt = ch[(0, 1, 2, 3, 2, 1)[arp_i % 6]] + p["oc"]
                    arp_i += 1
                else:
                    if rng.random() < .22:
                        continue
                    m = max(0, min(9, m + rng.choice((-2, -1, -1, 0, 1, 1, 2))))
                    nt = deg_note(sc, root + p["oc"], m)
                tone(buf, t0, int(sn * 1.6), mf(nt), p["a"], p["dec"], p["w"])
            d = st["dr"]
            if d["k"] and d["k"][s] == "x":
                kick(buf, t0)
            if d["s"] and d["s"][s] == "x":
                snare(buf, t0)
            if d["h"] and d["h"][s] == "x":
                hat(buf, t0)
            if d["o"] and d["o"][s] == "x":
                hat(buf, t0, True)
    peak = max(max(buf), -min(buf)) or 1.0
    g, rnd = .85 / peak, random.random
    out = array.array("h", [int(32000 * max(-1.0, min(1.0, x * g + (rnd() - .5) * .014))) for x in buf])
    for i in range(240):                                    # плавное начало и конец
        out[i] = int(out[i] * i / 240)
        out[-1 - i] = int(out[-1 - i] * i / 240)
    return out, len(out) / SR, analyse(out)


def analyse(out):
    """6 полос частот (однополюсные ФНЧ) по 20 кадров в секунду для VU и спектра."""
    fs = SR / 2
    c = [1 - math.exp(-2 * math.pi * f / fs) for f in (90, 250, 600, 1400, 3000)]
    c0, c1, c2, c3, c4 = c
    l0 = l1 = l2 = l3 = l4 = 0.0
    x, fl, env = out[::2], int(fs / ENV_FPS), []
    for st in range(0, len(x), fl):
        a0 = a1 = a2 = a3 = a4 = a5 = 0.0
        for v in x[st:st + fl]:
            l0 += c0 * (v - l0)
            l1 += c1 * (v - l1)
            l2 += c2 * (v - l2)
            l3 += c3 * (v - l3)
            l4 += c4 * (v - l4)
            a0 += abs(l0)
            a1 += abs(l1 - l0)
            a2 += abs(l2 - l1)
            a3 += abs(l3 - l2)
            a4 += abs(l4 - l3)
            a5 += abs(v - l4)
        env.append((a0, a1, a2, a3, a4, a5))
    mx = [max(e[j] for e in env) or 1.0 for j in range(6)]
    return [tuple((e[j] / mx[j]) ** .7 for j in range(6)) for e in env]


# =====================================================================
#                              ЗВУКОВЫЕ БЭКЕНДЫ
# =====================================================================
def to_bytes(arr):
    if sys.byteorder == "big":
        arr = array.array("h", arr)
        arr.byteswap()
    return arr.tobytes()


class PygameBackend:
    live, name = True, "pygame"

    def __init__(self):
        import pygame
        pygame.mixer.init(SR, -16, 1, 1024, allowedchanges=0)
        if pygame.mixer.get_init()[0] != SR:
            raise RuntimeError("частота")
        self.pg, self.snd = pygame, None

    def play(self, pcm, gain):
        self.stop()
        self.snd = self.pg.mixer.Sound(buffer=pcm)
        self.snd.set_volume(gain)
        self.snd.play()

    def stop(self):
        self.pg.mixer.stop()

    def set_volume(self, g):
        if self.snd:
            self.snd.set_volume(g)


class ExternalBackend:
    live = False

    def __init__(self):
        self.proc, self.n, self.last = None, 0, None
        self.cmd = None
        if sys.platform == "win32":
            self.name = "winsound"
        elif sys.platform == "darwin":
            self.cmd, self.name = ["afplay"], "afplay"
        else:
            for c in (["paplay"], ["aplay", "-q"], ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
                      ["play", "-q"]):
                if shutil.which(c[0]):
                    self.cmd, self.name = c, c[0]
                    break
        if sys.platform != "win32" and not self.cmd:
            raise RuntimeError("нет плеера")

    def play(self, pcm, gain):
        self.stop()
        self.n += 1
        path = os.path.join(tempfile.gettempdir(), f"tapedeck_{os.getpid()}_{self.n % 3}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm)
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            self.proc = subprocess.Popen(self.cmd + [path], stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)

    def stop(self):
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        elif self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.proc = None

    def set_volume(self, g):
        pass


class NullBackend:
    live, name = True, "без звука"

    def play(self, pcm, gain): pass
    def stop(self): pass
    def set_volume(self, g): pass


def make_backend():
    for cls in (PygameBackend, ExternalBackend):
        try:
            return cls()
        except Exception:
            pass
    return NullBackend()


def process(samples, off, gain, tone_v):
    """Срез с позиции off, тембр (ФНЧ) и, если нужно, запечённая громкость."""
    sl = samples[int(off * SR):]
    if tone_v < .98:
        a, y, res = .07 + .93 * tone_v ** 2, 0.0, []
        for v in sl:
            y += a * (v - y)
            res.append(int(y))
        sl = array.array("h", res)
    if gain < .999:
        if audioop and sys.byteorder == "little":
            return audioop.mul(sl.tobytes(), 2, gain)
        sl = array.array("h", [int(v * gain) for v in sl])
    return to_bytes(sl)


# =====================================================================
#                           БИБЛИОТЕКА КАССЕТ
# =====================================================================
BG, PANEL, EDGE, INK, MUTE = "#14161b", "#1c1f26", "#2a2f3a", "#e8ecf4", "#7d8799"
AMBER, RED, BLUE = "#ffb84a", "#e0382d", "#4aa3ff"

CASS = [
    dict(id="d90", brand="TEKNA", model="D 90", sub="HIGH OUTPUT  TYPE I", mins=90, body="#2a2d34",
         label="#f4f1e8", ink="#1a1a1a", stripes=["#e0382d", "#f2a33a", "#e0382d"], layout="stripes",
         tape="#3b2a1e", sides=[dict(style="synthwave", name="Midnight Drive",
                                      tracks=["Neon Boulevard", "Chrome Hearts", "Last Exit 88"]),
                                dict(style="disco", name="Mirror Ball",
                                     tracks=["Glitter Floor", "Saturday Dream", "Last Dance 78"])]),
    dict(id="ur", brand="MAXIM", model="UR 90", sub="NORMAL BIAS  TYPE I", mins=90, body="#15171b",
         label="#d9dce1", ink="#0e0e10", band="#111214", acc="#d8b45a", layout="band",
         tape="#3b2a1e", sides=[dict(style="funk", name="Groove Machine",
                                      tracks=["Slap Alley", "Brass Monkey Jr", "Late Night Walk"]),
                                dict(style="lofi", name="Slow Burn",
                                     tracks=["Vinyl Sunday", "Cigar Smoke", "Sleepy Town"])]),
    dict(id="hf", brand="SONIQ", model="HF 60", sub="HIGH FIDELITY", mins=60, body="#e4e8ee",
         label="#ffffff", ink="#10233f", band="#2f7de1", acc="#ffffff", layout="band",
         tape="#3b2a1e", sides=[dict(style="lofi", name="Rainy Window",
                                      tracks=["Paper Planes", "Coffee Steam", "Bus Stop 5pm"]),
                                dict(style="ambient", name="Cloud Atlas",
                                     tracks=["Slow Cirrus", "Hum of Rain", "Quiet Hours"])]),
    dict(id="chr", brand="BASALT", model="CHROME", sub="TYPE II  70us EQ", mins=90, body="#1d2a3d",
         label="#cdd6e3", ink="#122033", band="#16233a", acc="#e2b64a", layout="band",
         tape="#262a31", sides=[dict(style="ambient", name="Deep Blue",
                                      tracks=["Tidal Memory", "Abyssal Hum", "Blue Hour"]),
                                dict(style="synthwave", name="Night Shift",
                                     tracks=["Harbor Lights", "Steel Rain", "Radio Tower"])]),
    dict(id="memo", brand="MEMORIA", model="RETRO 60", sub="ULTRA DYNAMIC", mins=60, body="#f08a24",
         label="#fff4d6", ink="#5a2a00", stripes=["#e0382d", "#ffd23f", "#2f9e5b"], layout="stripes",
         tape="#3b2a1e", sides=[dict(style="chip", name="Pixel Sunrise",
                                      tracks=["Coin Rush", "Boss Level 3", "Game Over Waltz"]),
                                dict(style="funk", name="Arcade Funk",
                                     tracks=["Joystick Slide", "High Score", "Insert Coin"])]),
    dict(id="neon", brand="NEON-X", model="SYNTH 90", sub="LIMITED EDITION", mins=90, body="#170b2e",
         label="#20103f", ink="#ff4fd8", acc="#37e6ff", layout="neon", tape="#1a1a22",
         sides=[dict(style="synthwave", name="Laser Grid",
                     tracks=["Sunset Horizon", "Turbo Highway", "Laser Grid"]),
                dict(style="chip", name="Cyber Arcade",
                     tracks=["Pixel Rain", "Neon Quest", "Final Boss"])]),
    dict(id="metal", brand="AGATE", model="METAL IV", sub="METAL POSITION", mins=90, body="#0b0b0d",
         label="#151517", ink="#d8b45a", acc="#d8b45a", layout="metal", tape="#1a1a1a",
         sides=[dict(style="disco", name="Gold Rush",
                     tracks=["Velvet Floor", "Nightclub 4AM", "Gold Rush"]),
                dict(style="funk", name="Black Velvet",
                     tracks=["Smoke Signals", "Midnight Strut", "After Hours"])]),
    dict(id="mix", brand="MIXTAPE", model="'89", sub="for you", mins=60, body="#d9d4c4",
         label="#fffef6", ink="#2a3b8f", acc="#c0392b", layout="hand", tape="#3b2a1e",
         sides=[dict(style="lofi", name="songs 4 the bus stop",
                     tracks=["Tape Hiss Lullaby", "Summer in Cassette", "Walkman Girl"]),
                dict(style="ambient", name="B-side: sleep",
                     tracks=["Dream Index", "Soft Static", "Goodnight Reel"])]),
]
for _c in CASS:
    _c["_tr"] = [[dict(title=t, spec=make_spec(_c["id"], si, ti, s["style"]))
                  for ti, t in enumerate(s["tracks"])] for si, s in enumerate(_c["sides"])]


# =====================================================================
#                              РИСОВАНИЕ
# =====================================================================
def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def rrect(c, x0, y0, x1, y1, r, **kw):
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
           x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def oval(c, cx, cy, r, **kw):
    return c.create_oval(cx - r, cy - r, cx + r, cy + r, **kw)


def fmt(t):
    t = max(0, int(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def draw_cassette(c, d, ox, oy, S, ang=(0.0, 0.0), packs=(40, 40), side=0, shadow="#05070a"):
    """Кассета 560x360 в масштабе S: корпус, этикетка (6 стилей), окно с катушками, трапеция."""
    X = lambda v: ox + v * S
    Y = lambda v: oy + v * S
    lw = lambda v: max(1, round(v * S))

    def rr(x0, y0, x1, y1, r, **k):
        return rrect(c, X(x0), Y(y0), X(x1), Y(y1), max(1, r * S), **k)

    def box(x0, y0, x1, y1, **k):
        c.create_rectangle(X(x0), Y(y0), X(x1), Y(y1), **k)

    def tx(x, y, s, sz, col, anchor="w", style="bold", fam="Helvetica"):
        c.create_text(X(x), Y(y), text=s, fill=col, anchor=anchor, font=(fam, max(5, int(sz * S)), style))

    body, lay = d["body"], d["layout"]
    if shadow:
        rr(10, 16, 570, 374, 22, fill=shadow, outline="")
    rr(0, 0, 560, 360, 18, fill=body, outline=mix(body, "#000000", .55), width=lw(2))
    rr(6, 5, 554, 28, 10, fill=mix(body, "#ffffff", .10), outline="")
    for sx, sy in ((22, 22), (538, 22), (22, 338), (538, 338)):
        oval(c, X(sx), Y(sy), 7 * S, fill="#9aa0a8", outline="#50555c")
        c.create_line(X(sx - 4), Y(sy), X(sx + 4), Y(sy), fill="#50555c", width=lw(1.5))

    # ---- этикетка ----
    lab, ink = d["label"], d["ink"]
    rr(34, 36, 526, 216, 8, fill=lab, outline=mix(lab, "#000000", .3), width=lw(1))
    title = d["sides"][side]["name"]
    if lay == "stripes":
        for i, col in enumerate(d["stripes"]):
            box(35, 40 + i * 7, 525, 46 + i * 7, fill=col, outline="")
        tx(52, 78, d["brand"], 24, ink, style="bold italic")
        tx(508, 78, d["model"], 20, ink, "e")
        tx(52, 98, title, 11, ink, style="italic")
    elif lay == "band":
        box(35, 37, 525, 72, fill=d["band"], outline="")
        tx(50, 55, d["brand"], 22, d["acc"], style="bold italic")
        tx(508, 55, d["sub"], 8, d["acc"], "e")
        tx(52, 90, title, 12, ink, style="italic")
        tx(508, 90, d["model"], 16, ink, "e")
    elif lay == "neon":
        box(35, 37, 525, 215, fill=lab, outline="")
        for i, col in enumerate((d["ink"], d["acc"])):
            box(35, 42 + i * 9, 525, 46 + i * 9, fill=col, outline="")
        tx(53, 79, d["brand"], 24, mix(d["ink"], lab, .6), style="bold italic")
        tx(50, 77, d["brand"], 24, d["ink"], style="bold italic")
        tx(508, 79, d["model"], 17, d["acc"], "e")
        tx(52, 98, title, 11, d["acc"], style="italic")
        for i in range(7):
            c.create_line(X(35 + i * 70), Y(215), X(280), Y(180), fill=mix(d["ink"], lab, .65), width=lw(1))
    elif lay == "metal":
        rr(42, 44, 518, 208, 6, fill="", outline=d["acc"], width=lw(1.5))
        rr(48, 50, 512, 202, 4, fill="", outline=mix(d["acc"], lab, .6), width=lw(1))
        tx(62, 74, d["brand"], 22, d["acc"], style="bold")
        tx(498, 74, d["model"], 18, d["acc"], "e")
        tx(62, 96, title, 10, mix(d["acc"], lab, .3), style="italic")
    else:                                                       # hand: тетрадная линейка
        for yy in (50, 66, 82, 98):
            box(35, yy, 525, yy + 1, fill="#bcd3ea", outline="")
        tx(508, 46, d["brand"] + " " + d["model"], 8, "#7a8696", "e")
        tx(50, 76, title, 17, ink, style="italic", fam="Helvetica")
        tx(50, 92, d["sub"], 10, d["acc"], style="italic")
    oval(c, X(76), Y(160), 21 * S, fill="#ffffff", outline=ink, width=lw(1.5))
    tx(76, 160, "AB"[side], 22, ink, "center")
    tx(484, 152, str(d["mins"]), 22, ink, "center")
    tx(484, 176, "MIN", 8, ink, "center")

    # ---- окно с катушками ----
    wbg = mix(body, "#000000", .72)
    rr(120, 106, 440, 208, 24, fill=wbg, outline=mix(body, "#000000", .4), width=lw(2))
    cxs, cy = (200, 360), 157
    tape = d["tape"]
    for k in (0, 1):
        r = max(27, packs[k])
        sgn = -1 if k == 0 else 1
        px, py = cxs[k] + sgn * r * .72, cy + r * .70
        c.create_line(X(px), Y(py), X(150 if k == 0 else 410), Y(208), fill=tape, width=lw(3))
        oval(c, X(cxs[k]), Y(cy), r * S, fill=tape, outline=mix(tape, "#ffffff", .22), width=lw(1.5))
        for a0 in (0, 180):
            rs = (r - 5) * S
            c.create_arc(X(cxs[k]) - rs, Y(cy) - rs, X(cxs[k]) + rs, Y(cy) + rs, start=ang[k] + a0,
                         extent=46, style="arc", outline=mix(tape, "#ffffff", .30), width=lw(2))
        oval(c, X(cxs[k]), Y(cy), 22 * S, fill="#eeeeee", outline="#8a8d92", width=lw(1))
        oval(c, X(cxs[k]), Y(cy), 14.5 * S, fill="#101114", outline="")
        for j in range(6):
            a = math.radians(ang[k] + 60 * j)
            c.create_line(X(cxs[k] + 15.5 * math.cos(a)), Y(cy - 15.5 * math.sin(a)),
                          X(cxs[k] + 9 * math.cos(a)), Y(cy - 9 * math.sin(a)),
                          fill="#eeeeee", width=lw(4), capstyle="butt")
    c.create_line(X(130), Y(115), X(250), Y(115), fill=mix(wbg, "#ffffff", .22), width=lw(2))

    # ---- нижняя трапеция ----
    tc = mix(body, "#000000", .30)
    c.create_polygon(X(100), Y(360), X(138), Y(262), X(422), Y(262), X(460), Y(360), fill=tc,
                     outline=mix(body, "#000000", .55), width=lw(1.5))
    for hx in (172, 388):
        oval(c, X(hx), Y(330), 9 * S, fill=mix(body, "#000000", .8), outline="#50555c")
    for hx in (236, 324):
        oval(c, X(hx), Y(300), 7 * S, fill="#0b0c0e", outline="#50555c")
    box(262, 292, 298, 312, fill="#0b0c0e", outline="#50555c")
    c.create_line(X(150), Y(352), X(410), Y(352), fill=tape, width=lw(5))


# =====================================================================
#                      ВСПОМОГАТЕЛЬНЫЕ ЭЛЕМЕНТЫ UI
# =====================================================================
def draw_icon(c, kind, cx, cy, sz, col):
    def tri(x, dirn):
        c.create_polygon(x - dirn * sz * .5, cy - sz * .6, x + dirn * sz * .5, cy, x - dirn * sz * .5,
                         cy + sz * .6, fill=col, outline="")
    if kind == "play":
        tri(cx, 1)
    elif kind == "pause":
        for dx in (-sz * .45, sz * .15):
            c.create_rectangle(cx + dx, cy - sz * .6, cx + dx + sz * .32, cy + sz * .6, fill=col, outline="")
    elif kind == "stop":
        c.create_rectangle(cx - sz * .5, cy - sz * .5, cx + sz * .5, cy + sz * .5, fill=col, outline="")
    elif kind == "ff":
        tri(cx - sz * .5, 1)
        tri(cx + sz * .5, 1)
    elif kind == "rew":
        tri(cx - sz * .5, -1)
        tri(cx + sz * .5, -1)
    elif kind == "next":
        tri(cx - sz * .25, 1)
        c.create_rectangle(cx + sz * .3, cy - sz * .6, cx + sz * .55, cy + sz * .6, fill=col, outline="")
    elif kind == "prev":
        tri(cx + sz * .25, -1)
        c.create_rectangle(cx - sz * .55, cy - sz * .6, cx - sz * .3, cy + sz * .6, fill=col, outline="")
    elif kind == "eject":
        c.create_polygon(cx - sz * .6, cy + sz * .1, cx, cy - sz * .6, cx + sz * .6, cy + sz * .1,
                         fill=col, outline="")
        c.create_rectangle(cx - sz * .6, cy + sz * .3, cx + sz * .6, cy + sz * .6, fill=col, outline="")


KEYS = ["prev", "rew", "play", "pause", "stop", "ff", "next", "eject"]


class Knob:
    def __init__(self, cx, cy, r, val, label, cb):
        self.cx, self.cy, self.r, self.val, self.label, self.cb = cx, cy, r, val, label, cb

    def hit(self, x, y):
        return math.hypot(x - self.cx, y - self.cy) <= self.r + 14

    def drag(self, x, y):
        a = math.degrees(math.atan2(x - self.cx, -(y - self.cy)))
        a = max(-135, min(135, a)) if abs(a) < 170 else (-135 if a < 0 else 135)
        self.val = (a + 135) / 270
        self.cb(self.val)

    def draw(self, c):
        cx, cy, r = self.cx, self.cy, self.r
        for a0, a1, col, w in ((-135, 135, "#252c3a", 9), (-135, -135 + 270 * self.val, BLUE, 9)):
            if a1 > a0 + .5:
                c.create_arc(cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14, start=90 - a1,
                             extent=a1 - a0, style="arc", outline=col, width=w)
        for i in range(8):
            oval(c, cx, cy, r - i * 2.2, fill=mix("#dfe6f2", "#f8fbff", i / 7), outline="")
        oval(c, cx, cy, r, outline="#9aa8c0", width=2)
        a = math.radians(-135 + 270 * self.val)
        oval(c, cx + math.sin(a) * r * .68, cy - math.cos(a) * r * .68, 6, fill=BLUE, outline="")
        c.create_text(cx, cy + r + 34, text=self.label, fill=MUTE, font=("Helvetica", 10, "bold"))
        c.create_text(cx, cy, text=f"{round(self.val * 100)}", fill="#44516b", font=("Helvetica", 15, "bold"))


# =====================================================================
#                         ДОПОЛНИТЕЛЬНЫЕ ОКНА
# =====================================================================
class Win:
    def __init__(self, deck, title, w, h, x, y):
        self.deck, self.w, self.h = deck, w, h
        self.top = tk.Toplevel(deck)
        self.top.title(title)
        self.top.configure(bg=BG)
        self.top.resizable(False, False)
        self.top.geometry(f"{w}x{h}+{x}+{y}")
        self.top.protocol("WM_DELETE_WINDOW", self.top.withdraw)
        self.cv = tk.Canvas(self.top, width=w, height=h, bg=BG, highlightthickness=0)
        self.cv.pack()

    def visible(self):
        return self.top.state() != "withdrawn"

    def show(self):
        self.top.deiconify()
        self.top.lift()


class LibraryWin(Win):
    CW, CH = 214, 204

    def __init__(self, deck, x, y):
        super().__init__(deck, "Библиотека кассет", 880, 480, x, y)
        self.hover = None
        self.cv.bind("<Motion>", lambda e: self.set_hover(self.index(e.x, e.y)))
        self.cv.bind("<Leave>", lambda e: self.set_hover(None))
        self.cv.bind("<Button-1>", self.click)
        self.draw()

    def index(self, x, y):
        col, row = (x - 16) // self.CW, (y - 56) // self.CH
        i = int(row * 4 + col)
        return i if 0 <= col < 4 and 0 <= row < 2 and 0 <= i < len(CASS) else None

    def set_hover(self, i):
        if i != self.hover:
            self.hover = i
            self.draw()

    def click(self, e):
        i = self.index(e.x, e.y)
        if i is not None:
            self.deck.insert(CASS[i])
            self.draw()

    def draw(self):
        c = self.cv
        c.delete("all")
        c.create_text(20, 28, text="БИБЛИОТЕКА КАССЕТ", anchor="w", fill=AMBER, font=("Helvetica", 18, "bold"))
        c.create_text(860, 28, text="клик по кассете вставляет её в магнитофон", anchor="e", fill=MUTE,
                      font=("Helvetica", 10))
        for i, d in enumerate(CASS):
            x0, y0 = 16 + (i % 4) * self.CW, 56 + (i // 4) * self.CH
            cur = self.deck.cass is d or self.deck.pending is d
            col = AMBER if cur else (BLUE if i == self.hover else EDGE)
            rrect(c, x0, y0, x0 + self.CW - 8, y0 + self.CH - 8, 12, fill=PANEL, outline=col, width=2)
            draw_cassette(c, d, x0 + 10, y0 + 14, .33, packs=(40, 36), shadow=None)
            nm = f"{d['brand']} {d['model']}"
            c.create_text(x0 + 12, y0 + 148, text=nm, anchor="w", fill=INK, font=("Helvetica", 12, "bold"))
            c.create_text(x0 + 12, y0 + 166, anchor="w", fill=MUTE, font=("Helvetica", 9),
                          text=f"A: {STY[d['sides'][0]['style']]['label']}  B: {STY[d['sides'][1]['style']]['label']}")
            if cur:
                c.create_text(x0 + self.CW - 20, y0 + 148, text="В ДЕКЕ", anchor="e", fill=AMBER,
                              font=("Helvetica", 9, "bold"))


class PlaylistWin(Win):
    def __init__(self, deck, x, y):
        super().__init__(deck, "Плейлист", 440, 380, x, y)
        self.cv.bind("<Button-1>", self.click)

    def click(self, e):
        d = self.deck
        if not d.cass:
            return
        if 296 <= e.y <= 340:
            if e.x < 220:
                d.set_side(0)
            else:
                d.set_side(1)
            return
        i = (e.y - 100) // 58
        if 0 <= i < len(d.tracks()):
            d.goto_track(int(i), play=True)

    def draw(self):
        d, c = self.deck, self.cv
        c.delete("all")
        c.create_text(20, 26, text="ПЛЕЙЛИСТ", anchor="w", fill=AMBER, font=("Helvetica", 18, "bold"))
        if not d.cass:
            c.create_text(220, 190, text="Кассета не вставлена", fill=MUTE, font=("Helvetica", 14))
            return
        s = d.cass["sides"][d.side]
        c.create_text(20, 60, text=f"{d.cass['brand']} {d.cass['model']}  ·  сторона {'AB'[d.side]}  ·  {s['name']}",
                      anchor="w", fill=INK, font=("Helvetica", 12, "bold"))
        t = time.time()
        for i, tr in enumerate(d.tracks()):
            y0 = 100 + i * 58
            cur = i == d.idx
            rrect(c, 14, y0, 426, y0 + 50, 10, fill=mix(PANEL, AMBER, .14) if cur else PANEL,
                  outline=AMBER if cur else EDGE, width=2 if cur else 1)
            c.create_text(34, y0 + 25, text=str(i + 1), fill=AMBER if cur else MUTE, font=("Courier", 18, "bold"))
            c.create_text(64, y0 + 18, text=tr["title"], anchor="w", fill=INK, font=("Helvetica", 13, "bold"))
            c.create_text(64, y0 + 36, text=STY[tr["spec"]["style"]]["label"], anchor="w", fill=MUTE,
                          font=("Helvetica", 9))
            c.create_text(412, y0 + 25, text=fmt(tr["spec"]["dur"]), anchor="e", fill=MUTE, font=("Courier", 12))
            if cur:
                for k in range(4):
                    h = 4 + (14 * (.5 + .5 * math.sin(t * (6 + k * 2.3) + k)) if d.state == "playing" else 2)
                    c.create_rectangle(344 + k * 7, y0 + 38 - h, 349 + k * 7, y0 + 38, fill=AMBER, outline="")
                fr = d.pos / tr["spec"]["dur"]
                c.create_rectangle(14, y0 + 47, 14 + 412 * min(1, fr), y0 + 50, fill=AMBER, outline="")
        for k in (0, 1):
            on = d.side == k
            rrect(c, 20 + k * 205, 300, 215 + k * 205, 338, 10, fill=AMBER if on else PANEL,
                  outline=AMBER if on else EDGE, width=2)
            c.create_text(117 + k * 205, 319, text=f"СТОРОНА {'AB'[k]}", fill="#1a1205" if on else MUTE,
                          font=("Helvetica", 12, "bold"))
        c.create_text(220, 362, text="клик по треку: играть · клик по стороне: перевернуть кассету", fill=MUTE,
                      font=("Helvetica", 9))


class MixerWin(Win):
    def __init__(self, deck, x, y):
        super().__init__(deck, "Микшер и спектр", 580, 360, x, y)
        self.knobs = [Knob(110, 160, 62, deck.volume, "VOLUME", deck.set_volume),
                      Knob(290, 175, 40, deck.tone, "TONE", deck.set_tone)]
        self.active = None
        self.cv.bind("<Button-1>", self.down)
        self.cv.bind("<B1-Motion>", self.move)
        self.cv.bind("<ButtonRelease-1>", self.up)

    def down(self, e):
        for k in self.knobs:
            if k.hit(e.x, e.y):
                self.active = k
                k.drag(e.x, e.y)

    def move(self, e):
        if self.active:
            self.active.drag(e.x, e.y)

    def up(self, e):
        self.active = None
        self.deck.knob_released()

    def draw(self):
        d, c = self.deck, self.cv
        c.delete("all")
        c.create_text(20, 26, text="МИКШЕР", anchor="w", fill=AMBER, font=("Helvetica", 18, "bold"))
        self.knobs[0].val, self.knobs[1].val = d.volume, d.tone
        for k in self.knobs:
            k.draw(c)
        c.create_text(380, 26, text="СПЕКТР", anchor="w", fill=AMBER, font=("Helvetica", 12, "bold"))
        names = ("60", "170", "400", "1k", "2k", "4k")
        for j in range(6):
            v = d.bands[j]
            lit = int(v * 14)
            for s in range(14):
                col = "#3ed598" if s < 8 else ("#ffd23f" if s < 12 else RED)
                x0, y0 = 380 + j * 31, 300 - s * 17
                c.create_rectangle(x0, y0, x0 + 24, y0 + 13, fill=col if s < lit else mix(col, BG, .86),
                                   outline="")
            pk = int(d.peaks[j] * 14)
            if pk > 0:
                c.create_rectangle(380 + j * 31, 300 - min(13, pk) * 17, 404 + j * 31, 313 - min(13, pk) * 17,
                                   fill="#ffffff", outline="")
            c.create_text(392 + j * 31, 322, text=names[j], fill=MUTE, font=("Helvetica", 8))
        c.create_text(20, 338, text=f"звук: {d.backend.name}", anchor="w", fill=MUTE, font=("Helvetica", 9))


# =====================================================================
#                              ГЛАВНОЕ ОКНО
# =====================================================================
CW, CH, DW = 680, 322, 680


class Deck(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TAPE DECK 90 · кассетный магнитофон")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.backend = make_backend()
        self.cass, self.pending, self.autoplay = None, None, False
        self.side, self.idx, self.pos, self.state = 0, 0, 0.0, "stopped"
        self.want_play, self.resume, self.held = False, False, None
        self.cache, self.requested = {}, set()
        self.jobs, self.done, self.cnt = queue.PriorityQueue(), queue.Queue(), 0
        self.slide, self.slide_t = 1.0, 1.0
        self.ang, self.rv = [0.0, 0.0], 0.0
        self.vu, self.bands, self.peaks = [0.0, 0.0], [0.0] * 6, [0.0] * 6
        self.volume, self.tone, self.repeat = .8, 1.0, False
        self.play_off = self.play_t0 = 0.0
        self.restart_job, self.frame, self.last = None, 0, time.time()
        self.pressed = None
        threading.Thread(target=self.worker, daemon=True).start()

        self.dp = tk.Canvas(self, width=DW, height=76, bg=BG, highlightthickness=0)
        self.cv = tk.Canvas(self, width=CW, height=CH, bg=BG, highlightthickness=0)
        self.vc = tk.Canvas(self, width=CW, height=128, bg=BG, highlightthickness=0)
        self.pb = tk.Canvas(self, width=CW, height=30, bg=BG, highlightthickness=0)
        self.kc = tk.Canvas(self, width=CW, height=86, bg=BG, highlightthickness=0)
        self.sb = tk.Canvas(self, width=CW, height=42, bg=BG, highlightthickness=0)
        for w in (self.dp, self.cv, self.vc, self.pb, self.kc, self.sb):
            w.pack(padx=10, pady=1)
        self.pb.bind("<Button-1>", self.pb_seek)
        self.pb.bind("<B1-Motion>", self.pb_seek)
        self.kc.bind("<ButtonPress-1>", self.key_down)
        self.kc.bind("<ButtonRelease-1>", self.key_up)
        self.sb.bind("<Button-1>", self.sb_click)
        for k, f in (("<space>", self.toggle), ("s", self.stop), ("n", self.next), ("p", self.prev),
                     ("f", self.flip), ("e", self.eject), ("l", lambda: self.show("lib")),
                     ("t", lambda: self.show("pl")), ("m", lambda: self.show("mx")),
                     ("<Up>", lambda: self.set_volume(self.volume + .05)),
                     ("<Down>", lambda: self.set_volume(self.volume - .05))):
            self.bind_all(k, lambda e, f=f: f())
        self.rel_job = None
        for key, kind in (("Right", "ff"), ("Left", "rew")):
            self.bind_all(f"<KeyPress-{key}>", lambda e, k=kind: self.key_seek(k))
            self.bind_all(f"<KeyRelease-{key}>", lambda e: self.key_seek(None))
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+30+20")
        big = sw >= 1500
        self.win = dict(
            lib=LibraryWin(self, 90 if not big else 760, 80 if not big else 20),
            pl=PlaylistWin(self, max(760, min(1350, sw - 460)) if big else 160, 540 if big else 120),
            mx=MixerWin(self, 760 if big else 200, 540 if big else 160))
        if not big:
            self.win["pl"].top.withdraw()
            self.win["mx"].top.withdraw()
        self.win["lib"].show()
        self.tick()

    # ---------- окна ----------
    def show(self, name):
        self.win[name].show()

    def quit_app(self):
        self.backend.stop()
        self.destroy()

    # ---------- рендер в фоне ----------
    def worker(self):
        while True:
            _, _, key, spec = self.jobs.get()
            try:
                res = render_track(spec)
            except Exception as e:                       # noqa
                res = e
            self.done.put((key, res))

    def tracks(self, c=None, side=None):
        c = c or self.cass
        return c["_tr"][self.side if side is None else side] if c else []

    def key(self, i=None):
        return (self.cass["id"], self.side, self.idx if i is None else i)

    def request(self, i, front=False):
        k = self.key(i)
        if k in self.cache or k in self.requested:
            return
        self.requested.add(k)
        self.cnt += 1
        self.jobs.put((0 if front else 1, self.cnt, k, self.tracks()[i]["spec"]))

    def prefetch(self):
        for i in [self.idx] + [j for j in range(len(self.tracks())) if j != self.idx]:
            self.request(i, front=(i == self.idx))

    def poll(self):
        while not self.done.empty():
            key, res = self.done.get()
            self.requested.discard(key)
            if isinstance(res, Exception):
                continue
            self.cache[key] = res
            if self.cass and key == self.key() and self.state == "loading" and self.want_play:
                self.start_audio(self.pos)

    def trk(self):
        return self.cache.get(self.key()) if self.cass else None

    def dur(self):
        return self.tracks()[self.idx]["spec"]["dur"] if self.cass else 0.0

    # ---------- транспорт ----------
    def insert(self, c):
        if c is self.cass and self.slide < .5:
            return
        self.backend.stop()
        self.state, self.pos, self.want_play = "stopped", 0.0, False
        self.pending, self.slide_t, self.autoplay = c, 1.0, True

    def eject(self):
        self.backend.stop()
        self.state, self.pos, self.want_play = "stopped", 0.0, False
        self.pending, self.slide_t, self.autoplay = None, 1.0, False
        self.show("lib")

    def play(self):
        if not self.cass:
            return self.show("lib")
        self.want_play = True
        if self.trk() is None:
            self.state = "loading"
            self.prefetch()
        else:
            self.start_audio(self.pos)

    def start_audio(self, off):
        tr = self.trk()
        off = max(0.0, min(off, self.dur() - .05))
        self.pos, self.play_off, self.play_t0, self.state = off, off, time.time(), "playing"
        pcm = process(tr[0], off, self.volume if not self.backend.live else 1.0, self.tone)
        self.backend.play(pcm, self.volume)
        self.prefetch()

    def toggle(self):
        if self.state == "playing":
            self.pause()
        elif self.state == "paused":
            self.play()
        else:
            self.play()

    def pause(self):
        if self.state == "playing":
            self.backend.stop()
            self.state, self.want_play = "paused", False
        elif self.state == "paused":
            self.play()

    def stop(self):
        self.backend.stop()
        self.state, self.pos, self.want_play = "stopped", 0.0, False

    def goto_track(self, i, play=False):
        if not self.cass:
            return
        was = self.state in ("playing", "loading") or play
        self.backend.stop()
        self.idx, self.pos = max(0, min(i, len(self.tracks()) - 1)), 0.0
        self.state, self.want_play = "stopped", False
        self.prefetch()
        if was:
            self.play()

    def next(self, auto=False):
        if not self.cass:
            return
        if self.idx + 1 < len(self.tracks()):
            self.goto_track(self.idx + 1, play=auto or self.state in ("playing", "loading"))
        elif auto and self.repeat:
            self.goto_track(0, play=True)
        elif auto:
            self.stop()
            self.idx = 0
        else:
            self.goto_track(0)

    def prev(self):
        if not self.cass:
            return
        if self.pos > 3:
            self.goto_track(self.idx, play=self.state in ("playing", "loading"))
        else:
            self.goto_track(max(0, self.idx - 1), play=self.state in ("playing", "loading"))

    def flip(self):
        if self.cass:
            self.set_side(1 - self.side)

    def set_side(self, s):
        if not self.cass or s == self.side:
            return
        self.backend.stop()
        self.side, self.idx, self.pos = s, 0, 0.0
        self.state, self.want_play = "stopped", False
        self.prefetch()

    def seek_hold(self, kind):
        if not self.cass or self.held:
            return
        self.resume = self.state in ("playing", "loading")
        if self.state == "playing":
            self.backend.stop()
        self.held, self.state, self.want_play = kind, kind, False

    def key_seek(self, kind):
        """Автоповтор клавиш шлёт пары Release/Press: гасим дребезг задержкой."""
        if self.rel_job:
            self.after_cancel(self.rel_job)
            self.rel_job = None
        if kind:
            self.seek_hold(kind)
        else:
            self.rel_job = self.after(90, self.seek_release)

    def seek_release(self):
        if not self.held:
            return
        self.held = None
        if self.resume:
            self.play()
        else:
            self.state = "paused" if self.pos > 0 else "stopped"

    def pb_seek(self, e):
        if not self.cass:
            return
        total = sum(t["spec"]["dur"] for t in self.tracks())
        t = max(0, min(1, (e.x - 20) / (CW - 40))) * total
        acc = 0.0
        for i, tr in enumerate(self.tracks()):
            if t < acc + tr["spec"]["dur"] or i == len(self.tracks()) - 1:
                was = self.state in ("playing", "loading")
                self.backend.stop()
                self.idx, self.pos = i, max(0.0, min(t - acc, tr["spec"]["dur"] - .1))
                self.state, self.want_play = "paused" if self.pos else "stopped", False
                self.prefetch()
                if was:
                    self.play()
                return
            acc += tr["spec"]["dur"]

    def set_volume(self, v):
        self.volume = max(0.0, min(1.0, v))
        self.backend.set_volume(self.volume)
        if not self.backend.live:
            self.schedule_restart()

    def set_tone(self, v):
        self.tone = max(0.0, min(1.0, v))
        self.schedule_restart()

    def knob_released(self):
        self.schedule_restart(150)

    def schedule_restart(self, ms=450):
        if self.restart_job:
            self.after_cancel(self.restart_job)
        self.restart_job = self.after(ms, self.restart_audio)

    def restart_audio(self):
        self.restart_job = None
        if self.state == "playing":
            self.start_audio(self.play_off + time.time() - self.play_t0)

    # ---------- мышь ----------
    def key_rects(self):
        return [(23 + i * 80, 12, 23 + i * 80 + 74, 74) for i in range(8)]

    def key_down(self, e):
        for name, (x0, y0, x1, y1) in zip(KEYS, self.key_rects()):
            if x0 <= e.x <= x1 and y0 <= e.y <= y1:
                self.pressed = name
                if name in ("ff", "rew"):
                    self.seek_hold(name)
                else:
                    {"prev": self.prev, "play": self.play, "pause": self.pause, "stop": self.stop,
                     "next": self.next, "eject": self.eject}[name]()

    def key_up(self, e):
        if self.pressed in ("ff", "rew"):
            self.seek_release()
        self.pressed = None

    def sb_click(self, e):
        for name, x0, x1 in (("lib", 20, 170), ("pl", 180, 330), ("mx", 340, 490)):
            if x0 <= e.x <= x1:
                self.show(name)
        if 500 <= e.x <= 660:
            self.repeat = not self.repeat

    # ---------- такт ----------
    def tick(self):
        now = time.time()
        dt = min(.06, now - self.last)
        self.last = now
        self.frame += 1
        self.poll()
        self.update(dt, now)
        self.draw_deck()
        self.draw_display()
        self.draw_vu()
        if self.frame % 2 == 0:
            self.draw_progress()
            self.draw_keys()
            self.draw_status()
            for w in self.win.values():
                if w.visible() and not isinstance(w, LibraryWin):
                    w.draw()
        self.after(33, self.tick)

    def update(self, dt, now):
        # анимация вставки/извлечения
        if self.slide < self.slide_t:
            self.slide = min(self.slide_t, self.slide + dt * 2.0)
        elif self.slide > self.slide_t:
            self.slide = max(self.slide_t, self.slide - dt * 2.0)
        if self.pending and self.slide >= 1:
            self.cass, self.pending = self.pending, None
            self.side, self.idx, self.pos = 0, 0, 0.0
            self.slide_t = 0.0
            self.prefetch()
            self.win["lib"].draw()
        if self.slide >= 1 and self.pending is None and self.slide_t >= 1 and self.cass:
            self.cass, self.idx, self.pos = None, 0, 0.0
        if self.cass and self.autoplay and self.slide <= 0:
            self.autoplay = False
            self.play()
            self.win["lib"].draw()
        # позиция
        if self.state == "playing":
            self.pos = self.play_off + now - self.play_t0
            if self.pos >= self.dur():
                self.next(auto=True)
        elif self.state == "ff":
            self.pos += 6 * dt
            if self.pos >= self.dur():
                if self.idx + 1 < len(self.tracks()):
                    self.idx, self.pos = self.idx + 1, 0.0
                    self.prefetch()
                else:
                    self.pos = self.dur() - .1
        elif self.state == "rew":
            self.pos -= 6 * dt
            if self.pos <= 0:
                if self.idx > 0:
                    self.idx -= 1
                    self.pos = self.dur() - .2
                    self.prefetch()
                else:
                    self.pos = 0.0
        # катушки: линейная скорость ленты постоянна, значит угловая ~ 1/радиус
        target = {"playing": 1.0, "ff": 7.0, "rew": -7.0, "loading": .5}.get(self.state, 0.0)
        self.rv += (target - self.rv) * min(1.0, dt * (6 if target else 3.0))
        rl, rr = self.packs()
        for k, r in ((0, rl), (1, rr)):
            w = max(-1000, min(1000, 10400 / r * self.rv))
            self.ang[k] = (self.ang[k] + w * dt) % 360
        # VU и спектр
        tr = self.trk()
        bv = (0.0,) * 6
        if self.state == "playing" and tr:
            f = min(len(tr[2]) - 1, int(self.pos * ENV_FPS))
            bv = tr[2][f]
        L = (bv[0] + .9 * bv[1] + .8 * bv[2] + .6 * bv[3] + .4 * bv[4] + .3 * bv[5]) / 4.0
        R = (.3 * bv[0] + .5 * bv[1] + .7 * bv[2] + .9 * bv[3] + bv[4] + bv[5]) / 4.4
        for k, lv in ((0, L), (1, R)):
            db = 20 * math.log10(max(lv * 1.15, 1e-3))
            tgt = max(0.0, min(1.0, (db + 20) / 23))
            self.vu[k] += (tgt - self.vu[k]) * (.40 if tgt > self.vu[k] else .10)
        for j in range(6):
            self.bands[j] += (bv[j] - self.bands[j]) * (.6 if bv[j] > self.bands[j] else .25)
            self.peaks[j] = max(self.bands[j], self.peaks[j] - dt * .6)

    def packs(self):
        if not self.cass:
            return 40.0, 40.0
        trs = self.tracks()
        total = sum(t["spec"]["dur"] for t in trs) or 1.0
        done = sum(t["spec"]["dur"] for t in trs[:self.idx]) + self.pos
        p = max(0.0, min(1.0, done / total))
        return 46 - 19 * p, 27 + 19 * p

    # ---------- отрисовка ----------
    def draw_deck(self):
        c = self.cv
        c.delete("all")
        rrect(c, 4, 2, CW - 4, CH - 2, 18, fill="#0b0d11", outline=EDGE, width=2)
        for i in range(0, CW, 12):                                  # лёгкая «решётка» динамика
            c.create_line(i, 6, i, 10, fill="#161a21")
        if self.cass is None:
            c.create_text(CW / 2, CH / 2 - 10, text="КАССЕТА НЕ ВСТАВЛЕНА", fill=MUTE,
                          font=("Helvetica", 20, "bold"))
            c.create_text(CW / 2, CH / 2 + 22, text="откройте библиотеку (L) и выберите кассету", fill=MUTE,
                          font=("Helvetica", 11))
            return
        rl, rr = self.packs()
        S = .84
        oy = 16 + smooth(self.slide) * (CH + 20)
        jit = .6 * math.sin(self.frame * 1.7) if self.state == "playing" else 0
        draw_cassette(c, self.cass, (CW - 560 * S) / 2, oy + jit, S, ang=self.ang, packs=(rl, rr), side=self.side)

    def draw_display(self):
        c = self.dp
        c.delete("all")
        rrect(c, 4, 4, DW - 4, 72, 14, fill="#0b0d11", outline=EDGE, width=2)
        names = dict(playing="PLAY", paused="PAUSE", stopped="STOP", ff="FF >>", rew="<< REW", loading="LOADING")
        tot = sum(t["spec"]["dur"] for t in self.tracks()[:self.idx]) + self.pos if self.cass else 0
        c.create_rectangle(18, 14, 94, 62, fill="#050608", outline="#2b2f3a")
        c.create_text(56, 38, text=f"{int(tot * 1.9) % 1000:03d}", fill=AMBER, font=("Courier", 26, "bold"))
        t = self.tracks()[self.idx] if self.cass else None
        top = f"{t['title']}" if t else "TAPE DECK 90"
        sub = (f"{self.cass['brand']} {self.cass['model']}  ·  SIDE {'AB'[self.side]}  ·  "
               f"TRK {self.idx + 1}/{len(self.tracks())}") if self.cass else "insert cassette"
        c.create_text(112, 28, text=top.upper(), anchor="w", fill=AMBER, font=("Courier", 17, "bold"))
        c.create_text(112, 52, text=sub, anchor="w", fill=mix(AMBER, "#000000", .35), font=("Courier", 10))
        c.create_text(DW - 24, 24, text=names.get(self.state, ""), anchor="e", fill=RED if self.state == "playing"
                      else AMBER, font=("Courier", 14, "bold"))
        c.create_text(DW - 24, 50, text=f"{fmt(self.pos)} / {fmt(self.dur())}", anchor="e", fill=AMBER,
                      font=("Courier", 16, "bold"))

    def draw_vu(self):
        c = self.vc
        c.delete("all")
        for k in (0, 1):
            x0 = 14 + k * 340
            cx, cyy = x0 + 156, 140                       # ось стрелки (ниже стекла)
            rrect(c, x0, 4, x0 + 312, 124, 14, fill="#0b0d11", outline=EDGE, width=2)
            rrect(c, x0 + 8, 10, x0 + 304, 116, 10, fill="#f1e5b6", outline="#b9a96a", width=2)
            f0 = 20 / 23                                  # положение 0 dB на шкале
            c.create_arc(cx - 102, cyy - 102, cx + 102, cyy + 102, start=42, extent=96, style="arc",
                         outline="#3a3a30", width=2)
            c.create_arc(cx - 100, cyy - 100, cx + 100, cyy + 100, start=42, extent=96 * (1 - f0),
                         style="arc", outline=RED, width=6)
            for db, lab in ((-20, "20"), (-10, "10"), (-7, "7"), (-5, "5"), (-3, "3"), (0, "0"), (3, "+3")):
                a = math.radians(-48 + 96 * (db + 20) / 23)
                col = RED if db >= 0 else "#3a3a30"
                c.create_line(cx + math.sin(a) * 94, cyy - math.cos(a) * 94, cx + math.sin(a) * 106,
                              cyy - math.cos(a) * 106, fill=col, width=2)
                c.create_text(cx + math.sin(a) * 82, cyy - math.cos(a) * 82, text=lab, fill=col,
                              font=("Helvetica", 9, "bold"))
            c.create_text(cx, 36, text="VU", fill="#3a3a30", font=("Helvetica", 15, "bold"))
            c.create_text(x0 + 26, 96, text="LR"[k], fill="#3a3a30", font=("Helvetica", 12, "bold"))
            a = math.radians(-48 + 96 * self.vu[k])
            c.create_line(cx + math.sin(a) * 30, cyy - math.cos(a) * 30, cx + math.sin(a) * 108,
                          cyy - math.cos(a) * 108, fill="#15120a", width=2)
            c.create_rectangle(x0 + 8, 102, x0 + 304, 118, fill="#0b0d11", outline="")
            rrect(c, x0 + 8, 10, x0 + 304, 116, 10, fill="", outline="#b9a96a", width=2)
            c.create_rectangle(x0 + 120, 96, x0 + 192, 106, fill="#15120a", outline="")

    def draw_progress(self):
        c = self.pb
        c.delete("all")
        rrect(c, 20, 10, CW - 20, 20, 5, fill="#0b0d11", outline=EDGE)
        if not self.cass:
            return
        trs = self.tracks()
        total = sum(t["spec"]["dur"] for t in trs)
        done = sum(t["spec"]["dur"] for t in trs[:self.idx]) + self.pos
        w = CW - 40
        rrect(c, 20, 10, 20 + max(10, w * done / total), 20, 5, fill=AMBER, outline="")
        acc = 0.0
        for t in trs[:-1]:
            acc += t["spec"]["dur"]
            c.create_line(20 + w * acc / total, 7, 20 + w * acc / total, 23, fill=MUTE)
        oval(c, 20 + w * done / total, 15, 8, fill="#f4f1e8", outline="#8a8d92", width=2)

    def draw_keys(self):
        c = self.kc
        c.delete("all")
        lit = {"play": self.state in ("playing", "loading"), "pause": self.state == "paused",
               "ff": self.state == "ff", "rew": self.state == "rew"}
        for name, (x0, y0, x1, y1) in zip(KEYS, self.key_rects()):
            dn = self.pressed == name or lit.get(name)
            o = 3 if dn else 0
            rrect(c, x0, y0 + 4, x1, y1 + 4, 9, fill="#07080a", outline="")
            rrect(c, x0, y0 + o, x1, y1 + o - 2, 9, fill="#4a4f5a" if dn else "#656b78", outline="#2a2e36", width=2)
            rrect(c, x0 + 4, y0 + o + 4, x1 - 4, y0 + o + 26, 6, fill="#7b8291" if not dn else "#5a606c", outline="")
            draw_icon(c, name, (x0 + x1) / 2, (y0 + y1) / 2 + o, 11, "#eef2fa" if not dn else AMBER)
            if lit.get(name):
                oval(c, x1 - 11, y0 + o + 10, 3.5, fill=RED if name == "play" else AMBER, outline="")

    def draw_status(self):
        c = self.sb
        c.delete("all")
        for txt, x0, x1 in (("БИБЛИОТЕКА  L", 20, 170), ("ПЛЕЙЛИСТ  T", 180, 330), ("МИКШЕР  M", 340, 490)):
            rrect(c, x0, 6, x1, 36, 8, fill=PANEL, outline=EDGE, width=2)
            c.create_text((x0 + x1) / 2, 21, text=txt, fill=INK, font=("Helvetica", 10, "bold"))
        rrect(c, 500, 6, 660, 36, 8, fill=mix(PANEL, AMBER, .25) if self.repeat else PANEL,
              outline=AMBER if self.repeat else EDGE, width=2)
        c.create_text(580, 21, text="ПОВТОР " + ("ВКЛ" if self.repeat else "ВЫКЛ"), fill=INK,
                      font=("Helvetica", 10, "bold"))


if __name__ == "__main__":
    Deck().mainloop()
