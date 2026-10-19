"""Gauge Lab: 5 стилей индикаторов на чистом tkinter (без зависимостей).
Запуск: python gauges.py
"""
import math
import time
import tkinter as tk

BG, CARD, LINE = "#07090d", "#0f131a", "#1b2230"
INK, MUTE, TRACK = "#eaf0fa", "#6c778a", "#252c3a"
BLUE, GREEN, PINK = "#4aa3ff", "#3ed598", "#ff4d8d"
RED, TEAL = "#ff5a4f", "#5fd4b8"

SIZE, C, S = 230, 115, 1.15      # размер холста, центр, масштаб
A0, A1 = -135, 135               # дуга шкалы (0 градусов = вверх)


def ang(v):
    return A0 + (A1 - A0) * v / 100


def P(r, a):
    t = math.radians(a)
    return C + r * S * math.sin(t), C - r * S * math.cos(t)


def arc(c, r, a, b, col, w):
    R = r * S
    c.create_arc(C - R, C - R, C + R, C + R, start=90 - b, extent=b - a,
                 style="arc", outline=col, width=w)


def tick(c, r1, r2, a, col, w=2):
    x1, y1 = P(r1, a)
    x2, y2 = P(r2, a)
    c.create_line(x1, y1, x2, y2, fill=col, width=w)


def disc(c, r, fill, outline=""):
    R = r * S
    c.create_oval(C - R, C - R, C + R, C + R, fill=fill, outline=outline)


def txt(c, x, y, s, size, col=MUTE, bold=False):
    c.create_text(x, y, text=s, fill=col,
                  font=("Helvetica", size, "bold" if bold else "normal"))


# ---------- 5 стилей ----------
def knob(c, v):
    arc(c, 90, A0, A1, TRACK, 7)
    if v > 0:
        arc(c, 90, A0, ang(v), BLUE, 7)
    disc(c, 78, "#2a2f38", "#000")
    disc(c, 60, "#1d2128")
    x, y = P(62, ang(v))
    c.create_oval(x - 10, y - 10, x + 10, y + 10, fill=BLUE, outline="")


def ring(c, v, n=60):
    for i in range(n + 1):
        p = i / n * 100
        tick(c, 80, 95, ang(p), BLUE if p <= v else TRACK)
    disc(c, 56, "#f2f4f8")
    disc(c, 42, GREEN)
    disc(c, 26, "#ffffff")
    txt(c, C, C, f"{round(v)}", 18, "#3a8ee6", True)
    txt(c, 45, 195, "0", 9)
    txt(c, 185, 195, "100", 9)


def minimal(c, v, n=70):
    for i in range(n + 1):
        p = i / n * 100
        tick(c, 80, 94, ang(p), TEAL if p <= v else TRACK, 2 if p <= v else 1)
    txt(c, C, C + 5, f"{round(v)}", 52, INK)
    txt(c, 62, 58, "40", 10)
    txt(c, 168, 58, "80", 10)


def speedo(c, v):
    arc(c, 90, A0, ang(70), BLUE, 7)
    arc(c, 90, ang(70), A1, TRACK, 7)
    for i in range(51):
        big = i % 5 == 0
        tick(c, 66 if big else 70, 77, ang(i * 2), MUTE, 2 if big else 1)
    for i in range(11):
        x, y = P(54, ang(i * 10))
        txt(c, x, y, str(i * 10), 8)
    x, y = P(62, ang(v))
    c.create_line(C, C, x, y, fill=RED, width=3, capstyle="round")
    disc(c, 17, RED)
    txt(c, C, C, f"{round(v)}", 11, "#fff", True)


def mbps(c, v):
    arc(c, 90, A0, ang(33), GREEN, 8)
    arc(c, 90, ang(33), ang(75), BLUE, 8)
    arc(c, 90, ang(75), A1, PINK, 8)
    for p in (0, 25, 50, 75, 100):
        x, y = P(70, ang(p))
        txt(c, x, y, f"{p}M", 8)
    a = ang(v)
    tip, l, r = P(58, a), P(6, a + 90), P(6, a - 90)
    c.create_polygon(*tip, *l, *r, fill="#9fd3ff", outline="")
    disc(c, 6, "#9fd3ff")
    c.create_rectangle(C - 38, 148, C + 38, 176, outline=LINE)
    txt(c, C, 162, f"{v:6.2f}", 14, INK, True)
    txt(c, C, 140, "Mbps", 8)


GAUGES = [("KNOB", knob), ("RING", ring), ("MINIMAL", minimal),
          ("SPEEDOMETER", speedo), ("MBPS", mbps)]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gauge Lab")
        self.configure(bg=BG, padx=16, pady=16)
        self.auto = False
        self.t0 = 0.0

        tk.Label(self, text="GAUGE LAB", bg=BG, fg=BLUE,
                 font=("Helvetica", 26, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")

        # панель управления
        bar = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=12, ipady=8)
        self.big = tk.Label(bar, text="65", bg=CARD, fg=INK, width=4,
                            font=("Helvetica", 34, "bold"))
        self.big.pack(side="left", padx=10)
        self.scale = tk.Scale(bar, from_=0, to=100, resolution=0.1, orient="horizontal",
                              length=380, showvalue=False, bg=CARD, fg=INK,
                              troughcolor=TRACK, highlightthickness=0,
                              activebackground=BLUE, command=self.on_scale)
        self.scale.pack(side="left", padx=6)
        self.btn_auto = self.button(bar, "▶ Авто", self.toggle_auto)
        for p in (0, 25, 50, 75, 100):
            self.button(bar, str(p), lambda p=p: self.manual(p))

        # холсты
        self.canvases = []
        for i, (name, _) in enumerate(GAUGES):
            f = tk.Frame(self, bg=CARD, highlightbackground=LINE, highlightthickness=1)
            f.grid(row=2 + i // 3, column=i % 3, padx=6, pady=6)
            cv = tk.Canvas(f, width=SIZE, height=SIZE, bg=CARD, highlightthickness=0)
            cv.pack()
            tk.Label(f, text=name, bg=CARD, fg=MUTE,
                     font=("Helvetica", 9, "bold")).pack(pady=(0, 8))
            self.canvases.append(cv)
        k = self.canvases[0]                       # ручка крутится мышью
        k.configure(cursor="hand2")
        k.bind("<Button-1>", self.knob_drag)
        k.bind("<B1-Motion>", self.knob_drag)

        self.scale.set(65)

    def button(self, parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd, bg=CARD, fg=INK,
                      activebackground=BLUE, activeforeground="#fff",
                      relief="flat", highlightbackground=LINE, padx=10)
        b.pack(side="left", padx=4)
        return b

    # ----- логика -----
    def value(self):
        return float(self.scale.get())

    def on_scale(self, _=None):
        v = self.value()
        self.big.config(text=str(round(v)))
        for cv, (_, fn) in zip(self.canvases, GAUGES):
            cv.delete("all")
            fn(cv, v)

    def manual(self, v):
        self.stop_auto()
        self.scale.set(v)

    def knob_drag(self, e):
        self.stop_auto()
        a = math.degrees(math.atan2(e.x - C, -(e.y - C)))
        a = max(A0, min(A1, a))
        self.scale.set((a - A0) / (A1 - A0) * 100)

    def toggle_auto(self):
        if self.auto:
            return self.stop_auto()
        self.auto = True
        self.t0 = time.time()
        self.btn_auto.config(text="❚❚ Стоп", bg=BLUE)
        self.tick_auto()

    def stop_auto(self):
        self.auto = False
        self.btn_auto.config(text="▶ Авто", bg=CARD)

    def tick_auto(self):
        if not self.auto:
            return
        s = time.time() - self.t0
        self.scale.set(50 + 50 * math.sin(s * 1.1) * math.cos(s * 0.37))
        self.after(16, self.tick_auto)


if __name__ == "__main__":
    App().mainloop()

