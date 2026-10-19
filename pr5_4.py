import pygame
import math
import random
import sys
import time

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
FPS = 60
TITLE = "GOOD / BAD Gauges - Premium Indicators"

# === ЦВЕТА (PREMIUM DARK) ===
COLOR_BG_TOP = (18, 20, 30)
COLOR_BG_BOTTOM = (8, 10, 15)
COLOR_PANEL = (28, 32, 44)
COLOR_PANEL_LIGHT = (40, 46, 62)
COLOR_PANEL_DARK = (18, 22, 32)
COLOR_WHITE = (240, 245, 255)
COLOR_SOFT_WHITE = (180, 190, 210)
COLOR_GRAY = (110, 120, 140)
COLOR_DARK_GRAY = (55, 62, 80)

# === Неон ===
COLOR_NEON_BLUE = (0, 200, 255)
COLOR_NEON_GREEN = (50, 255, 100)
COLOR_NEON_YELLOW = (255, 220, 50)
COLOR_NEON_ORANGE = (255, 140, 40)
COLOR_NEON_RED = (255, 60, 60)

# === Индикатор GOOD/BAD ===
COLOR_GOOD_BG = (230, 235, 245)
COLOR_GOOD_BORDER = (40, 45, 60)
COLOR_GOOD_TEXT = (60, 65, 80)
COLOR_GOOD_NEEDLE = (220, 50, 50)
COLOR_GOOD_FRAME_TOP = (90, 95, 110)
COLOR_GOOD_FRAME_BOTTOM = (25, 28, 38)

# === Дуговой индикатор ===
COLOR_ARC_BG = (20, 24, 34)


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def clamp(v, mn, mx): return max(mn, min(v, mx))


def lerp(a, b, t): return a + (b - a) * t


def draw_text(surface, text, font, color, x, y, center=True):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def draw_vertical_gradient(surface, rect, top_color, bottom_color):
    x, y, w, h = rect
    for i in range(h):
        t = i / h
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surface, (r, g, b), (x, y + i), (x + w, y + i))


def draw_glow_circle(surface, color, center, radius, glow=6, alpha_max=80):
    for i in range(glow, 0, -1):
        a = int(alpha_max / i)
        s = pygame.Surface((radius * 2 + glow * 4, radius * 2 + glow * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, a), (radius + glow * 2, radius + glow * 2), radius + i)
        surface.blit(s, (center[0] - radius - glow * 2, center[1] - radius - glow * 2))


def draw_glow_line(surface, color, p1, p2, width, glow=4, alpha_max=60):
    x1, y1 = p1
    x2, y2 = p2
    min_x = int(min(x1, x2) - glow * 3)
    min_y = int(min(y1, y2) - glow * 3)
    max_x = int(max(x1, x2) + glow * 3)
    max_y = int(max(y1, y2) + glow * 3)
    s = pygame.Surface((max(1, max_x - min_x), max(1, max_y - min_y)), pygame.SRCALPHA)
    local_p1 = (x1 - min_x, y1 - min_y)
    local_p2 = (x2 - min_x, y2 - min_y)
    for i in range(glow, 0, -1):
        a = int(alpha_max / i)
        pygame.draw.line(s, (*color, a), local_p1, local_p2, width + i * 2)
    surface.blit(s, (min_x, min_y))


# =============================================================================
# ИНДИКАТОР GOOD / BAD
# =============================================================================

class GoodBadGauge:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.value = 50.0
        self.target_value = 50.0
        self.velocity = 0.0
        self.auto_mode = True
        self.auto_timer = 0.0
        self.auto_interval = 2.5
        self.dragging = False

        self.font_label = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_percent = pygame.font.SysFont("Arial", 42, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 11, bold=True)
        self.font_bars = pygame.font.SysFont("Arial", 10, bold=True)

        self.bar_value = 0.75

    def update(self, dt, mouse_pos, mouse_pressed):
        if self.auto_mode and not self.dragging:
            self.auto_timer += dt
            if self.auto_timer > self.auto_interval:
                self.auto_timer = 0
                self.auto_interval = random.uniform(1.5, 3.0)
                self.target_value = random.uniform(5, 95)

        gauge_rect = pygame.Rect(self.x, self.y, self.w, self.h)

        if mouse_pressed and not self.dragging:
            if gauge_rect.collidepoint(mouse_pos):
                self.dragging = True
                self.auto_mode = False

        if not mouse_pressed:
            self.dragging = False

        if self.dragging:
            rel_x = (mouse_pos[0] - self.x) / self.w
            rel_x = clamp(rel_x, 0, 1)
            self.target_value = rel_x * 100

        force = (self.target_value - self.value) * 0.15
        self.velocity += force
        self.velocity *= 0.80
        self.value += self.velocity
        self.value = clamp(self.value, 0, 100)

        self.bar_value = lerp(self.bar_value, 1.0 - self.value / 100.0, 3 * dt)

    def get_color(self, value):
        if value < 33:
            t = value / 33
            return (int(lerp(50, 255, t)), int(lerp(220, 220, t)), int(lerp(80, 60, t)))
        elif value < 66:
            t = (value - 33) / 33
            return (255, int(lerp(220, 150, t)), int(lerp(60, 40, t)))
        else:
            t = (value - 66) / 34
            return (255, int(lerp(150, 60, t)), int(lerp(40, 60, t)))

    def draw(self, surface):
        frame_rect = pygame.Rect(self.x - 15, self.y - 15, self.w + 30, self.h + 30)

        shadow = frame_rect.copy()
        shadow.x += 5
        shadow.y += 5
        s = pygame.Surface((shadow.w, shadow.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 120), (0, 0, shadow.w, shadow.h), border_radius=20)
        surface.blit(s, shadow.topleft)

        for i in range(frame_rect.h):
            t = i / frame_rect.h
            r = int(COLOR_GOOD_FRAME_TOP[0] * (1 - t) + COLOR_GOOD_FRAME_BOTTOM[0] * t)
            g = int(COLOR_GOOD_FRAME_TOP[1] * (1 - t) + COLOR_GOOD_FRAME_BOTTOM[1] * t)
            b = int(COLOR_GOOD_FRAME_TOP[2] * (1 - t) + COLOR_GOOD_FRAME_BOTTOM[2] * t)
            pygame.draw.line(surface, (r, g, b),
                             (frame_rect.x, frame_rect.y + i),
                             (frame_rect.right, frame_rect.y + i))

        inner_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        pygame.draw.rect(inner_surf, COLOR_GOOD_BG, (0, 0, self.w, self.h), border_radius=12)
        surface.blit(inner_surf, (self.x, self.y))

        glass_surf = pygame.Surface((self.w, self.h // 2), pygame.SRCALPHA)
        for i in range(self.h // 2):
            t = i / (self.h // 2)
            a = int(80 * (1 - t))
            pygame.draw.line(glass_surf, (255, 255, 255, a), (0, i), (self.w, i))
        surface.blit(glass_surf, (self.x, self.y))

        pygame.draw.rect(surface, COLOR_GOOD_BORDER, (self.x, self.y, self.w, self.h), 2, border_radius=12)

        scale_y = self.y + 18
        scale_h = 40
        segment_w = 4
        gap = 2
        num_segments = (self.w - 40) // (segment_w + gap)

        for i in range(num_segments):
            sx = self.x + 20 + i * (segment_w + gap)
            progress = i / num_segments
            color = self.get_color(progress * 100)
            pygame.draw.rect(surface, color, (sx, scale_y, segment_w, scale_h), border_radius=2)
            pygame.draw.line(surface, (255, 255, 255, 100),
                             (sx + 1, scale_y + 2),
                             (sx + 1, scale_y + scale_h - 2), 1)

        good_font = pygame.font.SysFont("Arial", 16, bold=True)
        good_img = good_font.render("GOOD", True, COLOR_GOOD_TEXT)
        good_rotated = pygame.transform.rotate(good_img, 20)
        surface.blit(good_rotated, (self.x + 20, self.y + 62))

        bad_img = good_font.render("BAD", True, COLOR_GOOD_TEXT)
        bad_rotated = pygame.transform.rotate(bad_img, -20)
        bad_rect = bad_rotated.get_rect()
        bad_rect.topright = (self.x + self.w - 20, self.y + 62)
        surface.blit(bad_rotated, bad_rect)

        center_x = self.x + self.w // 2
        center_y = self.y + self.h // 2 + 15

        value_color = self.get_color(self.value)
        percent_str = f"{int(self.value)}"

        draw_text(surface, percent_str, self.font_percent, (0, 0, 0, 100),
                  center_x + 2, center_y + 2, center=True)
        draw_text(surface, percent_str, self.font_percent, COLOR_GOOD_TEXT,
                  center_x, center_y, center=True)

        draw_text(surface, "%", self.font_label, value_color,
                  center_x + 45, center_y - 8, center=True)

        pivot_x = self.x + self.w // 2
        pivot_y = self.y + self.h - 10

        needle_t = self.value / 100
        tip_x = self.x + 20 + needle_t * (self.w - 40)
        tip_y = self.y + 60

        needle_color = COLOR_GOOD_NEEDLE
        draw_glow_line(surface, needle_color, (pivot_x, pivot_y), (tip_x, tip_y), 3, glow=5, alpha_max=60)

        pygame.draw.line(surface, needle_color, (pivot_x, pivot_y), (tip_x, tip_y), 3)
        pygame.draw.circle(surface, needle_color, (int(tip_x), int(tip_y)), 5)
        pygame.draw.circle(surface, (255, 255, 255), (int(tip_x), int(tip_y)), 2)

        bar_w = 80
        bar_h = 20
        bar_x = self.x + self.w - bar_w - 20
        bar_y = self.y + self.h - bar_h - 12

        pygame.draw.rect(surface, COLOR_GOOD_BORDER, (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        num_bars = 10
        bar_seg_w = (bar_w - 8) / num_bars - 2
        filled = int(self.bar_value * num_bars)

        for i in range(num_bars):
            bx = bar_x + 4 + i * (bar_seg_w + 2)
            if i < filled:
                t = i / num_bars
                color = (int(lerp(50, 255, t)), int(lerp(220, 220, t)), int(lerp(80, 60, t)))
            else:
                color = (60, 65, 80)
            pygame.draw.rect(surface, color, (bx, bar_y + 4, bar_seg_w, bar_h - 8), border_radius=1)


# =============================================================================
# ДУГОВОЙ ИНДИКАТОР (ПРАВИЛЬНЫЙ)
# =============================================================================

class ArcGauge:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.value = 0.5
        self.target_value = 0.5
        self.velocity = 0.0
        self.auto_mode = True
        self.auto_timer = 0.0
        self.auto_interval = 2.0
        self.dragging = False

        # Углы в МАТЕМАТИЧЕСКОЙ системе (0 = вправо, pi/2 = ВВЕРХ)
        # Дуга сверху: от 150° (лево-верх) до 30° (право-верх)
        self.math_arc_start = math.radians(150)
        self.math_arc_end = math.radians(30)

        self.font_label = pygame.font.SysFont("Arial", 15, bold=True)
        self.font_val = pygame.font.SysFont("Consolas", 30, bold=True)

    def update(self, dt, mouse_pos, mouse_pressed):
        if self.auto_mode and not self.dragging:
            self.auto_timer += dt
            if self.auto_timer > self.auto_interval:
                self.auto_timer = 0
                self.auto_interval = random.uniform(1.5, 3.5)
                self.target_value = random.uniform(0.05, 0.95)

        dist = math.hypot(mouse_pos[0] - self.x, mouse_pos[1] - self.y)
        in_zone = (self.radius * 0.4 < dist < self.radius * 1.2)

        if mouse_pressed and not self.dragging:
            if in_zone:
                self.dragging = True
                self.auto_mode = False

        if not mouse_pressed:
            self.dragging = False

        if self.dragging:
            dx = mouse_pos[0] - self.x
            dy = mouse_pos[1] - self.y
            # Математический угол (инверсия Y)
            math_angle = math.atan2(-dy, dx)
            if math_angle < 0:
                math_angle = 0
            # Ограничиваем [30°, 150°]
            if math_angle > self.math_arc_start:
                math_angle = self.math_arc_start
            if math_angle < self.math_arc_end:
                math_angle = self.math_arc_end
            # value = 0 → 150°, value = 1 → 30°
            ratio = (self.math_arc_start - math_angle) / (self.math_arc_start - self.math_arc_end)
            self.target_value = clamp(ratio, 0, 1)

        force = (self.target_value - self.value) * 0.15
        self.velocity += force
        self.velocity *= 0.80
        self.value += self.velocity
        self.value = clamp(self.value, 0, 1)

    def get_needle_math_angle(self):
        return lerp(self.math_arc_start, self.math_arc_end, self.value)

    def get_arc_color(self, t):
        if t < 0.5:
            k = t / 0.5
            return (int(lerp(50, 250, k)), int(lerp(220, 220, k)), int(lerp(80, 60, k)))
        else:
            k = (t - 0.5) / 0.5
            return (int(lerp(250, 240, k)), int(lerp(220, 60, k)), int(lerp(60, 60, k)))

    def draw(self, surface):
        panel_w = int(self.radius * 2.4)
        panel_h = int(self.radius * 1.8)
        panel_rect = pygame.Rect(self.x - panel_w // 2, self.y - panel_h // 2, panel_w, panel_h)

        # Тень панели
        shadow = panel_rect.copy()
        shadow.x += 6
        shadow.y += 6
        s = pygame.Surface((shadow.w, shadow.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 120), (0, 0, shadow.w, shadow.h), border_radius=20)
        surface.blit(s, shadow.topleft)

        # Фон панели
        for i in range(panel_rect.h):
            t = i / panel_rect.h
            r = int(COLOR_ARC_BG[0] * (1 - t) + 5 * t)
            g = int(COLOR_ARC_BG[1] * (1 - t) + 5 * t)
            b = int(COLOR_ARC_BG[2] * (1 - t) + 10 * t)
            pygame.draw.line(surface, (r, g, b),
                             (panel_rect.x, panel_rect.y + i),
                             (panel_rect.right, panel_rect.y + i))

        pygame.draw.rect(surface, COLOR_PANEL_LIGHT, panel_rect, 3, border_radius=20)
        inner_glow = panel_rect.inflate(-8, -8)
        pygame.draw.rect(surface, (40, 50, 70), inner_glow, 1, border_radius=15)

        # === ДУГА СВЕРХУ (через много кружочков, без pygame.draw.arc) ===
        arc_r = self.radius - 30
        arc_width = 30

        num_segments = 100
        for i in range(num_segments):
            t = i / num_segments
            # Угол интерполируем от 150° до 30° (слева-верх → справа-верх)
            angle = lerp(self.math_arc_start, self.math_arc_end, t)

            # Координаты точки на дуге (с инверсией Y)
            dx = math.cos(angle)
            dy = -math.sin(angle)

            # Центр сегмента
            cx = self.x + dx * arc_r
            cy = self.y + dy * arc_r

            # Цвет: слева (t=0) зелёный, справа (t=1) красный
            color = self.get_arc_color(t)

            # Рисуем кружок (толщина дуги)
            pygame.draw.circle(surface, color, (int(cx), int(cy)), arc_width // 2 + 2)

            # Внутренний блик для объёма
            inner_cx = self.x + dx * (arc_r - 3)
            inner_cy = self.y + dy * (arc_r - 3)
            pygame.draw.circle(surface, (255, 255, 255, 40), (int(inner_cx), int(inner_cy)), arc_width // 4)

        # Внешние обводки дуги (тонкие линии поверх)
        for i in range(4):
            offset = arc_width // 2 + 3 + i
            points = []
            for j in range(40):
                t = j / 39
                angle = lerp(self.math_arc_start, self.math_arc_end, t)
                dx = math.cos(angle)
                dy = -math.sin(angle)
                px = self.x + dx * (arc_r + offset)
                py = self.y + dy * (arc_r + offset)
                points.append((px, py))
            if len(points) > 1:
                pygame.draw.lines(surface, (50, 60, 80, 100 - i * 20), False, points, 2)

        # === СТРЕЛКА ===
        needle_math_angle = self.get_needle_math_angle()

        ndx = math.cos(needle_math_angle)
        ndy = -math.sin(needle_math_angle)

        needle_len = arc_r - arc_width // 2 - 5
        tip_x = self.x + ndx * needle_len
        tip_y = self.y + ndy * needle_len

        marker_x = self.x + ndx * (arc_r + arc_width // 2 + 5)
        marker_y = self.y + ndy * (arc_r + arc_width // 2 + 5)

        value_color = self.get_arc_color(self.value)
        draw_glow_circle(surface, value_color, (int(marker_x), int(marker_y)), 10, glow=6, alpha_max=100)

        # Тень
        pygame.draw.line(surface, (0, 0, 0, 100),
                         (self.x + 3, self.y + 3),
                         (tip_x + 3, tip_y + 3), 6)

        # Стрелка
        pygame.draw.line(surface, (240, 245, 255), (self.x, self.y), (tip_x, tip_y), 5)
        pygame.draw.line(surface, (255, 255, 255), (self.x, self.y), (tip_x, tip_y), 2)

        # Наконечник
        tip_size = 14
        perp_dx = -ndy
        perp_dy = ndx
        t1 = (tip_x + perp_dx * tip_size * 0.5, tip_y + perp_dy * tip_size * 0.5)
        t2 = (tip_x - perp_dx * tip_size * 0.5, tip_y - perp_dy * tip_size * 0.5)
        t3 = (tip_x + ndx * tip_size, tip_y + ndy * tip_size)
        pygame.draw.polygon(surface, (240, 245, 255), [t1, t2, t3])
        pygame.draw.polygon(surface, (255, 255, 255), [t1, t2, t3], 2)

        # Маркер на дуге
        pygame.draw.circle(surface, value_color, (int(marker_x), int(marker_y)), 12)
        pygame.draw.circle(surface, (255, 255, 255), (int(marker_x), int(marker_y)), 12, 2)
        pygame.draw.circle(surface, (255, 255, 255), (int(marker_x), int(marker_y)), 4)

        # === ЦЕНТР ===
        draw_glow_circle(surface, value_color, (self.x, self.y), 18, glow=5, alpha_max=50)
        pygame.draw.circle(surface, (60, 70, 90), (self.x, self.y), 20)
        pygame.draw.circle(surface, (90, 100, 125), (self.x, self.y), 16)
        pygame.draw.circle(surface, (40, 48, 65), (self.x, self.y), 10)
        pygame.draw.circle(surface, value_color, (self.x, self.y), 5)

        # === ЗНАЧЕНИЕ ВНИЗУ ===
        val_str = f"{int(self.value * 100)}"
        val_color = self.get_arc_color(self.value)
        val_y = self.y + int(arc_r * 0.7)
        draw_text(surface, val_str, self.font_val, val_color,
                  self.x, val_y, center=True)
        draw_text(surface, "%", self.font_label, COLOR_SOFT_WHITE,
                  self.x + 40, val_y - 5, center=True)


# =============================================================================
# ПРИЛОЖЕНИЕ
# =============================================================================

class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_title = pygame.font.SysFont("Arial", 24, bold=True)
        self.font_sub = pygame.font.SysFont("Arial", 13)
        self.font_hint = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_label = pygame.font.SysFont("Arial", 11, bold=True)

        self.good_bad = GoodBadGauge(150, 240, 400, 260)
        self.arc_gauge = ArcGauge(880, 380, 220)

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_SPACE:
                    self.good_bad.auto_mode = not self.good_bad.auto_mode
                    self.arc_gauge.auto_mode = not self.arc_gauge.auto_mode
                if event.key == pygame.K_r:
                    self.good_bad.target_value = 50.0
                    self.arc_gauge.target_value = 0.5
                    self.good_bad.auto_mode = True
                    self.arc_gauge.auto_mode = True

        self.good_bad.update(0.016, mouse_pos, mouse_pressed)
        self.arc_gauge.update(0.016, mouse_pos, mouse_pressed)

    def update(self, dt):
        pass

    def draw_background(self):
        draw_vertical_gradient(self.screen, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
                               COLOR_BG_TOP, COLOR_BG_BOTTOM)

        for i in range(5):
            cx = 150 + i * 250
            cy = 200 + (i % 2) * 350
            s = pygame.Surface((400, 400), pygame.SRCALPHA)
            pygame.draw.circle(s, (40, 60, 100, 12), (200, 200), 180)
            self.screen.blit(s, (cx - 200, cy - 200))

        for x in range(0, SCREEN_WIDTH, 80):
            pygame.draw.line(self.screen, (22, 28, 42), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 80):
            pygame.draw.line(self.screen, (22, 28, 42), (0, y), (SCREEN_WIDTH, y))

    def draw(self):
        self.draw_background()

        draw_text(self.screen, "P R E M I U M   I N D I C A T O R S",
                  self.font_title, COLOR_WHITE,
                  SCREEN_WIDTH // 2, 35, center=True)

        pygame.draw.line(self.screen, COLOR_NEON_BLUE,
                         (SCREEN_WIDTH // 2 - 200, 60),
                         (SCREEN_WIDTH // 2 + 200, 60), 2)

        draw_text(self.screen, "GOOD / BAD   •   ARC INDICATOR",
                  self.font_sub, COLOR_NEON_BLUE,
                  SCREEN_WIDTH // 2, 80, center=True)

        panel1 = pygame.Rect(80, 130, 540, 500)
        self._draw_panel(panel1, "SYSTEM STATUS", COLOR_NEON_GREEN)

        panel2 = pygame.Rect(660, 130, 460, 500)
        self._draw_panel(panel2, "PERFORMANCE", COLOR_NEON_BLUE)

        self.good_bad.draw(self.screen)
        self.arc_gauge.draw(self.screen)

        status_colors = [
            (COLOR_NEON_GREEN, "OK"),
            (COLOR_NEON_YELLOW, "WARN"),
            (COLOR_NEON_RED, "BAD"),
        ]
        if self.good_bad.value < 33:
            s_color, s_label = status_colors[0]
        elif self.good_bad.value < 66:
            s_color, s_label = status_colors[1]
        else:
            s_color, s_label = status_colors[2]

        pulse = abs(math.sin(time.time() * 3)) * 0.7 + 0.3
        pygame.draw.circle(self.screen, s_color, (110, 155), int(6 * pulse + 4))
        draw_glow_circle(self.screen, s_color, (110, 155), 5, glow=4, alpha_max=100)
        draw_text(self.screen, s_label, self.font_label, s_color, 125, 155, center=False)

        mode_text = "AUTO" if self.good_bad.auto_mode else "MANUAL"
        mode_color = COLOR_NEON_BLUE if self.good_bad.auto_mode else COLOR_NEON_YELLOW
        pygame.draw.circle(self.screen, mode_color, (480, 155), 5)
        draw_text(self.screen, mode_text, self.font_label, mode_color, 495, 155, center=False)

        mode_text_r = "AUTO" if self.arc_gauge.auto_mode else "MANUAL"
        mode_color_r = COLOR_NEON_BLUE if self.arc_gauge.auto_mode else COLOR_NEON_YELLOW
        pygame.draw.circle(self.screen, mode_color_r, (1010, 155), 5)
        draw_text(self.screen, mode_text_r, self.font_label, mode_color_r, 1025, 155, center=False)

        hint_y = SCREEN_HEIGHT - 35
        pygame.draw.line(self.screen, COLOR_DARK_GRAY,
                         (50, hint_y - 15), (SCREEN_WIDTH - 50, hint_y - 15), 1)

        hints = [
            ("Мышь", "тянуть стрелку"),
            ("SPACE", "авто/ручной"),
            ("R", "сброс"),
            ("ESC", "выход"),
        ]

        x_start = 80
        for key, desc in hints:
            key_font = pygame.font.SysFont("Consolas", 11, bold=True)
            key_img = key_font.render(key, True, COLOR_WHITE)
            key_rect = key_img.get_rect()
            key_rect.topleft = (x_start, hint_y)

            bg = pygame.Rect(key_rect.x - 6, key_rect.y - 3, key_rect.w + 12, key_rect.h + 6)
            pygame.draw.rect(self.screen, COLOR_PANEL_LIGHT, bg, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_DARK_GRAY, bg, 1, border_radius=4)

            self.screen.blit(key_img, key_rect)
            draw_text(self.screen, desc, self.font_hint, COLOR_SOFT_WHITE,
                      key_rect.right + 8, hint_y + key_rect.h // 2, center=False)

            x_start = key_rect.right + 12 + self.font_hint.size(desc)[0] + 30

        pygame.display.flip()

    def _draw_panel(self, rect, label, accent_color):
        shadow = rect.copy()
        shadow.x += 6
        shadow.y += 6
        s = pygame.Surface((shadow.w, shadow.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 80), (0, 0, shadow.w, shadow.h), border_radius=20)
        self.screen.blit(s, shadow.topleft)

        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=20)

        pygame.draw.rect(self.screen, accent_color,
                         (rect.x + 20, rect.y, rect.w - 40, 3), border_radius=2)

        pygame.draw.rect(self.screen, COLOR_PANEL_LIGHT, rect, 2, border_radius=20)

        draw_text(self.screen, label, self.font_label, COLOR_SOFT_WHITE,
                  rect.centerx, rect.y + 25, center=True)

        pygame.draw.line(self.screen, COLOR_DARK_GRAY,
                         (rect.x + 50, rect.y + 42),
                         (rect.right - 50, rect.y + 42), 1)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


def main():
    print("=" * 60)
    print("PREMIUM INDICATORS")
    print("=" * 60)
    print("Управление:")
    print("  Мышь   - тянуть стрелку индикатора")
    print("  SPACE  - авто/ручной режим")
    print("  R      - сброс")
    print("  ESC    - выход")
    print("=" * 60)
    App().run()


if __name__ == "__main__":
    main()