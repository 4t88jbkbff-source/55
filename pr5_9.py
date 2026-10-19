"""Индикаторы направления: спидометр + 4 стиля D-pad на чистом tkinter.
Запуск: python direction_pads.py
Управление: мышь (зажать стрелку), стрелки или WASD, пробел или центр = сброс.
Вверх/вниз меняют скорость, влево/вправо меняют курс.
"""
import math
import tkinter as tk

BG, CARD, LINE, MUTE, INK = "#07090d", "#0f131a", "#1b2230", "#6c778a", "#eaf0fa"
CYAN, GREEN, LIME, RED = "#2fd0f0", "#3ed598", "#c4e84a", "#ff5a4f"
SIZE, C = 250, 125
A0, A1 = -135, 135

VEC = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]
NAMES = ["ВВЕРХ", "ВВЕРХ-ВПРАВО", "ВПРАВО", "ВНИЗ-ВПРАВО",
         "ВНИЗ", "ВНИЗ-ВЛЕВО", "ВЛЕВО", "ВВЕРХ-ВЛЕВО"]


# ---------- утилиты ----------
def rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def mix(a, b, t):
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(rgb(a), rgb(b)))


def grad(stops, t):
    n = len(stops) - 1
    t = max(0.0, min(1.0, t)) * n
    i = min(int(t), n - 1)
    return mix(stops[i], stops[i + 1], t - i)


def P(r, a):
    t = math.radians(a)
    return C + r * math.sin(t), C - r * math.cos(t)


def circle(c, r, fill="", outline="", w=1):
    c.create_oval(C - r, C - r, C + r, C + r, fill=fill, outline=outline, width=w)


def arc(c, r, a, b, col, w):
    c.create_arc(C - r, C - r, C + r, C + r, start=90 - b, extent=b - a,
                 style="arc", outline=col, width=w)


def ang(v):
    return A0 + (A1 - A0) * v / 100


def text(c, x, y, s, size, col, bold=False):
    c.create_text(x, y, text=s, fill=col,
                  font=("Helvetica", size, "bold" if bold else "normal"))


def triangle(c, cx, cy, a, s, col):
    """Треугольник, смотрящий наружу под компасным углом a."""
    t = math.radians(a)
    ux, uy = math.sin(t), -math.cos(t)
    px, py = math.cos(t), math.sin(t)
    pts = [cx + ux * s, cy + uy * s,
           cx - ux * s * .6 + px * s * .9, cy - uy * s * .6 + py * s * .9,
           cx - ux * s * .6 - px * s * .9, cy - uy * s * .6 - py * s * .9]
    c.create_polygon(*pts, fill=col, outline="")


def sync_icon(c, col, r=11):
    for start in (20, 200):
        c.create_arc(C - r, C - r, C + r, C + r, start=start, extent=140,
                     style="arc", outline=col, width=3)
        th = math.radians(start + 140)
        px, py = C + r * math.cos(th), C - r * math.sin(th)
        dx, dy = -math.sin(th), -math.cos(th)
        rx, ry = math.cos(th), -math.sin(th)
        c.create_polygon(px + dx * 6, py + dy * 6, px + rx * 5, py + ry * 5,
                         px - rx * 5, py - ry * 5, fill=col, outline="")


# ---------- спидометр ----------
def speedo(c, v):
    c.delete("all")
    circle(c, 113, fill="#5c5c5c")
    circle(c, 109, fill="#101010")
    for i in range(14):
        circle(c, 101 - i * 7, fill=mix("#1b1b1b", "#404040", i / 13))
    for j in range(28):
        arc(c, 96, ang(j * 2.5), ang((j + 1) * 2.5) + .6,
            grad([CYAN, GREEN, LIME], j * 2.5 / 70), 4)
    for i in range(51):
        val, big = i * 2, i % 5 == 0
        col = grad([CYAN, GREEN, LIME], val / 70) if val <= 70 else "#d6d6d6"
        a = ang(val)
        x1, y1 = P(80 if big else 85, a)
        x2, y2 = P(92, a)
        c.create_line(x1, y1, x2, y2, fill=col, width=2 if big else 1)
    for i in range(11):
        x, y = P(64, ang(i * 10))
        text(c, x, y, str(i * 10), 8, "#cfcfcf")
    x1, y1 = P(-14, ang(v))
    x2, y2 = P(76, ang(v))
    c.create_line(x1, y1, x2, y2, fill=RED, width=3, capstyle="round")
    circle(c, 11, fill=RED)
    circle(c, 5, fill="#ff9a92")
    text(c, C, 188, f"{round(v)}", 22, "#ffffff", True)
    text(c, C, 208, "км/ч", 8, "#9a9a9a")


# ---------- D-pad ----------
THEMES = {
    "dark":   dict(rim="#1c1f2b", stops=None, face="#3b3e4b", arrow="#cfd3dc",
                   accent="#35c4b8", cfill="#3b3e4b", cring="#35c4b8", icon="#e2e6ee"),
    "light":  dict(rim=None, stops=["#3fb8ab", "#e0c070", "#e07a3f"], face="#f5f6f8",
                   arrow="#9ea4ad", accent="#e07a3f", cfill="#f1f2f4", cring="#dfe2e6", icon="#a7adb6"),
    "blue":   dict(rim=None, stops=["#78c0f5", "#7f9aa8", "#e8b84a"], face="#1f3f66",
                   arrow="#4aa3ff", accent="#9fdcff", cfill="#17314f", cring="#2a5b94", icon="#4aa3ff"),
    "purple": dict(rim=None, stops=["#4a6fd0", "#7a58b0", "#a66bb5"], face="#38355e",
                   arrow="#a59ae0", accent="#d2c4ff", cfill="#322f55", cring="#4a4678", icon="#8f86cc"),
}


class Pad:
    def __init__(self, parent, app, theme):
        self.app, self.t = app, THEMES[theme]
        self.cv = tk.Canvas(parent, width=SIZE, height=SIZE, bg=CARD, highlightthickness=0)
        self.hover = self.pressed = None
        self.last = "x"
        self.cv.bind("<Motion>", lambda e: self.set_hover(self.hit(e)))
        self.cv.bind("<Leave>", lambda e: self.set_hover(None))
        self.cv.bind("<ButtonPress-1>", self.press)
        self.cv.bind("<B1-Motion>", lambda e: self.press(e, move=True))
        self.cv.bind("<ButtonRelease-1>", self.release)
        self.draw()

    @staticmethod
    def hit(e):
        dx, dy = e.x - C, e.y - C
        d = math.hypot(dx, dy)
        if d <= 32:
            return "c"
        if d <= 108:
            return round((math.degrees(math.atan2(dx, -dy)) % 360) / 45) % 8
        return None

    def set_hover(self, s):
        self.hover = s

    def press(self, e, move=False):
        s = self.hit(e)
        self.hover = s
        self.pressed = s if s != "c" else None
        if s == "c" and not move:
            self.app.reset()

    def release(self, _):
        self.pressed = None

    def state(self):
        sel = self.pressed if self.pressed is not None else self.hover
        return sel if sel is not None else self.app.key_sel

    def draw(self):
        t, c, sel = self.t, self.cv, self.state()
        self.last = sel
        c.delete("all")
        if t["stops"]:
            circle(c, 113, fill=t["face"])
            for i in range(90):
                a = i * 4
                w = ((a - 315) % 360) / 360
                arc(c, 107, a, a + 5.5, grad(t["stops"], 1 - abs(2 * w - 1)), 12)
        else:
            circle(c, 113, fill=t["rim"])
            circle(c, 101, fill=t["face"])
        if isinstance(sel, int):
            a = sel * 45
            c.create_arc(C - 99, C - 99, C + 99, C + 99, start=90 - (a + 22.5), extent=45,
                         style="pieslice", fill=mix(t["face"], t["accent"], .18), outline="")
        for k in range(8):
            x, y = P(72 if k % 2 == 0 else 70, k * 45)
            triangle(c, x, y, k * 45, 11 if k % 2 == 0 else 8,
                     t["accent"] if k == sel else t["arrow"])
        circle(c, 31, fill=t["cfill"], outline=t["accent"] if sel == "c" else t["cring"], w=4)
        sync_icon(c, t["accent"] if sel == "c" else t["icon"])


# ---------- приложение ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Индикаторы направления")
        self.configure(bg=BG, padx=16, pady=16)
        self.speed, self.heading = 65.0, 0.0
        self.keys, self.key_sel, self.drawn = set(), None, None

        tk.Label(self, text="ИНДИКАТОРЫ НАПРАВЛЕНИЯ", bg=BG, fg="#4aa3ff",
                 font=("Helvetica", 22, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        self.status = tk.Label(self, bg=BG, fg=INK, font=("Menlo", 12), anchor="w")
        self.status.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 10))

        self.cards = []
        self.speedo_cv = None
        for i in range(5):
            f = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)
            f.grid(row=2 + i // 3, column=i % 3, padx=6, pady=6)
            if i == 0:
                self.speedo_cv = tk.Canvas(f, width=SIZE, height=SIZE, bg=CARD, highlightthickness=0)
                self.speedo_cv.pack()
                name = "SPEEDOMETER"
            else:
                theme = list(THEMES)[i - 1]
                pad = Pad(f, self, theme)
                pad.cv.pack()
                self.cards.append(pad)
                name = theme.upper()
            tk.Label(f, text=name, bg=CARD, fg=MUTE, font=("Helvetica", 9, "bold")).pack(pady=(0, 8))

        self.bind("<KeyPress>", self.key_down)
        self.bind("<KeyRelease>", self.key_up)
        self.focus_set()
        self.loop()

    def reset(self):
        self.speed, self.heading = 0.0, 0.0

    def key_down(self, e):
        k = e.keysym.lower()
        if k == "space":
            return self.reset()
        self.keys.add(k)

    def key_up(self, e):
        self.keys.discard(e.keysym.lower())

    def vector(self):
        k = self.keys
        dx = (("right" in k or "d" in k) - ("left" in k or "a" in k))
        dy = (("up" in k or "w" in k) - ("down" in k or "s" in k))
        for p in self.cards:
            if isinstance(p.pressed, int):
                mx, my = VEC[p.pressed]
                dx, dy = dx + mx, dy + my
        return max(-1, min(1, dx)), max(-1, min(1, dy))

    def loop(self):
        k = self.keys
        kx = (("right" in k or "d" in k) - ("left" in k or "a" in k))
        ky = (("up" in k or "w" in k) - ("down" in k or "s" in k))
        self.key_sel = VEC.index((kx, ky)) if (kx, ky) in VEC else None

        dx, dy = self.vector()
        self.speed = max(0.0, min(100.0, self.speed + (dy * 0.9 if dy else -0.12)))
        self.heading = (self.heading + dx * 2.2) % 360

        key = round(self.speed, 1)
        if key != self.drawn:
            speedo(self.speedo_cv, self.speed)
            self.drawn = key
        for p in self.cards:
            if p.state() != p.last:
                p.draw()
        d = NAMES[VEC.index((dx, dy))] if (dx, dy) in VEC else "—"
        self.status.config(text=f"Скорость {self.speed:5.1f} км/ч   Курс {self.heading:05.1f}°   Направление: {d}")
        self.after(33, self.loop)


if __name__ == "__main__":
    App().mainloop()

