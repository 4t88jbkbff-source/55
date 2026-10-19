"""COMPASS HUNTER: мини-игра, где главный герой это компас.
Запуск: python compass_hunter.py   (только стандартный tkinter)

Сокровище скрыто в тумане. Единственная подсказка: золотой маркер на красном
ободке компаса показывает пеленг на клад, а число в центре его дистанцию.
Совмести стрелку (курс корабля) с маркером и плыви вперёд.

Управление:  A/D или стрелки  поворот   W/вверх  газ   S/вниз  тормоз
             клик/тяни по компасу  автоповорот на выбранный курс
             Space  сонар (на 2 с показывает клад на карте, перезарядка 7 с)
             R  заново
Правила:  60 с на старте, каждый клад +12 с. Столкновение со скалой -2 с.
"""
import math
import random
import time
import tkinter as tk

BG, CARD, LINE, MUTE, INK = "#07090d", "#0f131a", "#1b2230", "#6c778a", "#eaf0fa"
SEA, GRID, FOG = "#0b1c27", "#10283a", "#03070a"
W, VW = 1600, 620            # размер мира и окна карты
CC = 175                     # центр холста компаса (350x350)


# ---------- утилиты ----------
def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


def P(cx, cy, r, a):
    t = math.radians(a)
    return cx + r * math.sin(t), cy - r * math.cos(t)


def disc(c, cx, cy, r, fill="", outline="", w=1):
    c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=w)


def diff(a, b):
    """Кратчайшая разница углов a-b в диапазоне -180..180."""
    return (a - b + 540) % 360 - 180


# ---------- компас ----------
def compass(c, hdg, brg, dist, p, lock, t):
    c.delete("all")
    cx = cy = CC
    pulse = (math.sin(t * (2 + 7 * p)) + 1) / 2
    glow = mix("#3aa0ff", "#ff5a3a", p)                     # холодно -> горячо
    for r, a in ((173, .10), (171, .22), (169, .40)):
        disc(c, cx, cy, r, mix(CARD, glow, a * (.5 + .5 * pulse)))
    for i in range(10):                                      # красный ободок
        disc(c, cx, cy, 166 - i * 2.8, mix("#c84848", "#7a2323", i / 9))
    for i in range(16):                                      # тёмный циферблат
        disc(c, cx, cy, 139 - i * 8.6, mix("#2a2f3a", "#5a647c", i / 15))
    disc(c, cx, cy, 100, outline="#6a7691", w=9)
    disc(c, cx, cy, 94, outline="#394155", w=2)
    for d in range(0, 360, 10):                              # мелкие риски
        if d % 45:
            x1, y1 = P(cx, cy, 126, d)
            x2, y2 = P(cx, cy, 131, d)
            c.create_line(x1, y1, x2, y2, fill="#6d7890")
    for d in (45, 135, 225, 315):                            # белые диагонали
        x1, y1 = P(cx, cy, 106, d)
        x2, y2 = P(cx, cy, 124, d)
        c.create_line(x1, y1, x2, y2, fill="#fff", width=4, capstyle="round")
    for d, s in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
        x, y = P(cx, cy, 122, d)
        c.create_text(x, y, text=s, fill="#fff", font=("Helvetica", 17, "bold"))

    # золотой маркер пеленга на клад
    s = 1 + .25 * pulse
    col = "#5cff8a" if lock else "#ffd23f"
    tip = P(cx, cy, 140, brg)
    b1, b2 = P(cx, cy, 161, brg - 4.5 * s), P(cx, cy, 161, brg + 4.5 * s)
    c.create_polygon(*tip, *b1, *b2, fill=col, outline="#4a3500")

    # стрелка = курс корабля
    u = (math.sin(math.radians(hdg)), -math.cos(math.radians(hdg)))
    n = (math.cos(math.radians(hdg)), math.sin(math.radians(hdg)))
    tip, tail = (cx + u[0] * 94, cy + u[1] * 94), (cx - u[0] * 94, cy - u[1] * 94)
    L, Rr = (cx + n[0] * 9, cy + n[1] * 9), (cx - n[0] * 9, cy - n[1] * 9)
    for apex, side_l, side_r, cl, cr in (
            (tip, L, Rr, "#e86a66", "#b0403c"), (tail, L, Rr, "#7cb6f2", "#4a86c8")):
        c.create_polygon(*apex, *side_l, cx, cy, fill=cl, outline="")
        c.create_polygon(*apex, *side_r, cx, cy, fill=cr, outline="")
    disc(c, cx, cy, 20, "#c9cdd4")
    disc(c, cx, cy, 17, "#f2f4f7")
    disc(c, cx, cy, 11, "#dfe2e7")
    c.create_text(cx, cy, text=str(int(dist / 10)), fill="#333",
                  font=("Helvetica", 9, "bold"))


# ---------- игра ----------
class Game(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("COMPASS HUNTER")
        self.configure(bg=BG, padx=14, pady=14)
        self.keys = set()
        self.best = 0
        self.state = "ready"

        self.map = tk.Canvas(self, width=VW, height=VW, bg=SEA, highlightthickness=1,
                             highlightbackground=LINE)
        self.map.grid(row=0, column=0, rowspan=2, padx=(0, 14))
        side = tk.Frame(self, bg=BG)
        side.grid(row=0, column=1, sticky="n")
        tk.Label(side, text="COMPASS HUNTER", bg=BG, fg="#4aa3ff",
                 font=("Helvetica", 20, "bold")).pack(anchor="w")
        self.cv = tk.Canvas(side, width=350, height=350, bg=BG, highlightthickness=0)
        self.cv.pack(pady=8)
        self.hud = {}
        for k in ("score", "time", "status", "info", "ping"):
            self.hud[k] = tk.Label(side, bg=BG, fg=INK, anchor="w", justify="left",
                                   font=("Menlo", 12))
            self.hud[k].pack(fill="x")
        self.hud["score"].config(font=("Helvetica", 16, "bold"))
        self.hud["time"].config(font=("Helvetica", 28, "bold"))
        self.hud["status"].config(font=("Helvetica", 14, "bold"))
        tk.Label(side, bg=BG, fg=MUTE, justify="left", font=("Helvetica", 9), pady=8,
                 text="A/D ← →  поворот    W ↑  газ    S ↓  тормоз\n"
                      "клик по компасу: курс    Space: сонар    R: заново").pack(anchor="w")

        for ev in ("<Button-1>", "<B1-Motion>"):
            self.cv.bind(ev, self.compass_click)
        self.map.bind("<Button-1>", lambda e: self.start_or_restart())
        self.bind("<KeyPress>", self.key_down)
        self.bind("<KeyRelease>", lambda e: self.keys.discard(e.keysym.lower()))
        self.setup()
        self.last = time.time()
        self.loop()

    # ----- состояние -----
    def setup(self):
        self.x = self.y = W / 2
        self.h, self.speed, self.steer = 0.0, 0.0, None
        self.score, self.time = 0, 60.0
        self.trail, self.fx, self.pings = [], [], []
        self.hit_cd = self.ping_cd = self.ping_t = 0.0
        self.rocks = []
        while len(self.rocks) < 38:
            r = random.randint(18, 46)
            x, y = random.randint(60, W - 60), random.randint(60, W - 60)
            if math.hypot(x - W / 2, y - W / 2) > 170 + r:
                self.rocks.append((x, y, r))
        self.spawn_treasure()

    def spawn_treasure(self):
        for _ in range(300):
            x, y = random.randint(110, W - 110), random.randint(110, W - 110)
            d = math.hypot(x - self.x, y - self.y)
            if 400 < d < 1000 and all(math.hypot(x - a, y - b) > r + 40 for a, b, r in self.rocks):
                break
        self.tx, self.ty = x, y

    def start_or_restart(self):
        if self.state != "play":
            self.setup()
            self.state = "play"

    def key_down(self, e):
        k = e.keysym.lower()
        self.keys.add(k)
        if k == "r":
            self.setup()
            self.state = "play"
        elif k == "space":
            if self.state != "play":
                self.start_or_restart()
            elif self.ping_cd <= 0:
                self.ping_cd, self.ping_t = 7.0, 2.0
                self.pings.append(0.0)

    def compass_click(self, e):
        if self.state != "play":
            return self.start_or_restart()
        self.steer = math.degrees(math.atan2(e.x - CC, -(e.y - CC))) % 360

    # ----- физика -----
    def pressed(self, *names):
        return any(n in self.keys for n in names)

    def step(self, dt):
        if self.state != "play":
            return
        turn = self.pressed("d", "right") - self.pressed("a", "left")
        if turn:
            self.h += turn * 3.4
            self.steer = None
        elif self.steer is not None:
            d = diff(self.steer, self.h)
            self.h += max(-4.5, min(4.5, d))
            if abs(d) < 1:
                self.steer = None
        self.h %= 360
        if self.pressed("w", "up"):
            self.speed = min(5.2, self.speed + .18)
        elif self.pressed("s", "down"):
            self.speed = max(0, self.speed - .3)
        else:
            self.speed *= .985
        nx = self.x + math.sin(math.radians(self.h)) * self.speed
        ny = self.y - math.cos(math.radians(self.h)) * self.speed
        for rx, ry, rr in self.rocks:
            d = math.hypot(nx - rx, ny - ry)
            if d < rr + 11:
                nx, ny = rx + (nx - rx) / d * (rr + 11), ry + (ny - ry) / d * (rr + 11)
                self.speed *= .3
                if self.hit_cd <= 0:
                    self.time -= 2
                    self.hit_cd = .6
                    self.fx.append(dict(k="text", x=nx, y=ny, a=0, t="-2с", c="#ff6a5e"))
        self.x, self.y = max(12, min(W - 12, nx)), max(12, min(W - 12, ny))
        if self.speed > .3 and (not self.trail or math.hypot(self.x - self.trail[-1][0],
                                                              self.y - self.trail[-1][1]) > 14):
            self.trail = (self.trail + [(self.x, self.y)])[-80:]
        if math.hypot(self.x - self.tx, self.y - self.ty) < 28:
            self.score += 1
            self.time = min(99, self.time + 12)
            self.fx += [dict(k="ring", x=self.tx, y=self.ty, a=0, c="#ffd23f"),
                        dict(k="text", x=self.tx, y=self.ty - 20, a=0, t="+12с", c="#ffd23f")]
            self.spawn_treasure()
        self.time -= dt
        self.hit_cd -= dt
        self.ping_cd -= dt
        self.ping_t -= dt
        self.pings = [a + dt for a in self.pings if a < 1.4]
        for f in self.fx:
            f["a"] += dt
        self.fx = [f for f in self.fx if f["a"] < 1.2]
        if self.time <= 0:
            self.time, self.state = 0, "over"
            self.best = max(self.best, self.score)

    # ----- отрисовка карты -----
    def draw_map(self, t):
        c = self.map
        c.delete("all")
        ox, oy, m = self.x - VW / 2, self.y - VW / 2, VW / 2
        c.create_rectangle(0, 0, VW, VW, fill="#05090d", outline="")
        c.create_rectangle(-ox, -oy, W - ox, W - oy, fill=SEA, outline="#b84040", width=4)
        y0, y1 = max(0, -oy), min(VW, W - oy)
        x0, x1 = max(0, -ox), min(VW, W - ox)
        for k in range(8):
            X, Y = -(ox % 100) + k * 100, -(oy % 100) + k * 100
            if x0 < X < x1:
                c.create_line(X, y0, X, y1, fill=GRID)
            if y0 < Y < y1:
                c.create_line(x0, Y, x1, Y, fill=GRID)
        for rx, ry, rr in self.rocks:
            sx, sy = rx - ox, ry - oy
            if -rr < sx < VW + rr and -rr < sy < VW + rr:
                disc(c, sx, sy, rr, "#222b36", "#3d4a5a", 2)
                disc(c, sx - rr * .15, sy - rr * .15, rr * .62, "#2f3a48")
        if len(self.trail) > 1:
            c.create_line(*[v for px, py in self.trail for v in (px - ox, py - oy)],
                          fill="#2a7a9a", width=2, smooth=True)
        tsx, tsy = self.tx - ox, self.ty - oy
        d = math.hypot(self.x - self.tx, self.y - self.ty)
        if (d < 120 or self.ping_t > 0) and self.state == "play":
            for i in range(3):
                r = 10 + ((t * 30 + i * 12) % 36)
                disc(c, tsx, tsy, r, outline=mix("#ffd23f", SEA, r / 46), w=2)
            disc(c, tsx, tsy, 9, "#ffd23f", "#fff2a8", 2)
        for a in self.pings:
            disc(c, m, m, a * 460, outline=mix("#5ae0ff", SEA, a / 1.4), w=3)
        for f in self.fx:
            sx, sy = f["x"] - ox, f["y"] - oy
            if f["k"] == "ring":
                disc(c, sx, sy, 10 + f["a"] * 120, outline=mix(f["c"], SEA, f["a"] / 1.2), w=3)
            else:
                c.create_text(sx, sy - f["a"] * 40, text=f["t"], fill=mix(f["c"], SEA, f["a"] / 1.2),
                              font=("Helvetica", 16, "bold"))
        pts = [P(m, m, 16, self.h), P(m, m, 11, self.h + 150),
               P(m, m, 5, self.h + 180), P(m, m, 11, self.h - 150)]
        if self.speed > .6:
            c.create_line(*P(m, m, 8, self.h + 180), *P(m, m, 8 + self.speed * 4, self.h + 180),
                          fill="#ff9a3a", width=3)
        c.create_polygon(*[v for p in pts for v in p], fill="#e8eef8", outline="#6aa8e8", width=2)
        for i in range(12):                                   # туман по краям
            r = 240 + i * 20
            c.create_oval(m - r, m - r, m + r, m + r, outline=mix(SEA, FOG, i / 10), width=22)
        if self.state != "play":
            c.create_rectangle(110, 200, 510, 420, fill="#0a0f16", outline="#4aa3ff", width=2)
            title = "COMPASS HUNTER" if self.state == "ready" else "ВРЕМЯ ВЫШЛО"
            c.create_text(m, 245, text=title, fill="#4aa3ff", font=("Helvetica", 24, "bold"))
            if self.state == "ready":
                body = ("Клад спрятан в тумане.\nСтавь стрелку на золотой маркер\n"
                        "и плыви. Число в центре: дистанция.")
            else:
                body = f"Кладов найдено: {self.score}\nРекорд: {self.best}"
            c.create_text(m, 320, text=body, fill=INK, font=("Helvetica", 13), justify="center")
            c.create_text(m, 390, text="Space / клик: начать", fill="#ffd23f",
                          font=("Helvetica", 13, "bold"))

    # ----- цикл -----
    def loop(self):
        now = time.time()
        dt = min(.05, now - self.last)
        self.last = now
        self.step(dt)
        dist = math.hypot(self.tx - self.x, self.ty - self.y)
        brg = math.degrees(math.atan2(self.tx - self.x, -(self.ty - self.y))) % 360
        p = max(0.0, 1 - dist / 900)
        lock = abs(diff(brg, self.h)) < 6 and self.state == "play"
        compass(self.cv, self.h, brg, dist, p, lock, now)
        self.draw_map(now)
        word = "холодно" if p < .35 else "тепло" if p < .7 else "ГОРЯЧО"
        self.hud["score"].config(text=f"Кладов: {self.score}     Рекорд: {self.best}")
        self.hud["time"].config(text=f"{self.time:4.1f} c", fg="#ff6a5e" if self.time < 10 else INK)
        self.hud["status"].config(text="КУРС ВЕРНЫЙ ✓" if lock else word.upper(),
                                  fg="#5cff8a" if lock else mix("#3aa0ff", "#ff5a3a", p))
        self.hud["info"].config(text=f"Курс {self.h:05.1f}°   Пеленг {brg:05.1f}°\n"
                                     f"Скорость {self.speed * 6:4.1f} уз   Дистанция {dist / 10:4.0f} м")
        self.hud["ping"].config(text="Сонар: готов (Space)" if self.ping_cd <= 0
                                else f"Сонар: {self.ping_cd:3.1f} с")
        self.after(16, self.loop)


if __name__ == "__main__":
    Game().mainloop()

