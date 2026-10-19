#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEON HORIZON — аркадные гонки в стиле Forza Horizon
Установка:  pip install pygame
Запуск:     python neon_horizon.py

Управление:
  W / ↑        газ            A D / ← →   руль
  S / ↓ / Пробел  тормоз      Shift       нитро
  R  рестарт    F11 полный экран    Esc  выход
"""
import math
import random
import sys
import types

import pygame

pygame.init()
pygame.display.set_caption("NEON HORIZON")
W, H = 1280, 720
screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
clock = pygame.time.Clock()
pygame.mouse.set_visible(False)

# ───────────────────────── константы ─────────────────────────
HOR = int(H * 0.36)          # линия горизонта
VS = H * 0.38                # вертикальный масштаб дороги
HALF = W / 2
SEG_LEN = 200
ROAD_W = 2200
LANES = 3
DRAW = 170
CAM_H = 1100
CAM_DEPTH = 1 / math.tan(math.radians(50))
PLAYER_Z = CAM_H * CAM_DEPTH
MAXSPEED = SEG_LEN * 60.0
CAR_W = 580
DASH_H = 215
FOG_COL = (96, 54, 122)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def mix(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def font(size, bold=True):
    return pygame.font.SysFont("bahnschrift,dinalternate,segoeui,helveticaneue,arial", size, bold=bold)


F_TICK = font(15)
F_SMALL = font(18)
F_MED = font(26)
F_GEAR = font(92)
F_SPEED = font(108)
F_HUGE = font(210)

# ───────────────────────── трасса ─────────────────────────


class Seg:
    __slots__ = ("i", "y1", "y2", "curve", "alt", "cars", "props")

    def __init__(self, i, y1, y2, curve):
        self.i, self.y1, self.y2, self.curve = i, y1, y2, curve
        self.alt = (i // 3) % 2
        self.cars = []
        self.props = []


segs = []


def last_y():
    return segs[-1].y2 if segs else 0.0


def add_seg(curve, y):
    segs.append(Seg(len(segs), last_y(), y, curve))


def ease_in(a, b, p):
    return a + (b - a) * p * p


def ease_out(a, b, p):
    return a + (b - a) * (1 - (1 - p) ** 2)


def ease_io(a, b, p):
    return a + (b - a) * (0.5 - math.cos(p * math.pi) / 2)


def road(enter, hold, leave, curve, hill):
    sy = last_y()
    ey = sy + hill * SEG_LEN
    tot = enter + hold + leave
    for n in range(enter):
        add_seg(ease_in(0, curve, n / enter), ease_io(sy, ey, n / tot))
    for n in range(hold):
        add_seg(curve, ease_io(sy, ey, (enter + n) / tot))
    for n in range(leave):
        add_seg(ease_out(curve, 0, n / leave), ease_io(sy, ey, (enter + hold + n) / tot))


def build_track():
    road(0, 50, 0, 0, 0)
    road(30, 40, 30, 4, 0)
    road(20, 30, 20, 0, 18)
    road(25, 35, 25, -5, -10)
    road(20, 20, 20, 3, 0)
    road(20, 20, 20, -3, 0)
    road(30, 60, 30, 6, 12)
    road(25, 30, 25, 0, -20)
    road(30, 40, 30, -6, 0)
    road(20, 50, 20, 0, 10)
    road(25, 30, 25, 4, -6)
    road(25, 30, 25, -4, 0)
    road(20, 30, 20, 2, 8)
    road(30, 40, 30, -4, -10)
    road(0, 40, 0, 0, 0)
    road(30, 0, 30, 0, -last_y() / SEG_LEN)
    segs[-1].y2 = 0.0
    rnd = random.Random(7)
    for i, sg in enumerate(segs):
        if i % 10 == 0:
            sg.props.append((1.32 if (i // 10) % 2 else -1.32, "lamp", 0))
        if i % 4 == 0 and rnd.random() < 0.35:
            sg.props.append((rnd.choice((-1, 1)) * rnd.uniform(1.7, 3.4), "tree", rnd.random()))
        if i % 150 == 2:
            sg.props.append((0, "arch", (i // 150) % 3))


build_track()
N = len(segs)
TRACK_LEN = N * SEG_LEN


def seg_at(z):
    return segs[int(z // SEG_LEN) % N]


# ───────────────────────── цвета/туман ─────────────────────────
fog_n = [clamp(1 - math.exp(-((n / DRAW) ** 2) * 3.2), 0, 1) for n in range(DRAW)]
_GRASS = ((24, 56, 66), (20, 48, 58))
_RUMBLE = ((214, 38, 72), (240, 240, 246))
_ROAD = ((64, 64, 80), (57, 57, 72))
_LANE = (236, 236, 246)
GRASS = [[mix(_GRASS[a], FOG_COL, fog_n[n]) for n in range(DRAW)] for a in (0, 1)]
RUMBLE = [[mix(_RUMBLE[a], FOG_COL, fog_n[n]) for n in range(DRAW)] for a in (0, 1)]
ROADC = [[mix(_ROAD[a], FOG_COL, fog_n[n]) for n in range(DRAW)] for a in (0, 1)]
LANEC = [mix(_LANE, FOG_COL, fog_n[n]) for n in range(DRAW)]

# ───────────────────────── спрайты ─────────────────────────


def make_glow(r=64, col=(255, 190, 110)):
    s = pygame.Surface((r * 2, r * 2))
    for i in range(r, 0, -1):
        a = (1 - i / r) ** 2
        pygame.draw.circle(s, (int(col[0] * a), int(col[1] * a), int(col[2] * a)), (r, r), i)
    return s


GLOW = make_glow()


def make_car(body, w=480, h=256, brake=False):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    R = pygame.Rect
    dark = mix(body, (0, 0, 0), 0.55)
    light = mix(body, (255, 255, 255), 0.38)
    pygame.draw.ellipse(s, (0, 0, 0, 120), R(w * 0.02, h * 0.78, w * 0.96, h * 0.22))
    for x in (0.035, 0.805):
        pygame.draw.rect(s, (10, 10, 14), R(w * x, h * 0.56, w * 0.16, h * 0.38), border_radius=int(h * 0.05))
        pygame.draw.rect(s, (34, 34, 44), R(w * x + 5, h * 0.585, w * 0.16 - 10, 5), border_radius=3)
    pygame.draw.rect(s, dark, R(w * 0.07, h * 0.62, w * 0.86, h * 0.26), border_radius=int(h * 0.07))
    pygame.draw.rect(s, body, R(w * 0.05, h * 0.36, w * 0.90, h * 0.40), border_radius=int(h * 0.12))
    pygame.draw.rect(s, light, R(w * 0.09, h * 0.37, w * 0.82, h * 0.035), border_radius=4)
    pygame.draw.polygon(s, body, [(w * 0.20, h * 0.40), (w * 0.29, h * 0.08), (w * 0.71, h * 0.08), (w * 0.80, h * 0.40)])
    pygame.draw.polygon(s, (10, 14, 26), [(w * 0.245, h * 0.38), (w * 0.32, h * 0.13), (w * 0.68, h * 0.13), (w * 0.755, h * 0.38)])
    pygame.draw.polygon(s, (44, 64, 120), [(w * 0.30, h * 0.36), (w * 0.355, h * 0.15), (w * 0.43, h * 0.15), (w * 0.37, h * 0.36)])
    pygame.draw.line(s, light, (w * 0.30, h * 0.085), (w * 0.70, h * 0.085), 3)
    pygame.draw.rect(s, (12, 12, 18), R(w * 0.12, h * 0.30, w * 0.76, h * 0.045), border_radius=3)
    for x in (0.12, 0.87):
        pygame.draw.rect(s, (12, 12, 18), R(w * x - 3, h * 0.26, 6, h * 0.12))
    if brake:
        gl = pygame.Surface((w, h), pygame.SRCALPHA)
        for x in (0.10, 0.62):
            pygame.draw.ellipse(gl, (255, 40, 50, 70), R(w * x - 18, h * 0.40, w * 0.28 + 36, h * 0.22))
        s.blit(gl, (0, 0))
    lc = (255, 70, 80) if brake else (200, 20, 36)
    hc = (255, 220, 220) if brake else (255, 110, 110)
    for x in (0.10, 0.62):
        pygame.draw.rect(s, lc, R(w * x, h * 0.47, w * 0.28, h * 0.075), border_radius=5)
        pygame.draw.rect(s, hc, R(w * x + 6, h * 0.485, w * 0.28 - 12, h * 0.03), border_radius=3)
    pygame.draw.rect(s, (255, 60, 70) if brake else (120, 15, 25), R(w * 0.38, h * 0.50, w * 0.24, h * 0.02))
    pygame.draw.rect(s, (235, 235, 240), R(w * 0.41, h * 0.57, w * 0.18, h * 0.08), border_radius=3)
    pygame.draw.rect(s, (8, 8, 12), R(w * 0.16, h * 0.74, w * 0.68, h * 0.10), border_radius=6)
    for i in range(8):
        x = w * (0.18 + 0.08 * i)
        pygame.draw.line(s, (36, 36, 48), (x, h * 0.75), (x, h * 0.83), 2)
    return s


TRAFFIC_COLORS = [(230, 40, 60), (240, 190, 30), (250, 250, 250), (40, 200, 160),
                  (160, 80, 240), (255, 120, 30), (34, 34, 46)]
CAR_SPRITES = [make_car(c) for c in TRAFFIC_COLORS]
PW = int(CAR_W * HALF / CAM_H)
PH = int(PW * 256 / 480)
PLAYER_SPR = [pygame.transform.smoothscale(make_car((24, 120, 255), brake=b), (PW, PH)) for b in (False, True)]


class Car:
    __slots__ = ("z", "off", "speed", "kind", "si")


cars = []


def spawn_traffic():
    cars.clear()
    for sg in segs:
        sg.cars.clear()
    for _ in range(22):
        c = Car()
        c.z = random.uniform(4000, TRACK_LEN - 500)
        c.off = random.choice((-0.66, 0.0, 0.66)) + random.uniform(-0.08, 0.08)
        c.speed = random.uniform(0.16, 0.40) * MAXSPEED
        c.kind = random.randrange(len(CAR_SPRITES))
        c.si = int(c.z // SEG_LEN) % N
        segs[c.si].cars.append(c)
        cars.append(c)


# ───────────────────────── фон ─────────────────────────


def make_sky():
    s = pygame.Surface((W, H))
    stops = [(0, (8, 6, 36)), (0.45, (58, 28, 112)), (0.80, (214, 84, 128)), (1.0, (255, 176, 112))]
    for y in range(HOR + 1):
        t = y / HOR
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                k = (t - stops[i][0]) / (stops[i + 1][0] - stops[i][0])
                col = mix(stops[i][1], stops[i + 1][1], k)
                break
        pygame.draw.line(s, col, (0, y), (W, y))
    s.fill(_GRASS[0], (0, HOR, W, H - HOR))
    rnd = random.Random(3)
    for _ in range(140):
        y = rnd.randint(0, int(HOR * 0.55))
        b = rnd.randint(110, 255)
        s.set_at((rnd.randint(0, W - 1), y), (b, b, min(255, b + 20)))
    cx, cy, rr = W // 2, HOR - 54, 118
    gl = pygame.Surface((W, H), pygame.SRCALPHA)
    for k in range(14, 0, -1):
        pygame.draw.circle(gl, (255, 120, 150, 9), (cx, cy), rr + k * 16)
    s.blit(gl, (0, 0))
    for y in range(cy - rr, cy + rr):
        if y > HOR:
            break
        dy = y - cy
        half = int(math.sqrt(max(0, rr * rr - dy * dy)))
        if dy > -rr * 0.15:
            band = int((y - (cy - rr * 0.15)) / 9)
            if (y - cy) % (7 + band) < 3 + band // 2:
                continue
        col = mix((255, 236, 120), (255, 70, 150), (y - (cy - rr)) / (2 * rr))
        pygame.draw.line(s, col, (cx - half, y), (cx + half, y))
    return s


LH = 300
WT = W * 2


def make_mountains(color, base, amps, seed):
    rnd = random.Random(seed)
    s = pygame.Surface((WT, LH), pygame.SRCALPHA)
    ph = [rnd.random() * 6.28 for _ in amps]
    pts = [(0, LH)]
    for x in range(0, WT + 1, 8):
        h = base
        for (k, a), p in zip(amps, ph):
            h += a * math.sin(2 * math.pi * k * x / WT + p)
        pts.append((x, LH - h))
    pts.append((WT, LH))
    pygame.draw.polygon(s, color, pts)
    return s


def make_city(color, seed):
    rnd = random.Random(seed)
    s = pygame.Surface((WT, LH), pygame.SRCALPHA)
    x = 0
    while x < WT:
        bw = rnd.randint(22, 64)
        bh = rnd.randint(36, 150) if rnd.random() < 0.8 else rnd.randint(150, 230)
        pygame.draw.rect(s, color, (x, LH - bh, bw, bh))
        for wy in range(LH - bh + 8, LH - 6, 11):
            for wx in range(x + 5, x + bw - 5, 9):
                if rnd.random() < 0.22:
                    pygame.draw.rect(s, rnd.choice(((255, 214, 130), (255, 150, 190), (150, 220, 255))), (wx, wy, 3, 4))
        x += bw + rnd.randint(0, 6)
    return s


SKY = make_sky()
LAYERS = [
    (make_mountains((84, 42, 128), 70, [(3, 40), (7, 22), (13, 10)], 1), 0.25),
    (make_city((30, 18, 62), 5), 0.55),
    (make_mountains((16, 12, 38), 36, [(5, 22), (11, 12), (23, 6)], 2), 1.0),
]


def make_vignette():
    sw, sh = 64, 36
    v = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            dx = (x / (sw - 1) - 0.5) * 2
            dy = (y / (sh - 1) - 0.5) * 2
            d = math.hypot(dx, dy) / 1.414
            a = int(clamp((d - 0.45) / 0.55, 0, 1) ** 1.6 * 175)
            v.set_at((x, y), (5, 0, 16, a))
    return pygame.transform.smoothscale(v, (W, H))


VIGNETTE = make_vignette()

# ───────────────────────── приборная панель ─────────────────────────
BX, BW, NSEG = 330, 690, 69
BAR1_Y, BAR2_Y, BAR_H = 60, 134, 30
STOPS = [(0, (50, 130, 255)), (0.45, (100, 120, 255)), (0.70, (170, 90, 255)),
         (0.88, (255, 60, 190)), (1.0, (255, 50, 70))]


def grad(t):
    for i in range(len(STOPS) - 1):
        if STOPS[i][0] <= t <= STOPS[i + 1][0]:
            k = (t - STOPS[i][0]) / (STOPS[i + 1][0] - STOPS[i][0])
            return mix(STOPS[i][1], STOPS[i + 1][1], k)
    return STOPS[-1][1]


def make_dash_bg():
    s = pygame.Surface((W, DASH_H), pygame.SRCALPHA)

    def top(x):
        return 28 + 30 * ((2 * x / W - 1) ** 2)

    for x in range(W):
        yt = int(top(x))
        pygame.draw.line(s, (8, 6, 20, 244), (x, yt), (x, DASH_H))
        for k in range(1, 14):
            pygame.draw.line(s, (8, 6, 20, int(150 * (1 - k / 14) ** 2)), (x, yt - k), (x, yt - k))
    pts = [(x, top(x)) for x in range(0, W + 1, 8)]
    pygame.draw.lines(s, (70, 44, 160, 110), False, [(x, y + 2) for x, y in pts], 7)
    pygame.draw.lines(s, (160, 120, 255, 255), False, pts, 2)
    pygame.draw.circle(s, (14, 10, 34, 255), (130, 134), 88)
    pygame.draw.circle(s, (70, 50, 140, 255), (130, 134), 88, 2)
    d = pygame.Rect(250, 50, 780, 140)
    pygame.draw.rect(s, (3, 2, 9, 255), d, border_radius=16)
    pygame.draw.rect(s, (78, 60, 150, 255), d, 2, border_radius=16)
    pygame.draw.line(s, (120, 100, 200, 90), (d.x + 18, d.y + 4), (d.right - 18, d.y + 4), 1)

    def label(txt, fnt, col, pos, anchor="center"):
        im = fnt.render(txt, True, col)
        r = im.get_rect()
        setattr(r, anchor, pos)
        s.blit(im, r)

    label("RPM", F_SMALL, (150, 130, 255), (262, 75), "midleft")
    label("KM/H", F_SMALL, (120, 170, 255), (262, 149), "midleft")
    for k in range(10):
        x = BX + BW * k / 9
        label(str(k), F_TICK, (225, 190, 255) if k < 8 else (255, 110, 150), (x, 104))
        pygame.draw.line(s, (90, 70, 160, 255), (x, 94), (x, 97), 1)
    for v in range(0, 361, 60):
        x = BX + BW * v / 360
        label(str(v), F_TICK, (120, 170, 255), (x, 122))
    label("N E O N   H O R I Z O N", F_TICK, (84, 66, 150), (W // 2 - 10, 178))
    label("GEAR", F_TICK, (140, 120, 230), (130, 198))
    label("KM/H", F_SMALL, (150, 140, 230), (1236, 152), "midright")
    label("NITRO", F_TICK, (140, 120, 230), (1056, 172), "midleft")
    return s


DASH_BG = make_dash_bg()
led = pygame.Surface((W, DASH_H)).convert()


def led_bar(surf, y, value, tick):
    pitch = BW / NSEG
    sw = int(pitch) - 3
    v = clamp(value, 0, 1) * NSEG
    for i in range(NSEG):
        x = int(BX + i * pitch)
        col = grad(i / (NSEG - 1))
        if i + 1 <= v:
            k = 1.0
        elif i < v:
            k = v - i
        else:
            k = 0.0
        if k > 0:
            c = mix((22, 20, 40), col, k)
            pygame.draw.rect(surf, c, (x, y, sw, BAR_H), border_radius=2)
            if k > 0.5:
                pygame.draw.rect(surf, mix(col, (255, 255, 255), 0.55), (x + 2, y + 3, 3, BAR_H - 6))
        else:
            pygame.draw.rect(surf, (24, 21, 42), (x, y, sw, BAR_H), border_radius=2)


def draw_dash(scr, kmh, rpm, peak, gear, nitro, boosting, t):
    scr.blit(DASH_BG, (0, H - DASH_H))
    led.fill((0, 0, 0))
    limiter = rpm > 8300
    if limiter and int(t * 14) % 2 == 0:
        pitch = BW / NSEG
        for i in range(int(NSEG * 0.86), NSEG):
            pygame.draw.rect(led, (255, 210, 235), (int(BX + i * pitch), BAR1_Y, int(pitch) - 3, BAR_H), border_radius=2)
        led_bar(led, BAR1_Y, min(rpm, 8200) / 9000 * 0.86, 0)
    else:
        led_bar(led, BAR1_Y, rpm / 9000, 0)
    px = int(BX + (peak / 9000) * BW)
    pygame.draw.rect(led, (255, 255, 255), (min(px, BX + BW - 3), BAR1_Y - 5, 3, 4))
    led_bar(led, BAR2_Y, kmh / 360, 1)
    # кольцо оборотов вокруг передачи
    cx, cy, n = 130, 134, 40
    for i in range(n):
        a = math.radians(135 + 270 * i / (n - 1))
        r1, r2 = 58, 76
        p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
        p2 = (cx + math.cos(a) * r2, cy + math.sin(a) * r2)
        lit = (i + 1) / n <= rpm / 9000
        col = grad(i / (n - 1)) if lit else (26, 22, 46)
        pygame.draw.line(led, col, p1, p2, 5)
    g = F_GEAR.render(gear, True, (232, 222, 255))
    led.blit(g, g.get_rect(center=(130, 132)))
    # скорость цифрами
    ghost = F_SPEED.render("888", True, (24, 20, 44))
    led.blit(ghost, ghost.get_rect(midright=(1236, 98)))
    num = F_SPEED.render(str(int(kmh)), True, (235, 226, 255) if not boosting else (170, 235, 255))
    led.blit(num, num.get_rect(midright=(1236, 98)))
    # нитро
    for i in range(20):
        x = 1056 + i * 9
        lit = (i + 1) / 20 <= nitro
        col = mix((60, 190, 255), (200, 120, 255), i / 19) if lit else (24, 21, 42)
        pygame.draw.rect(led, col, (x, 184, 6, 12), border_radius=2)
    # свечение
    small = pygame.transform.smoothscale(led, (W // 6, DASH_H // 6))
    big = pygame.transform.smoothscale(small, (W, DASH_H))
    led.blit(big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    led.blit(big, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    scr.blit(led, (0, H - DASH_H), special_flags=pygame.BLEND_RGB_ADD)


# ───────────────────────── рендер дороги ─────────────────────────


def draw_prop(scene, off, kind, var, x1, y1, w1, s1, n):
    unit = s1 * HALF
    sx = x1 + off * w1
    fg = fog_n[n]
    if kind == "lamp":
        ph = 2900 * unit
        if ph < 5:
            return
        side = 1 if off > 0 else -1
        col = mix((46, 42, 72), FOG_COL, fg)
        tw = max(1, int(90 * unit))
        top = y1 - ph
        pygame.draw.line(scene, col, (int(sx), int(y1)), (int(sx), int(top)), tw)
        ax = sx - side * 750 * unit
        pygame.draw.line(scene, col, (int(sx), int(top)), (int(ax), int(top)), tw)
        hr = max(1, int(120 * unit))
        pygame.draw.circle(scene, (255, 232, 176), (int(ax), int(top + hr)), hr)
        gd = int(2600 * unit * (1 - fg * 0.7))
        if gd >= 6:
            g = pygame.transform.scale(GLOW, (gd, gd))
            scene.blit(g, (int(ax - gd / 2), int(top + hr - gd / 2)), special_flags=pygame.BLEND_RGB_ADD)
    elif kind == "tree":
        th = (1700 + 900 * var) * unit
        if th < 4:
            return
        pygame.draw.rect(scene, mix((54, 32, 40), FOG_COL, fg), (int(sx - 60 * unit), int(y1 - th * 0.2), max(1, int(120 * unit)), max(1, int(th * 0.2))))
        for k in range(3):
            base_y = y1 - th * 0.12 - k * th * 0.26
            top_y = base_y - th * 0.44
            hw = (600 - 130 * k) * unit
            col = mix(mix((14, 58, 70), (36, 110, 116), k / 2), FOG_COL, fg)
            pygame.draw.polygon(scene, col, [(sx - hw, base_y), (sx + hw, base_y), (sx, top_y)])
    elif kind == "arch":
        h = 3800 * unit
        if h < 8:
            return
        xl, xr = x1 - 1.16 * w1, x1 + 1.16 * w1
        col = mix((26, 24, 46), FOG_COL, fg)
        neon = ((255, 60, 170), (60, 220, 255), (255, 200, 60))[var]
        neon = mix(neon, FOG_COL, fg * 0.8)
        tw = max(2, int(170 * unit))
        pygame.draw.line(scene, col, (int(xl), int(y1)), (int(xl), int(y1 - h)), tw)
        pygame.draw.line(scene, col, (int(xr), int(y1)), (int(xr), int(y1 - h)), tw)
        beam = pygame.Rect(int(xl - tw / 2), int(y1 - h), int(xr - xl + tw), max(2, int(520 * unit)))
        pygame.draw.rect(scene, col, beam)
        pygame.draw.rect(scene, neon, beam, max(1, int(40 * unit)))
        for k in range(5):
            gx = xl + (xr - xl) * (k + 0.5) / 5
            gd = int(1500 * unit * (1 - fg * 0.6))
            if gd >= 6:
                g = pygame.transform.scale(GLOW, (gd, gd))
                tint = pygame.Surface((gd, gd))
                tint.fill(neon)
                g.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                scene.blit(g, (int(gx - gd / 2), int(y1 - h + beam.h / 2 - gd / 2)), special_flags=pygame.BLEND_RGB_ADD)


def render_world(scene, pos, player_x, bg_off):
    scene.blit(SKY, (0, 0))
    for lay, f in LAYERS:
        ox = -(int(bg_off * f) % WT)
        scene.blit(lay, (ox, HOR - LH + 4))
        scene.blit(lay, (ox + WT, HOR - LH + 4))
    scene.fill(_GRASS[0], (0, HOR, W, H - HOR))

    base_i = int(pos // SEG_LEN)
    base = segs[base_i % N]
    pct = (pos % SEG_LEN) / SEG_LEN
    pseg = seg_at(pos + PLAYER_Z)
    ppct = ((pos + PLAYER_Z) % SEG_LEN) / SEG_LEN
    camy = lerp(pseg.y1, pseg.y2, ppct) + CAM_H
    cam_x = player_x * ROAD_W

    x, dx = 0.0, -base.curve * pct
    proj = []
    for n in range(DRAW):
        seg = segs[(base_i + n) % N]
        z1 = max(n * SEG_LEN - pct * SEG_LEN, 250.0)
        z2 = (n + 1) * SEG_LEN - pct * SEG_LEN
        s1 = CAM_DEPTH / z1
        s2 = CAM_DEPTH / z2
        x1 = HALF + s1 * (x - cam_x) * HALF
        x2 = HALF + s2 * (x + dx - cam_x) * HALF
        y1 = HOR - s1 * (seg.y1 - camy) * VS
        y2 = HOR - s2 * (seg.y2 - camy) * VS
        proj.append((seg, x1, y1, s1 * ROAD_W * HALF, s1, x2, y2, s2 * ROAD_W * HALF, s2, n))
        x += dx
        dx += seg.curve

    draw = pygame.draw
    for k in range(DRAW - 1, -1, -1):
        seg, x1, y1, w1, s1, x2, y2, w2, s2, n = proj[k]
        alt = seg.alt
        if y2 < y1 and y1 > HOR:
            top = int(y2)
            draw.rect(scene, GRASS[alt][n], (0, top, W, int(y1) + 1 - top))
            r1, r2 = w1 / 6, w2 / 6
            rc = RUMBLE[alt][n]
            draw.polygon(scene, rc, [(x1 - w1 - r1, y1), (x1 - w1, y1), (x2 - w2, y2), (x2 - w2 - r2, y2)])
            draw.polygon(scene, rc, [(x1 + w1 + r1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 + w2 + r2, y2)])
            draw.polygon(scene, ROADC[alt][n], [(x1 - w1, y1), (x1 + w1, y1), (x2 + w2, y2), (x2 - w2, y2)])
            if alt == 0:
                lw1, lw2 = w1 / 38, w2 / 38
                for lane in range(1, LANES):
                    lx1 = x1 - w1 + (2 * w1 / LANES) * lane
                    lx2 = x2 - w2 + (2 * w2 / LANES) * lane
                    draw.polygon(scene, LANEC[n], [(lx1 - lw1, y1), (lx1 + lw1, y1), (lx2 + lw2, y2), (lx2 - lw2, y2)])
        for off, kind, var in seg.props:
            draw_prop(scene, off, kind, var, x1, y1, w1, s1, n)
        for c in seg.cars:
            p = (c.z % SEG_LEN) / SEG_LEN
            s = lerp(s1, s2, p)
            sx = lerp(x1, x2, p) + s * c.off * ROAD_W * HALF
            sy = lerp(y1, y2, p)
            cw = int(s * CAR_W * HALF)
            if cw < 4 or cw > 1500:
                continue
            ch = int(cw * 256 / 480)
            sc = pygame.transform.smoothscale(CAR_SPRITES[c.kind], (cw, ch))
            sc.set_alpha(int(255 * (1 - fog_n[n] * 0.85)))
            scene.blit(sc, (int(sx - cw / 2), int(sy - ch)))


# ───────────────────────── HUD / эффекты ─────────────────────────


def text(surf, fnt, s, pos, col=(255, 255, 255), anchor="topleft", shadow=True):
    im = fnt.render(s, True, col)
    r = im.get_rect()
    setattr(r, anchor, pos)
    if shadow:
        sh = fnt.render(s, True, (0, 0, 0))
        sh.set_alpha(150)
        surf.blit(sh, r.move(2, 2))
    surf.blit(im, r)


def fmt_time(t):
    return "%d:%04.1f" % (int(t // 60), t % 60)


def speed_lines(scene, k):
    cx, cy = W / 2, HOR + 40
    for _ in range(int(46 * k)):
        a = random.random() * math.tau
        r1 = random.uniform(300, 560)
        r2 = r1 + random.uniform(80, 280) * k
        pygame.draw.line(scene, (150, 140, 210),
                         (cx + math.cos(a) * r1 * 1.55, cy + math.sin(a) * r1 * 0.9),
                         (cx + math.cos(a) * r2 * 1.55, cy + math.sin(a) * r2 * 0.9), 1)


# ───────────────────────── игра ─────────────────────────


def new_state():
    g = types.SimpleNamespace()
    g.pos = 0.0
    g.speed = 0.0
    g.px = 0.0
    g.steer = 0.0
    g.nitro = 1.0
    g.rpm = 900.0
    g.peak = 0.0
    g.lap = 1
    g.lap_t = 0.0
    g.best = None
    g.state = "count"
    g.timer = 3.4
    g.go_flash = 0.0
    g.hit = 0.0
    g.bg_off = 0.0
    g.t = 0.0
    g.boost = False
    g.brake = False
    spawn_traffic()
    return g


def main():
    scene = pygame.Surface((W, H)).convert()
    g = new_state()
    UP = [0, 55, 105, 155, 205, 255, 310]
    while True:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        g.t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if e.key == pygame.K_r:
                    g = new_state()
                if e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
        k = pygame.key.get_pressed()
        throttle = k[pygame.K_UP] or k[pygame.K_w]
        brake = k[pygame.K_DOWN] or k[pygame.K_s] or k[pygame.K_SPACE]
        left = k[pygame.K_LEFT] or k[pygame.K_a]
        right = k[pygame.K_RIGHT] or k[pygame.K_d]
        want_boost = (k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT]) and g.nitro > 0.02 and throttle

        if g.state == "count":
            g.timer -= dt
            if g.timer <= 0:
                g.state = "run"
                g.go_flash = 1.0
        else:
            g.lap_t += dt
            g.go_flash = max(0, g.go_flash - dt)

        running = g.state == "run"
        g.boost = bool(want_boost and running)
        g.brake = bool(brake and running)
        max_speed = MAXSPEED * (1.2 if g.boost else 1.0)
        if running:
            if throttle:
                acc = MAXSPEED / 3.6 * (2.0 if g.boost else 1.0)
                g.speed += acc * (1 - 0.65 * g.speed / max_speed) * dt
            elif brake:
                g.speed -= MAXSPEED * 0.65 * dt
            else:
                g.speed -= MAXSPEED * 0.10 * dt
            if brake and throttle:
                g.speed -= MAXSPEED * 0.3 * dt
            offroad = abs(g.px) > 1.08
            if offroad and g.speed > MAXSPEED * 0.28:
                g.speed -= MAXSPEED * 0.8 * dt
            if g.speed > MAXSPEED and not g.boost:
                g.speed -= MAXSPEED * 0.18 * dt
            g.speed = clamp(g.speed, 0, max_speed)
            if g.boost:
                g.nitro = max(0, g.nitro - 0.22 * dt)
            else:
                g.nitro = min(1, g.nitro + 0.045 * dt)
        else:
            offroad = False

        target = (1 if right else 0) - (1 if left else 0)
        g.steer += (target - g.steer) * min(1, dt * 8)
        sp = g.speed / MAXSPEED
        dxs = dt * 1.7 * sp
        g.px += dxs * g.steer
        pseg = seg_at(g.pos + PLAYER_Z)
        g.px -= dxs * sp * pseg.curve * 0.3
        g.px = clamp(g.px, -2.4, 2.4)
        g.pos += g.speed * dt
        if g.pos >= TRACK_LEN:
            g.pos -= TRACK_LEN
            if g.lap_t > 5 and (g.best is None or g.lap_t < g.best):
                g.best = g.lap_t
            g.lap += 1
            g.lap_t = 0.0
        g.bg_off += pseg.curve * sp * dt * 45 * (1 if running else 0)

        # трафик
        pz = g.pos + PLAYER_Z
        for c in cars:
            c.z = (c.z + c.speed * dt) % TRACK_LEN
            si = int(c.z // SEG_LEN) % N
            if si != c.si:
                segs[c.si].cars.remove(c)
                segs[si].cars.append(c)
                c.si = si
            diff = (c.z - pz + TRACK_LEN / 2) % TRACK_LEN - TRACK_LEN / 2
            if abs(diff) < 260 and abs(c.off - g.px) < CAR_W / ROAD_W * 0.95 and g.speed > c.speed:
                g.speed = c.speed * 0.55
                g.hit = 0.5
                g.px += (0.12 if g.px >= c.off else -0.12)
        g.hit = max(0, g.hit - dt)

        # передачи и обороты
        kmh = g.speed / MAXSPEED * 300
        gear = 1
        for i in range(1, 6):
            if kmh >= UP[i]:
                gear = i + 1
        lo, hi = UP[gear - 1], UP[gear]
        if kmh < 1.5:
            tgt = 900 + (5200 if throttle else 0)
        else:
            tgt = 2200 + (kmh - lo) / (hi - lo) * 5900
            if not throttle:
                tgt -= 350
        g.rpm += (tgt - g.rpm) * min(1, dt * 10)
        if g.rpm > 8700:
            g.rpm = 8700 + random.uniform(-250, 250)
        g.rpm = clamp(g.rpm, 700, 9000)
        g.peak = max(g.rpm, g.peak - 2600 * dt)
        gear_s = "N" if (kmh < 1.5 and not throttle) else str(gear)

        # рендер
        render_world(scene, g.pos, g.px, g.bg_off)
        if g.speed / MAXSPEED > 0.55:
            speed_lines(scene, (g.speed / MAXSPEED - 0.45) * (1.8 if g.boost else 1.0))
        bob = math.sin(g.t * 28) * sp * 1.6
        pbot = HOR + VS + bob
        spr = PLAYER_SPR[1 if g.brake else 0]
        rot = pygame.transform.rotozoom(spr, -g.steer * 2.6 * (0.4 + sp), 1.0)
        scene.blit(rot, rot.get_rect(midbottom=(int(HALF + g.steer * 14), int(pbot))))
        if g.boost:
            tint = pygame.Surface((W, H))
            tint.fill((6, 22, 36))
            scene.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if g.hit > 0:
            tint = pygame.Surface((W, H))
            tint.fill((int(90 * g.hit * 2), 0, 0))
            scene.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        shx = shy = 0
        amp = (6 * sp if offroad else 0) + g.hit * 22
        if amp > 0.5:
            shx, shy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        screen.fill((0, 0, 0))
        screen.blit(scene, (int(shx), int(shy)))
        screen.blit(VIGNETTE, (0, 0))

        draw_dash(screen, kmh * (1.0), g.rpm, g.peak, gear_s, g.nitro, g.boost, g.t)

        # HUD сверху
        panel = pygame.Surface((250, 84), pygame.SRCALPHA)
        pygame.draw.rect(panel, (8, 6, 22, 170), panel.get_rect(), border_radius=14)
        pygame.draw.rect(panel, (140, 110, 255, 200), panel.get_rect(), 2, border_radius=14)
        screen.blit(panel, (20, 18))
        text(screen, F_SMALL, "КРУГ %d" % g.lap, (36, 26), (170, 150, 255))
        text(screen, F_MED, fmt_time(g.lap_t), (36, 48), (255, 255, 255))
        best = "ЛУЧШИЙ  " + (fmt_time(g.best) if g.best else "--:--.-")
        text(screen, F_SMALL, best, (W - 24, 26), (255, 200, 120), "topright")
        if g.t < 9:
            a = int(255 * clamp(9 - g.t, 0, 1))
            hint = F_SMALL.render("WASD / стрелки — руль и газ  •  Пробел — тормоз  •  Shift — нитро  •  R — рестарт", True, (255, 255, 255))
            hint.set_alpha(a)
            screen.blit(hint, hint.get_rect(midtop=(W // 2, 22)))
        if g.state == "count":
            n = int(math.ceil(g.timer))
            if n >= 1:
                frac = g.timer - (n - 1)
                im = F_HUGE.render(str(n), True, (255, 255, 255))
                im.set_alpha(int(255 * clamp(frac * 1.6, 0, 1)))
                screen.blit(im, im.get_rect(center=(W // 2, 230)))
        elif g.go_flash > 0:
            im = F_HUGE.render("GO!", True, (120, 255, 190))
            im.set_alpha(int(255 * g.go_flash))
            screen.blit(im, im.get_rect(center=(W // 2, 230)))

        pygame.display.flip()


if __name__ == "__main__":
    main()
