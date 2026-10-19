import math, sys
import pygame
from pygame import gfxdraw

pygame.init()
pygame.display.set_caption("GAUGE")
W, H = 1400, 760
screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
clock = pygame.time.Clock()

R = 300                       # радиус циферблата
SZ = R * 2 + 60
C = SZ // 2
A0, SWEEP, VMAX = 135, 270, 100
CENTERS = [(350, 360), (1050, 360)]

def lerp(a, b, t): return a + (b - a) * t
def clamp(v, a, b): return a if v < a else b if v > b else v
def mix(c1, c2, t): return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))
def ang(v): return math.radians(A0 + SWEEP * v / VMAX)
def pt(r, a, cx=C, cy=C): return (int(round(cx + math.cos(a) * r)), int(round(cy + math.sin(a) * r)))

def font(size):
    return pygame.font.SysFont("bahnschrift,dinalternate,segoeui,helveticaneue,arial", size, bold=True)
F_NUM, F_BIG, F_SM = font(30), font(60), font(20)

THEMES = {
    "dark": dict(bg=(6, 8, 18), bg2=(22, 24, 48), face=(12, 14, 28), face2=(34, 38, 70),
                 text=(226, 231, 255), tick=(205, 212, 245), minor=(110, 118, 165),
                 rim=(78, 84, 130), box=(8, 10, 24), boxline=(70, 130, 255), num=(120, 195, 255)),
    "light": dict(bg=(206, 206, 208), bg2=(238, 238, 240), face=(236, 236, 238), face2=(255, 255, 255),
                  text=(25, 25, 25), tick=(25, 25, 25), minor=(105, 105, 105),
                  rim=(45, 45, 48), box=(250, 250, 250), boxline=(40, 90, 210), num=(30, 80, 205)),
}
STOPS = [(0, (40, 200, 255)), (0.55, (90, 120, 255)), (0.75, (255, 200, 60)), (1, (255, 50, 60))]

def grad(t):
    for i in range(len(STOPS) - 1):
        if STOPS[i][0] <= t <= STOPS[i + 1][0]:
            k = (t - STOPS[i][0]) / (STOPS[i + 1][0] - STOPS[i][0])
            return mix(STOPS[i][1], STOPS[i + 1][1], k)
    return STOPS[-1][1]

def sector(surf, r1, r2, a1, a2, col):
    steps = max(2, int(abs(a2 - a1) / 0.04))
    pts = [pt(r2, lerp(a1, a2, i / steps)) for i in range(steps + 1)]
    pts += [pt(r1, lerp(a1, a2, i / steps)) for i in range(steps, -1, -1)]
    gfxdraw.filled_polygon(surf, pts, col)
    gfxdraw.aapolygon(surf, pts, col)

def build_dial(style, th):
    s = pygame.Surface((SZ, SZ), pygame.SRCALPHA)
    # тень и корпус
    for i in range(18, 0, -1):
        gfxdraw.filled_circle(s, C, C + 10, R + 24 + i, (0, 0, 0, 5))
    rim = th["rim"]
    for k, rr in enumerate((R + 26, R + 21, R + 16, R + 11)):
        col = mix(rim, (255, 255, 255), (0.0, 0.35, 0.12, 0.0)[k])
        gfxdraw.filled_circle(s, C, C, rr, (*col, 255))
        gfxdraw.aacircle(s, C, C, rr, (*col, 255))
    # лицо с радиальным градиентом
    for i in range(R + 8, 0, -2):
        t = i / (R + 8)
        col = mix(th["face2"], th["face"], clamp(t * 1.15, 0, 1))
        gfxdraw.filled_circle(s, C, C, i, (*col, 255))
    gfxdraw.aacircle(s, C, C, R + 8, (*mix(rim, (0, 0, 0), 0.4), 255))
    # трек шкалы
    r1, r2 = (R - 50, R - 18) if style == 0 else (R - 52, R - 16)
    a1, a2 = ang(0), ang(VMAX)
    if style == 0:
        n = 50
        for i in range(n):
            s0 = lerp(a1, a2, i / n) + 0.004
            s1 = lerp(a1, a2, (i + 1) / n) - 0.004
            sector(s, r1, r2, s0, s1, (*mix(grad(i / n), th["face"], 0.84), 255))
    else:
        sector(s, r1, r2, a1, a2, (*mix(th["face"], (0, 0, 0), 0.45), 255))
        sector(s, r1 - 2, r1, a1, a2, (*mix(rim, th["face2"], 0.4), 255))
        sector(s, r2, r2 + 2, a1, a2, (*mix(rim, th["face2"], 0.4), 255))
    # деления
    for v in range(0, VMAX + 1, 2):
        a = ang(v)
        if v % 10 == 0:
            ln, w, col = 28, 4, th["tick"]
        elif v % 10 == 5 or v % 5 == 0:
            ln, w, col = 18, 3, th["minor"]
        else:
            ln, w, col = 10, 2, th["minor"]
        p1, p2 = pt(R - 62, a), pt(R - 62 - ln, a)
        pygame.draw.line(s, col, p1, p2, w)
    for v in range(0, VMAX + 1, 10):
        im = F_NUM.render(str(v), True, th["text"])
        s.blit(im, im.get_rect(center=pt(R - 122, ang(v))))
    return s

def draw_gauge(dst, dial, cx, cy, val, peak, th, style, label, unit):
    dst.blit(dial, (cx - C, cy - C))
    lay = pygame.Surface((SZ, SZ), pygame.SRCALPHA)
    r1, r2 = (R - 50, R - 18) if style == 0 else (R - 52, R - 16)
    a1 = ang(0)
    # залитая часть шкалы
    if style == 0:
        n = 50
        for i in range(n):
            k = clamp(val / VMAX * n - i, 0, 1)
            if k <= 0:
                continue
            s0 = lerp(a1, ang(VMAX), i / n) + 0.004
            s1 = lerp(a1, ang(VMAX), (i + 1) / n) - 0.004
            c0 = mix(mix(grad(i / n), th["face"], 0.84), grad(i / n), k)
            sector(lay, r1, r2, s0, s1, (*c0, 255))
    else:
        n = 90
        for i in range(n):
            t0, t1 = i / n * VMAX, (i + 1) / n * VMAX
            if t0 >= val:
                break
            col = grad(i / n)
            e = min(t1, val)
            for g, al in ((10, 22), (6, 40)):
                sector(lay, r1 - g, r2 + g, ang(t0), ang(e) + 0.01, (*col, al))
            sector(lay, r1, r2, ang(t0), ang(e) + 0.008, (*col, 255))
    # пик
    if peak > 1:
        a = ang(peak)
        gfxdraw.filled_polygon(lay, [pt(R - 8, a), pt(R + 4, a + 0.03), pt(R + 4, a - 0.03)], (255, 255, 255, 235))
    # табло
    box = pygame.Rect(C - 82, C + int(R * 0.50), 164, 78)
    pygame.draw.rect(lay, (*th["box"], 255), box, border_radius=12)
    pygame.draw.rect(lay, (*th["boxline"], 255), box, 3, border_radius=12)
    num = F_BIG.render(str(int(round(val))), True, th["num"])
    lay.blit(num, num.get_rect(center=(box.centerx, box.centery - 4)))
    lab = F_SM.render(label, True, th["text"])
    lay.blit(lab, lab.get_rect(center=(C, C + int(R * 0.50) - 18)))
    un = F_SM.render(unit, True, th["minor"])
    lay.blit(un, un.get_rect(center=(C, box.bottom + 18)))
    # стрелка
    a = ang(val)
    px, py = -math.sin(a), math.cos(a)
    tip = (C + math.cos(a) * (R - 64), C + math.sin(a) * (R - 64))
    tail = (C - math.cos(a) * 46, C - math.sin(a) * 46)
    def needle(wmul, col):
        pts = [tip,
               (C + px * 9 * wmul, C + py * 9 * wmul),
               (tail[0] + px * 5 * wmul, tail[1] + py * 5 * wmul),
               (tail[0] - px * 5 * wmul, tail[1] - py * 5 * wmul),
               (C - px * 9 * wmul, C - py * 9 * wmul)]
        pts = [(int(x), int(y)) for x, y in pts]
        gfxdraw.filled_polygon(lay, pts, col)
        gfxdraw.aapolygon(lay, pts, col)
    for k, al in ((5, 18), (3.4, 28), (2.0, 44)):
        needle(k, (255, 40, 50, al))
    needle(1.0, (240, 36, 48, 255))
    needle(0.35, (255, 150, 150, 255))
    # красное свечение ступицы
    for rr in range(46, 0, -2):
        al = int(150 * (1 - rr / 46) ** 1.6)
        gfxdraw.filled_circle(lay, C, C, rr, (255, 50, 60, al))
    gfxdraw.filled_circle(lay, C, C, 17, (*mix(th["rim"], (0, 0, 0), 0.5), 255))
    gfxdraw.filled_circle(lay, C, C, 13, (*mix(th["rim"], (255, 255, 255), 0.55), 255))
    gfxdraw.filled_circle(lay, C, C, 6, (235, 40, 50, 255))
    gfxdraw.aacircle(lay, C, C, 17, (0, 0, 0, 255))
    dst.blit(lay, (cx - C, cy - C))

def make_bg(th):
    s = pygame.Surface((W, H))
    for y in range(H):
        pygame.draw.line(s, mix(th["bg2"], th["bg"], clamp(y / H * 1.2, 0, 1)), (0, y), (W, y))
    return s

def angle_to_value(mx, my, cx, cy):
    deg = math.degrees(math.atan2(my - cy, mx - cx)) % 360
    rel = (deg - A0) % 360
    if rel <= SWEEP:
        return rel / SWEEP * VMAX
    return VMAX if rel < SWEEP + (360 - SWEEP) / 2 else 0

def main():
    name = "dark"
    th = THEMES[name]
    dials = [build_dial(0, th), build_dial(1, th)]
    bg = make_bg(th)
    val = vel = target = peak = 0.0
    demo, t = False, 0.0
    f = font(18)
    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        t += dt
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if e.key == pygame.K_SPACE:
                    demo = not demo
                if e.key == pygame.K_r:
                    target = 0.0; demo = False
                if e.key == pygame.K_p:
                    peak = 0.0
                if e.key == pygame.K_t:
                    name = "light" if name == "dark" else "dark"
                    th = THEMES[name]
                    dials = [build_dial(0, th), build_dial(1, th)]
                    bg = make_bg(th)
        k = pygame.key.get_pressed()
        step = (90 if k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT] else 35) * dt
        if k[pygame.K_UP] or k[pygame.K_RIGHT]:
            target += step; demo = False
        if k[pygame.K_DOWN] or k[pygame.K_LEFT]:
            target -= step; demo = False
        if pygame.mouse.get_pressed()[0]:
            mx, my = pygame.mouse.get_pos()
            for cx, cy in CENTERS:
                if math.hypot(mx - cx, my - cy) < R:
                    target = angle_to_value(mx, my, cx, cy); demo = False
        if demo:
            target = clamp(50 + 50 * math.sin(t * 0.8) * (0.65 + 0.35 * math.sin(t * 0.23)), 0, 100)
        target = clamp(target, 0, VMAX)
        # пружина со слабым перелётом
        vel += ((target - val) * 70 - vel * 9.5) * dt
        val = clamp(val + vel * dt, 0, VMAX + 1.5)
        peak = max(peak, val)

        screen.blit(bg, (0, 0))
        draw_gauge(screen, dials[0], *CENTERS[0], val, peak, th, 0, "SPEED", "km/h")
        draw_gauge(screen, dials[1], *CENTERS[1], val, peak, th, 1, "POWER", "%")
        hint = f.render("Мышь / ↑↓ — значение   Shift — быстрее   Пробел — демо   T — тема   P — сброс пика   R — ноль",
                        True, th["minor"])
        screen.blit(hint, hint.get_rect(midbottom=(W // 2, H - 14)))
        pygame.display.flip()

if __name__ == "__main__":
    main()

