"""COCKPIT RESCUE: мини-игра «Посади самолёт» на приборах с твоей картинки.
Запуск: python cockpit_rescue.py   (только стандартный tkinter)

Приборы:  бирюзовая дуга = ТОПЛИВО, тёмный спидометр = СКОРОСТЬ,
          ручка с синими рисками = ТЯГА, авиагоризонт = КРЕН/ТАНГАЖ (+ лента высоты).
Цель:     долететь до 100% дистанции сквозь турбулентность и посадить самолёт:
          скорость 14-50, крен и тангаж не больше 8 градусов, высота не больше 30.
Управление:  стрелки: тангаж (вверх/вниз) и крен (влево/вправо)
             W/S: тяга     мышь: тяни по авиагоризонту (штурвал) или крути ручку тяги
             Space / клик: старт и рестарт
Очки:     пока скорость, крен и тангаж в норме, растёт комбо (x1..x8) и очки.
"""
import math
import random
import time
import tkinter as tk

BG, CARD, EDGE, INK, MUTE = "#0a0d12", "#10151c", "#1f2733", "#e8ecf4", "#7d8799"
TEAL, BLUE, GREEN, AMBER, RED = "#4fb5bf", "#6fb1ff", "#5cc9b0", "#ffb84a", "#ff5a4f"
W, H = 700, 780
CELLS = dict(fuel=(175, 208), speed=(525, 208), knob=(175, 516), att=(505, 516))


# ---------- утилиты ----------
def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(pa, pb))


def P(cx, cy, r, a):
    t = math.radians(a)
    return cx + r * math.sin(t), cy - r * math.cos(t)


def oval(c, cx, cy, r, **kw):
    c.create_oval(cx - r, cy - r, cx + r, cy + r, **kw)


def arc(c, cx, cy, r, a, b, col, w):
    if b - a > .05:
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90 - b, extent=b - a, style="arc",
                     outline=col, width=w)


def txt(c, x, y, s, size, col=INK, bold=True, anchor="center"):
    c.create_text(x, y, text=s, fill=col, anchor=anchor,
                  font=("Helvetica", size, "bold" if bold else "normal"))


def clamp(v, a, b):
    return max(a, min(b, v))


# ---------- приборы ----------
def draw_fuel(c, cx, cy, v, frame):
    R = 125
    col = TEAL if v > 25 else (AMBER if v > 10 else RED)
    if v <= 10 and frame // 8 % 2:
        col = mix(CARD, RED, .5)
    a = lambda x: -125 + 250 * x / 100
    arc(c, cx, cy, R, -125, 125, mix(CARD, TEAL, .30), 7)
    for i in range(0, 101, 2):
        r1 = R - (17 if i % 10 == 0 else 9)
        x1, y1 = P(cx, cy, R - 4, a(i))
        x2, y2 = P(cx, cy, r1, a(i))
        c.create_line(x1, y1, x2, y2, fill=mix(CARD, TEAL, .55 if i % 10 == 0 else .32))
    for i in range(0, 101, 10):
        x, y = P(cx, cy, R - 34, a(i))
        txt(c, x, y, str(i), 10, mix(CARD, TEAL, .8), False)
    arc(c, cx, cy, R, -125, a(v), col, 7)
    x, y = P(cx, cy, R, a(v))
    oval(c, x, y, 8, fill=col, outline="")
    txt(c, cx, cy + 14, f"{v:.0f}%", 38, col, False)
    txt(c, cx, cy + 58, "ТОПЛИВО", 13, mix(CARD, TEAL, .85), False)


SPEED_ZONES = [(0, 14, "#ef6b6b"), (14, 60, "#5cc9b0"), (60, 78, "#e0d030"), (78, 100, "#ef6b6b")]


def draw_speed(c, cx, cy, v, frame):
    a = lambda x: -135 + 270 * x / 100
    oval(c, cx, cy, 142, fill="#4d4d4d", outline="")
    oval(c, cx, cy, 138, fill="#5e5e5e", outline="")
    for i in range(10):
        oval(c, cx, cy, 133 - i * 2, fill=mix("#2e2e2e", "#454545", i / 9), outline="")
    c.create_arc(cx - 128, cy - 128, cx + 128, cy + 128, start=105, extent=62, style="pieslice",
                 fill="#4b4b4b", outline="")
    oval(c, cx, cy, 70, fill="#575757", outline="")
    for i in range(101):
        big, mid = i % 10 == 0, i % 5 == 0
        x1, y1 = P(cx, cy, 133, a(i))
        x2, y2 = P(cx, cy, 121 if big else 125 if mid else 128, a(i))
        c.create_line(x1, y1, x2, y2, fill="#ffffff" if big else "#a9a9a9", width=2 if big else 1)
    for i in range(0, 101, 10):
        x, y = P(cx, cy, 108, a(i))
        txt(c, x, y, str(i), 9, "#ffffff")
    for lo, hi, col in SPEED_ZONES:
        arc(c, cx, cy, 82, a(lo), a(hi), col, 20)
    ang = a(clamp(v, 0, 100))
    tip, l, r = P(cx, cy, 96, ang), P(cx, cy, 8, ang - 90), P(cx, cy, 8, ang + 90)
    c.create_polygon(*tip, *l, *r, fill="#e8645f", outline="")
    oval(c, cx, cy, 25, fill="#ffffff", outline="#e05a55", width=5)
    txt(c, cx, cy, f"{v:.0f}", 17, "#111111")
    if (v < 14 or v > 85) and frame // 6 % 2:
        txt(c, cx, cy + 112, "STALL" if v < 14 else "OVERSPEED", 12, RED)


def draw_knob(c, cx, cy, thr):
    a = lambda i: -135 + 270 * i / 20
    for i in range(21):
        lit = i / 20 <= thr + 1e-6
        x1, y1 = P(cx, cy, 102, a(i))
        x2, y2 = P(cx, cy, 120, a(i))
        c.create_line(x1, y1, x2, y2, fill=BLUE if lit else "#3a424e", width=6, capstyle="round")
    oval(c, cx, cy, 96, fill="#0b0b0b", outline="")
    oval(c, cx, cy, 90, fill="#2e2e2e", outline="")
    oval(c, cx, cy, 78, outline="#383838", width=2)
    ang = -135 + 270 * thr
    x, y = P(cx, cy, 78, ang)
    c.create_line(cx, cy, x, y, fill=BLUE, width=14, capstyle="round")
    oval(c, cx, cy, 22, fill=BLUE, outline="")
    txt(c, cx, cy + 142, f"ТЯГА  {thr * 100:.0f}%", 13, mix(CARD, BLUE, .9), False)


def draw_att(c, cx, cy, pitch, roll, alt, show_land):
    R, k = 122, 3.0
    oval(c, cx, cy, R + 14, fill="#8a8d92", outline="")
    oval(c, cx, cy, R + 6, fill="#4c4f55", outline="")
    oval(c, cx, cy, R, fill="#4f86b8", outline="")
    hr = math.radians(-roll)
    ux, uy, nx, ny = math.cos(hr), math.sin(hr), -math.sin(hr), math.cos(hr)
    s = pitch * k
    if s <= -R:
        oval(c, cx, cy, R, fill="#8b6a40", outline="")
    elif s < R:
        th, phi = math.atan2(ny, nx), math.acos(s / R)
        pts = []
        for j in range(61):
            t = th - phi + 2 * phi * j / 60
            pts += [cx + R * math.cos(t), cy + R * math.sin(t)]
        c.create_polygon(*pts, fill="#8b6a40", outline="")
        for off, col, w in ((-9, "#8fb3d1", 14), (9, "#b89c7c", 14)):
            so = clamp(s + off, -R + 2, R - 2)
            h = math.sqrt(R * R - so * so)
            fx, fy = cx + nx * so, cy + ny * so
            c.create_line(fx - ux * h, fy - uy * h, fx + ux * h, fy + uy * h, fill=col, width=w)
        h = math.sqrt(R * R - s * s)
        fx, fy = cx + nx * s, cy + ny * s
        c.create_line(fx - ux * h, fy - uy * h, fx + ux * h, fy + uy * h, fill="#ffffff", width=3)
    for m, ln in ((-30, 52), (-20, 36), (-10, 22), (10, 22), (20, 36), (30, 52)):
        sm = (pitch - m) * k
        mx, my = cx + nx * sm, cy + ny * sm
        e1, e2 = (mx - ux * ln, my - uy * ln), (mx + ux * ln, my + uy * ln)
        if math.hypot(mx - cx, my - cy) < R - 30 and max(math.hypot(e1[0] - cx, e1[1] - cy),
                                                          math.hypot(e2[0] - cx, e2[1] - cy)) < R - 26:
            c.create_line(*e1, *e2, fill="#ffffff", width=2)
            for sg, e in ((-1, e1), (1, e2)):
                txt(c, e[0] + sg * ux * 12, e[1] + sg * uy * 12, str(abs(m)), 8, "#ffffff")
    oval(c, cx, cy, R + 7, outline="#8a8d92", width=14)                      # маска по кругу
    for t, big in ((-60, 1), (-45, 0), (-30, 1), (-20, 0), (-10, 0), (0, 1), (10, 0), (20, 0),
                   (30, 1), (45, 0), (60, 1)):
        x1, y1 = P(cx, cy, R - 1, t)
        x2, y2 = P(cx, cy, R - (17 if big else 10), t)
        c.create_line(x1, y1, x2, y2, fill="#ffffff", width=3 if big else 2)
    tip, b1, b2 = P(cx, cy, R - 14, -roll), P(cx, cy, R - 30, -roll - 4), P(cx, cy, R - 30, -roll + 4)
    c.create_polygon(*tip, *b1, *b2, fill="#e8645f", outline="")
    y = "#f7d23a"                                                            # силуэт самолёта
    c.create_line(cx - 92, cy + 8, cx - 38, cy + 8, cx - 28, cy + 20, fill=y, width=5, joinstyle="round")
    c.create_line(cx + 92, cy + 8, cx + 38, cy + 8, cx + 28, cy + 20, fill=y, width=5, joinstyle="round")
    c.create_line(cx, cy + 4, cx, cy + 82, fill=y, width=5)
    c.create_polygon(cx - 34, cy + 116, cx - 22, cy + 84, cx + 22, cy + 84, cx + 34, cy + 116, fill=y,
                     outline="")
    oval(c, cx, cy, 5, fill=y, outline="")
    # лента высоты
    tx, y0, y1 = cx + R + 28, cy - R, cy + R
    c.create_rectangle(tx - 8, y0, tx + 8, y1, fill="#171c25", outline=EDGE)
    c.create_rectangle(tx - 8, y1 - (y1 - y0) * .12, tx + 8, y1, fill=mix(CARD, RED, .55), outline="")
    if show_land:
        c.create_rectangle(tx - 8, y1 - (y1 - y0) * .30, tx + 8, y1 - (y1 - y0) * .12,
                           fill=mix(CARD, GREEN, .55), outline="")
        txt(c, tx - 22, y1 - (y1 - y0) * .21, "LAND", 7, GREEN)
    ym = y1 - (y1 - y0) * clamp(alt, 0, 100) / 100
    c.create_rectangle(tx - 8, ym, tx + 8, y1, fill=mix(CARD, BLUE, .65), outline="")
    c.create_polygon(tx - 8, ym, tx - 20, ym - 7, tx - 20, ym + 7, fill=AMBER, outline="")
    txt(c, tx, y0 - 12, "ALT", 8, MUTE)
    txt(c, tx, y1 + 12, f"{alt:.0f}", 9, INK)


# ---------- игра ----------
class Game(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("COCKPIT RESCUE")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.cv = tk.Canvas(self, width=W, height=H, bg=BG, highlightthickness=0)
        self.cv.pack()
        self.keys, self.rel = set(), {}
        self.drag, self.stick = None, (0.0, 0.0)
        self.best, self.state, self.frame, self.last = 0, "ready", 0, time.time()
        self.reset()
        self.cv.bind("<ButtonPress-1>", self.mouse_down)
        self.cv.bind("<B1-Motion>", self.mouse_move)
        self.cv.bind("<ButtonRelease-1>", self.mouse_up)
        self.bind("<KeyPress>", self.key_down)
        self.bind("<KeyRelease>", self.key_up)
        self.loop()

    def reset(self):
        self.pitch = self.roll = self.pitch_v = self.roll_v = 0.0
        self.speed, self.thr, self.fuel, self.alt, self.prog = 45.0, .5, 100.0, 50.0, 0.0
        self.score, self.combo, self.stab_t, self.t = 0.0, 1, 0.0, 0.0
        self.ph = [random.uniform(0, 6.28) for _ in range(6)]
        self.gust_t = random.uniform(6, 10)
        self.event, self.event_t = "", 0.0
        self.result = ("", "", INK)

    # ----- ввод -----
    def key_down(self, e):
        k = e.keysym.lower()
        self.rel.pop(k, None)
        self.keys.add(k)
        if k in ("space", "r", "return"):
            self.start()

    def key_up(self, e):
        self.rel[e.keysym.lower()] = time.time()

    def held(self, *names):
        return any(n in self.keys for n in names)

    def start(self):
        if self.state != "play":
            self.reset()
            self.state = "play"

    def mouse_down(self, e):
        if self.state != "play":
            return self.start()
        kx, ky = CELLS["knob"]
        ax, ay = CELLS["att"]
        if math.hypot(e.x - kx, e.y - ky) < 130:
            self.drag = "knob"
        elif math.hypot(e.x - ax, e.y - ay) < 140:
            self.drag = "stick"
        self.mouse_move(e)

    def mouse_move(self, e):
        if self.drag == "knob":
            kx, ky = CELLS["knob"]
            a = math.degrees(math.atan2(e.x - kx, -(e.y - ky)))
            a = clamp(a, -135, 135) if abs(a) < 170 else (-135 if a < 0 else 135)
            self.thr = (a + 135) / 270
        elif self.drag == "stick":
            ax, ay = CELLS["att"]
            self.stick = (clamp((e.x - ax) / 70, -1, 1), clamp(-(e.y - ay) / 70, -1, 1))

    def mouse_up(self, e):
        self.drag, self.stick = None, (0.0, 0.0)

    # ----- физика -----
    def update(self, dt):
        now = time.time()
        for k in [k for k, t in self.rel.items() if now - t > .07]:
            self.keys.discard(k)
            del self.rel[k]
        if self.state != "play":
            return
        self.t += dt
        pf = self.prog / 100
        ix = clamp(self.held("right", "d") - self.held("left", "a") + self.stick[0], -1, 1)
        iy = clamp(self.held("up") - self.held("down") + self.stick[1], -1, 1)
        if self.drag != "knob":
            self.thr = clamp(self.thr + (self.held("w") - self.held("s")) * .5 * dt, 0, 1)
        A = 9 + 14 * pf
        t = self.t
        tr = A * (math.sin(t * 1.3 + self.ph[0]) + .7 * math.sin(t * 2.9 + self.ph[1]) + .5 * math.sin(t * .7 + self.ph[2]))
        tp = A * .6 * (math.sin(t * 1.1 + self.ph[3]) + .6 * math.sin(t * 2.3 + self.ph[4]))
        if t >= self.gust_t:
            self.roll_v += random.choice((-1, 1)) * 45
            self.alt -= 6
            self.event, self.event_t = "ПОРЫВ ВЕТРА!", 1.6
            self.gust_t = t + random.uniform(7, 13)
        self.roll_v += (95 * ix + tr - 1.8 * self.roll_v - .6 * self.roll) * dt
        self.roll += self.roll_v * dt
        self.pitch_v += (70 * iy + tp - 1.8 * self.pitch_v - .4 * self.pitch) * dt
        if self.speed < 14:
            self.pitch_v -= (14 - self.speed) * 6 * dt
        self.pitch = clamp(self.pitch + self.pitch_v * dt, -45, 45)
        eff = self.thr if self.fuel > 0 else 0.0
        self.speed = clamp(self.speed + ((eff * 90 - self.speed) * .30 - self.pitch * .35) * dt, 0, 100)
        climb = (self.speed - 40) * .12 + self.pitch * .55
        if abs(self.roll) > 30:
            climb -= (abs(self.roll) - 30) * .08
        if self.speed < 15:
            climb -= (15 - self.speed) * .8
        self.alt = min(100.0, self.alt + climb * dt)
        self.prog += self.speed * .03 * dt
        self.fuel = max(0.0, self.fuel - (.25 + eff * .9) * dt)
        self.event_t -= dt
        stable = 15 <= self.speed <= 62 and abs(self.roll) < 14 and abs(self.pitch) < 9 and 8 < self.alt < 95
        if stable:
            self.stab_t += dt
            self.combo = min(8, 1 + int(self.stab_t / 3))
            self.score += 10 * self.combo * dt
        else:
            self.stab_t, self.combo = 0.0, 1
        if abs(self.roll) > 80:
            return self.finish(False, "ШТОПОР", "Крен больше 80 градусов")
        if self.speed >= 99:
            return self.finish(False, "РАЗРУШЕНИЕ", "Перегрузка по скорости")
        if self.prog >= 100:
            return self.land()
        if self.alt <= 0:
            return self.finish(False, "СТОЛКНОВЕНИЕ С ЗЕМЛЁЙ", "Высота кончилась до посадки")

    def land(self):
        bad = []
        if not 14 <= self.speed <= 50:
            bad.append(f"скорость {self.speed:.0f}")
        if abs(self.roll) > 8:
            bad.append(f"крен {self.roll:+.0f}°")
        if abs(self.pitch) > 8:
            bad.append(f"тангаж {self.pitch:+.0f}°")
        if self.alt > 30:
            bad.append(f"высота {self.alt:.0f}")
        if bad:
            return self.finish(False, "ЖЁСТКАЯ ПОСАДКА", ", ".join(bad))
        bonus = 500 + self.fuel * 5 + max(0, 60 - abs(self.speed - 30) * 3) + (30 - abs(self.roll)) * 2
        self.score += bonus
        self.finish(True, "ПОСАДКА УСПЕШНА!", f"Бонус +{bonus:.0f}   Топлива осталось {self.fuel:.0f}%")

    def finish(self, ok, title, why):
        self.state = "over"
        self.best = max(self.best, int(self.score))
        self.result = (title, why, GREEN if ok else RED)

    # ----- сообщения -----
    def warning(self):
        if self.event_t > 0:
            return self.event, AMBER
        if self.speed < 14:
            return "СВАЛИВАНИЕ! ДОБАВЬ ТЯГУ", RED
        if self.speed > 85:
            return "ПЕРЕГРУЗКА! СБРОСЬ ТЯГУ", RED
        if abs(self.roll) > 55:
            return "КРЕН! ВЫРАВНИВАЙ", RED
        if self.alt < 12:
            return "ВЫСОТА! ТЯНИ ВВЕРХ", RED
        if self.fuel < 20 and self.fuel > 0:
            return "МАЛО ТОПЛИВА", AMBER
        if self.fuel <= 0:
            return "ДВИГАТЕЛЬ ОСТАНОВЛЕН", RED
        if self.prog > 80:
            return "ПОСАДКА: скорость 14-50, крен/тангаж до 8°, высота до 30", GREEN
        return "", INK

    # ----- отрисовка -----
    def draw(self):
        c = self.cv
        c.delete("all")
        txt(c, 24, 28, "COCKPIT RESCUE", 20, AMBER, anchor="w")
        txt(c, W - 24, 28, "стрелки: штурвал   W/S: тяга   мышь: тяни приборы", 10, MUTE, False, "e")
        for key in CELLS:
            x, y = CELLS[key]
            c.create_rectangle(x - 170, y - 150, x + 170, y + 150, fill=CARD, outline=EDGE, width=1)
        draw_fuel(c, *CELLS["fuel"], self.fuel, self.frame)
        draw_speed(c, *CELLS["speed"], self.speed, self.frame)
        draw_knob(c, *CELLS["knob"], self.thr)
        draw_att(c, *CELLS["att"], self.pitch, self.roll, self.alt, self.prog > 78)
        # HUD
        y0 = 686
        msg, col = self.warning()
        if msg:
            txt(c, W / 2, y0, msg, 14, col)
        c.create_rectangle(30, y0 + 22, W - 30, y0 + 40, fill=CARD, outline=EDGE)
        c.create_rectangle(30, y0 + 22, 30 + (W - 60) * self.prog / 100, y0 + 40, fill=mix(CARD, BLUE, .8),
                           outline="")
        px = 30 + (W - 60) * min(self.prog, 100) / 100
        c.create_polygon(px + 12, y0 + 31, px - 4, y0 + 23, px - 4, y0 + 39, fill=AMBER, outline="")
        txt(c, 30, y0 + 56, f"ДИСТАНЦИЯ {self.prog:3.0f}%", 11, MUTE, anchor="w")
        txt(c, W - 30, y0 + 56, "ПОСАДКА", 11, GREEN, anchor="e")
        txt(c, 30, y0 + 84, f"СЧЁТ {self.score:6.0f}", 18, INK, anchor="w")
        txt(c, W / 2, y0 + 84, f"КОМБО x{self.combo}", 18, AMBER if self.combo > 1 else MUTE)
        txt(c, W - 30, y0 + 84, f"РЕКОРД {self.best}", 14, MUTE, anchor="e")
        if self.state != "play":
            c.create_rectangle(80, 250, W - 80, 520, fill="#070a0f", outline=AMBER, width=2)
            if self.state == "ready":
                txt(c, W / 2, 292, "COCKPIT RESCUE", 28, AMBER)
                lines = ["Турбулентность качает самолёт. Держи горизонт ровным,",
                         "скорость в зелёной зоне, следи за топливом и высотой.",
                         "Долети до 100% и посади машину:",
                         "скорость 14-50, крен и тангаж до 8°, высота до 30."]
                for i, s in enumerate(lines):
                    txt(c, W / 2, 345 + i * 26, s, 12, INK, False)
                txt(c, W / 2, 478, "Space / клик: взлёт", 15, AMBER)
            else:
                title, why, col = self.result
                txt(c, W / 2, 310, title, 28, col)
                txt(c, W / 2, 356, why, 13, INK, False)
                txt(c, W / 2, 410, f"СЧЁТ {self.score:.0f}    РЕКОРД {self.best}", 20, INK)
                txt(c, W / 2, 478, "Space / клик: ещё раз", 15, AMBER)

    def loop(self):
        now = time.time()
        dt = min(.05, now - self.last)
        self.last = now
        self.frame += 1
        self.update(dt)
        self.draw()
        self.after(33, self.loop)


if __name__ == "__main__":
    Game().mainloop()
