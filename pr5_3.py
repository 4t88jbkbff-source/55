import pygame
import math
import random
import sys
import time
from datetime import datetime

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 750
FPS = 60
TITLE = "Приборы - Manometer & Clock"

# === ЦВЕТА (PREMIUM DARK) ===
COLOR_BG_TOP = (18, 20, 30)
COLOR_BG_BOTTOM = (10, 12, 18)
COLOR_PANEL = (28, 32, 44)
COLOR_PANEL_LIGHT = (38, 44, 60)
COLOR_PANEL_DARK = (20, 24, 34)
COLOR_WHITE = (240, 245, 255)
COLOR_SOFT_WHITE = (180, 190, 210)
COLOR_GRAY = (110, 120, 140)
COLOR_DARK_GRAY = (60, 70, 90)

# === НЕОН ===
COLOR_NEON_BLUE = (0, 200, 255)
COLOR_NEON_CYAN = (0, 255, 220)
COLOR_NEON_PINK = (255, 60, 180)
COLOR_NEON_ORANGE = (255, 140, 40)

# === Манометр ===
COLOR_DIAL_BG = (22, 26, 36)
COLOR_DIAL_RING_OUTER = (55, 62, 80)
COLOR_DIAL_RING_INNER = (35, 40, 55)
COLOR_DIAL_TICK = (140, 150, 175)
COLOR_DIAL_TICK_MAJOR = (220, 230, 250)
COLOR_DIAL_TEXT = (200, 210, 230)
COLOR_GREEN_ZONE = (50, 220, 100)
COLOR_YELLOW_ZONE = (255, 200, 50)
COLOR_RED_ZONE = (255, 70, 70)
COLOR_NEEDLE = (230, 235, 250)
COLOR_NEEDLE_TIP = (255, 60, 60)
COLOR_NEEDLE_HUB = (60, 70, 90)

# === Часы ===
COLOR_CLOCK_RING = (220, 50, 60)
COLOR_CLOCK_RING_DARK = (150, 30, 40)
COLOR_CLOCK_DIAL = (245, 248, 255)
COLOR_CLOCK_DIAL_RING = (40, 45, 60)
COLOR_HOUR_HAND = (25, 28, 38)
COLOR_MINUTE_HAND = (25, 28, 38)
COLOR_SECOND_HAND = (220, 50, 60)


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
    """Рисует вертикальный градиент."""
    x, y, w, h = rect
    for i in range(h):
        t = i / h
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        pygame.draw.line(surface, (r, g, b), (x, y + i), (x + w, y + i))


def draw_glow_circle(surface, color, center, radius, glow=6, alpha_max=80):
    """Рисует светящийся круг."""
    for i in range(glow, 0, -1):
        a = int(alpha_max / i)
        s = pygame.Surface((radius * 2 + glow * 4, radius * 2 + glow * 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, a), (radius + glow * 2, radius + glow * 2), radius + i)
        surface.blit(s, (center[0] - radius - glow * 2, center[1] - radius - glow * 2))


def draw_glow_line(surface, color, p1, p2, width, glow=4, alpha_max=60):
    """Рисует светящуюся линию."""
    x1, y1 = p1
    x2, y2 = p2
    min_x = min(x1, x2) - glow * 3
    min_y = min(y1, y2) - glow * 3
    max_x = max(x1, x2) + glow * 3
    max_y = max(y1, y2) + glow * 3
    s = pygame.Surface((int(max_x - min_x), int(max_y - min_y)), pygame.SRCALPHA)
    local_p1 = (x1 - min_x, y1 - min_y)
    local_p2 = (x2 - min_x, y2 - min_y)
    for i in range(glow, 0, -1):
        a = int(alpha_max / i)
        pygame.draw.line(s, (*color, a), local_p1, local_p2, width + i * 2)
    surface.blit(s, (min_x, min_y))


def draw_arc_gradient(surface, rect, start_angle, end_angle, color, width, glow=True):
    """Рисует дугу с мягким свечением."""
    if glow:
        for i in range(4, 0, -1):
            a = int(40 / i)
            s = pygame.Surface((rect.w + 30, rect.h + 30), pygame.SRCALPHA)
            inner_rect = pygame.Rect(15, 15, rect.w, rect.h)
            pygame.draw.arc(s, (*color, a), inner_rect, start_angle, end_angle, width + i * 2)
            surface.blit(s, (rect.x - 15, rect.y - 15))
    pygame.draw.arc(surface, color, rect, start_angle, end_angle, width)


# =============================================================================
# МАНОМЕТР
# =============================================================================

class Manometer:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius
        self.max_value = 120.0
        self.value = 29.0
        self.target_value = 29.0
        self.velocity = 0.0
        self.auto_mode = True
        self.auto_timer = 0.0
        self.auto_interval = 2.0
        self.dragging = False

        self.start_angle = math.radians(135)
        self.end_angle = math.radians(405)

        # Шрифты
        self.font_num = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.font_label = pygame.font.SysFont("Segoe UI", 15, bold=True)
        self.font_value = pygame.font.SysFont("Consolas", 30, bold=True)
        self.font_unit = pygame.font.SysFont("Segoe UI", 13, bold=True)

    def update(self, dt, mouse_pos, mouse_pressed):
        if self.auto_mode and not self.dragging:
            self.auto_timer += dt
            if self.auto_timer > self.auto_interval:
                self.auto_timer = 0
                self.auto_interval = random.uniform(1.5, 3.5)
                self.target_value = random.uniform(20, 100)

        if mouse_pressed and not self.dragging:
            dist = math.hypot(mouse_pos[0] - self.x, mouse_pos[1] - self.y)
            if dist < self.radius + 20:
                self.dragging = True
                self.auto_mode = False

        if not mouse_pressed:
            self.dragging = False

        if self.dragging:
            dx = mouse_pos[0] - self.x
            dy = mouse_pos[1] - self.y
            angle = math.atan2(dy, dx)
            if angle < 0: angle += 2 * math.pi
            while angle < self.start_angle: angle += 2 * math.pi
            while angle > self.end_angle: angle -= 2 * math.pi
            ratio = (angle - self.start_angle) / (self.end_angle - self.start_angle)
            ratio = clamp(ratio, 0, 1)
            self.target_value = ratio * self.max_value

        force = (self.target_value - self.value) * 0.15
        self.velocity += force
        self.velocity *= 0.80
        self.value += self.velocity
        self.value = clamp(self.value, 0, self.max_value)

    def get_needle_angle(self):
        ratio = self.value / self.max_value
        return lerp(self.start_angle, self.end_angle, ratio)

    def draw(self, surface):
        # === ВНЕШНЕЕ СВЕЧЕНИЕ ===
        value_color = self.get_value_color()
        draw_glow_circle(surface, value_color, (self.x, self.y), self.radius, glow=8, alpha_max=40)

        # === ВНЕШНЕЕ КОЛЬЦО (градиент) ===
        for i in range(12):
            r = self.radius - i
            t = i / 12
            color = (
                int(lerp(COLOR_DIAL_RING_OUTER[0], COLOR_PANEL_DARK[0], t)),
                int(lerp(COLOR_DIAL_RING_OUTER[1], COLOR_PANEL_DARK[1], t)),
                int(lerp(COLOR_DIAL_RING_OUTER[2], COLOR_PANEL_DARK[2], t))
            )
            pygame.draw.circle(surface, color, (self.x, self.y), r)

        # === ЦИФЕРБЛАТ (тёмный) ===
        pygame.draw.circle(surface, COLOR_DIAL_BG, (self.x, self.y), self.radius - 12)

        # Тонкое внутреннее кольцо
        pygame.draw.circle(surface, COLOR_DIAL_RING_INNER, (self.x, self.y), self.radius - 12, 2)

        # === ЦВЕТНЫЕ ЗОНЫ ===
        zones = [
            (0, 60, COLOR_GREEN_ZONE),
            (60, 90, COLOR_YELLOW_ZONE),
            (90, 120, COLOR_RED_ZONE),
        ]

        arc_r = self.radius - 30
        arc_rect = pygame.Rect(self.x - arc_r, self.y - arc_r, arc_r * 2, arc_r * 2)

        for v_min, v_max, color in zones:
            a1 = lerp(self.start_angle, self.end_angle, v_min / self.max_value)
            a2 = lerp(self.start_angle, self.end_angle, v_max / self.max_value)
            # Свечение зоны
            draw_arc_gradient(surface, arc_rect, a1, a2, color, 10, glow=True)

        # === МЕТКИ ===
        for v in range(0, int(self.max_value) + 1, 5):
            ratio = v / self.max_value
            angle = lerp(self.start_angle, self.end_angle, ratio)
            is_major = (v % 15 == 0)

            if is_major:
                inner_r = self.radius - 40
                outer_r = self.radius - 25
                width = 3
                color = COLOR_DIAL_TICK_MAJOR
            else:
                inner_r = self.radius - 34
                outer_r = self.radius - 25
                width = 2
                color = COLOR_DIAL_TICK

            x1 = self.x + math.cos(angle) * inner_r
            y1 = self.y + math.sin(angle) * inner_r
            x2 = self.x + math.cos(angle) * outer_r
            y2 = self.y + math.sin(angle) * outer_r
            pygame.draw.line(surface, color, (x1, y1), (x2, y2), width)

            if is_major:
                tx = self.x + math.cos(angle) * (self.radius - 58)
                ty = self.y + math.sin(angle) * (self.radius - 58)
                draw_text(surface, str(v), self.font_num, COLOR_DIAL_TEXT, tx, ty, center=True)

        # === ПОДПИСЬ "bar" ===
        bar_y = self.y + self.radius - 70
        draw_text(surface, "bar", self.font_unit, COLOR_NEON_BLUE,
                  self.x, bar_y, center=True)

        # === СТРЕЛКА ===
        needle_angle = self.get_needle_angle()
        needle_length = self.radius - 45
        tip_x = self.x + math.cos(needle_angle) * needle_length
        tip_y = self.y + math.sin(needle_angle) * needle_length

        # Свечение стрелки
        draw_glow_line(surface, value_color, (self.x, self.y), (tip_x, tip_y), 4, glow=4, alpha_max=50)

        # Основная стрелка (белая)
        pygame.draw.line(surface, COLOR_NEEDLE, (self.x, self.y), (tip_x, tip_y), 3)

        # Красный кончик
        red_len = needle_length * 0.35
        red_x = self.x + math.cos(needle_angle) * (needle_length - red_len)
        red_y = self.y + math.sin(needle_angle) * (needle_length - red_len)
        pygame.draw.line(surface, COLOR_NEEDLE_TIP, (red_x, red_y), (tip_x, tip_y), 3)

        # Колпачок стрелки (градиент)
        draw_glow_circle(surface, value_color, (self.x, self.y), 14, glow=5, alpha_max=60)
        pygame.draw.circle(surface, COLOR_DIAL_RING_OUTER, (self.x, self.y), 14)
        pygame.draw.circle(surface, COLOR_NEEDLE_HUB, (self.x, self.y), 10)
        pygame.draw.circle(surface, COLOR_NEEDLE, (self.x, self.y), 5)

        # === ЦИФРОВОЕ ЗНАЧЕНИЕ (внизу) ===
        draw_text(surface, f"{self.value:.1f}", self.font_value, value_color,
                  self.x, self.y + self.radius + 40, center=True)

    def get_value_color(self):
        if self.value > 90:
            return COLOR_RED_ZONE
        elif self.value > 60:
            return COLOR_YELLOW_ZONE
        else:
            return COLOR_GREEN_ZONE


# =============================================================================
# ЧАСЫ
# =============================================================================

class Clock:
    def __init__(self, x, y, radius):
        self.x = x
        self.y = y
        self.radius = radius

        self.font_num = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.font_digital = pygame.font.SysFont("Consolas", 28, bold=True)
        self.font_date = pygame.font.SysFont("Segoe UI", 13, bold=True)

    def update(self, dt):
        pass

    def draw(self, surface):
        now = datetime.now()
        hours = now.hour % 12
        minutes = now.minute
        seconds = now.second
        ms = now.microsecond / 1000000.0

        # === СВЕЧЕНИЕ ВОКРУГ ЧАСОВ ===
        draw_glow_circle(surface, COLOR_CLOCK_RING, (self.x, self.y), self.radius, glow=8, alpha_max=40)

        # === КРАСНЫЙ ОБОДОК (градиент) ===
        for i in range(15):
            r = self.radius - i
            t = i / 15
            color = (
                int(lerp(COLOR_CLOCK_RING[0], COLOR_CLOCK_RING_DARK[0], t)),
                int(lerp(COLOR_CLOCK_RING[1], COLOR_CLOCK_RING_DARK[1], t)),
                int(lerp(COLOR_CLOCK_RING[2], COLOR_CLOCK_RING_DARK[2], t))
            )
            pygame.draw.circle(surface, color, (self.x, self.y), r)

        # === БЕЛЫЙ ЦИФЕРБЛАТ ===
        pygame.draw.circle(surface, COLOR_CLOCK_DIAL, (self.x, self.y), self.radius - 15)

        # Тонкое кольцо внутри
        pygame.draw.circle(surface, COLOR_CLOCK_DIAL_RING, (self.x, self.y), self.radius - 15, 2)

        # === 60 МЕТОК ===
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            is_hour = (i % 5 == 0)

            if is_hour:
                inner_r = self.radius - 45
                outer_r = self.radius - 28
                width = 4
                color = COLOR_HOUR_HAND
            else:
                inner_r = self.radius - 38
                outer_r = self.radius - 28
                width = 2
                color = (120, 130, 150)

            x1 = self.x + math.cos(angle) * inner_r
            y1 = self.y + math.sin(angle) * inner_r
            x2 = self.x + math.cos(angle) * outer_r
            y2 = self.y + math.sin(angle) * outer_r
            pygame.draw.line(surface, color, (x1, y1), (x2, y2), width)

        # === ЦИФРЫ 1-12 ===
        for h in range(1, 13):
            angle = math.radians(h * 30 - 90)
            tx = self.x + math.cos(angle) * (self.radius - 65)
            ty = self.y + math.sin(angle) * (self.radius - 65)
            draw_text(surface, str(h), self.font_num, COLOR_HOUR_HAND, tx, ty, center=True)

        # === ЧАСОВАЯ СТРЕЛКА ===
        hour_angle = math.radians((hours + minutes / 60.0) * 30 - 90)
        hour_len = self.radius * 0.45
        hx = self.x + math.cos(hour_angle) * hour_len
        hy = self.y + math.sin(hour_angle) * hour_len
        # Тень
        pygame.draw.line(surface, (0, 0, 0, 50), (self.x + 2, self.y + 2), (hx + 2, hy + 2), 9)
        pygame.draw.line(surface, COLOR_HOUR_HAND, (self.x, self.y), (hx, hy), 9)
        # Закруглённый кончик
        pygame.draw.circle(surface, COLOR_HOUR_HAND, (int(hx), int(hy)), 5)

        # === МИНУТНАЯ СТРЕЛКА ===
        minute_angle = math.radians((minutes + seconds / 60.0) * 6 - 90)
        minute_len = self.radius * 0.72
        mx = self.x + math.cos(minute_angle) * minute_len
        my = self.y + math.sin(minute_angle) * minute_len
        pygame.draw.line(surface, (0, 0, 0, 50), (self.x + 2, self.y + 2), (mx + 2, my + 2), 6)
        pygame.draw.line(surface, COLOR_MINUTE_HAND, (self.x, self.y), (mx, my), 6)
        pygame.draw.circle(surface, COLOR_MINUTE_HAND, (int(mx), int(my)), 4)

        # === СЕКУНДНАЯ СТРЕЛКА (плавная) ===
        second_angle = math.radians((seconds + ms) * 6 - 90)
        second_len = self.radius * 0.82
        second_back = self.radius * 0.18

        sx = self.x + math.cos(second_angle) * second_len
        sy = self.y + math.sin(second_angle) * second_len
        sx_back = self.x - math.cos(second_angle) * second_back
        sy_back = self.y - math.sin(second_angle) * second_back

        # Свечение секундной
        draw_glow_line(surface, COLOR_SECOND_HAND, (sx_back, sy_back), (sx, sy), 2, glow=3, alpha_max=60)

        # Секундная стрелка
        pygame.draw.line(surface, COLOR_SECOND_HAND, (sx_back, sy_back), (sx, sy), 2)
        pygame.draw.circle(surface, COLOR_SECOND_HAND, (int(sx), int(sy)), 4)

        # === ЦЕНТРАЛЬНЫЙ КОЛПАЧОК ===
        pygame.draw.circle(surface, COLOR_HOUR_HAND, (self.x, self.y), 11)
        pygame.draw.circle(surface, COLOR_SECOND_HAND, (self.x, self.y), 6)
        pygame.draw.circle(surface, COLOR_CLOCK_DIAL, (self.x, self.y), 3)

        # === ЦИФРОВОЕ ВРЕМЯ ===
        time_str = now.strftime("%H:%M:%S")
        draw_text(surface, time_str, self.font_digital, COLOR_CLOCK_RING,
                  self.x, self.y + self.radius + 40, center=True)

        # Дата
        date_str = now.strftime("%d.%m.%Y")
        draw_text(surface, date_str, self.font_date, COLOR_GRAY,
                  self.x, self.y + self.radius + 68, center=True)


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

        # Шрифты
        self.font_title = pygame.font.SysFont("Segoe UI", 26, bold=True)
        self.font_subtitle = pygame.font.SysFont("Segoe UI", 13)
        self.font_hint = pygame.font.SysFont("Segoe UI", 13)
        self.font_label = pygame.font.SysFont("Segoe UI", 12, bold=True)

        # Приборы
        self.manometer = Manometer(300, 380, 200)
        self.clock_obj = Clock(880, 380, 210)

        self.active_gauge = "manometer"

        # Анимация появления
        self.intro_timer = 0.0

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
                    self.manometer.auto_mode = not self.manometer.auto_mode
                if event.key == pygame.K_r:
                    self.manometer.target_value = 29.0
                    self.manometer.auto_mode = True
                if event.key == pygame.K_1:
                    self.active_gauge = "manometer"
                if event.key == pygame.K_2:
                    self.active_gauge = "clock"

        self.manometer.update(0.016, mouse_pos, mouse_pressed)

    def update(self, dt):
        self.clock_obj.update(dt)
        self.intro_timer += dt

    def draw_background(self):
        # Вертикальный градиент
        draw_vertical_gradient(self.screen, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT),
                               COLOR_BG_TOP, COLOR_BG_BOTTOM)

        # Декоративные круги (мягкие)
        for i in range(4):
            cx = 200 + i * 300
            cy = 200 + (i % 2) * 400
            s = pygame.Surface((400, 400), pygame.SRCALPHA)
            pygame.draw.circle(s, (40, 60, 100, 15), (200, 200), 180)
            self.screen.blit(s, (cx - 200, cy - 200))

        # Лёгкая сетка
        for x in range(0, SCREEN_WIDTH, 80):
            pygame.draw.line(self.screen, (25, 30, 45), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 80):
            pygame.draw.line(self.screen, (25, 30, 45), (0, y), (SCREEN_WIDTH, y))

    def draw(self):
        self.draw_background()

        # === ЗАГОЛОВОК ===
        title_y = 40
        # Линия сверху
        pygame.draw.line(self.screen, COLOR_NEON_BLUE,
                         (SCREEN_WIDTH // 2 - 150, title_y + 25),
                         (SCREEN_WIDTH // 2 + 150, title_y + 25), 2)

        draw_text(self.screen, "P R E M I U M   G A U G E S",
                  self.font_title, COLOR_WHITE,
                  SCREEN_WIDTH // 2, title_y, center=True)

        draw_text(self.screen, "Manometer  •  Analog Clock",
                  self.font_subtitle, COLOR_NEON_BLUE,
                  SCREEN_WIDTH // 2, title_y + 45, center=True)

        # === ПАНЕЛИ ПОД ПРИБОРАМИ ===
        # Левая панель (манометр)
        panel1 = pygame.Rect(60, 130, 480, 540)
        self._draw_panel(panel1, "MANOMETER")

        # Правая панель (часы)
        panel2 = pygame.Rect(660, 130, 480, 540)
        self._draw_panel(panel2, "ANALOG CLOCK")

        # === ПРИБОРЫ ===
        self.manometer.draw(self.screen)
        self.clock_obj.draw(self.screen)

        # === ИНДИКАТОРЫ РЕЖИМА ===
        # Левая панель — режим манометра
        mode_text = "AUTO" if self.manometer.auto_mode else "MANUAL"
        mode_color = COLOR_NEON_CYAN if self.manometer.auto_mode else COLOR_NEON_ORANGE

        # Кружок-индикатор
        pygame.draw.circle(self.screen, mode_color, (100, 160), 5)
        draw_glow_circle(self.screen, mode_color, (100, 160), 5, glow=3, alpha_max=80)
        draw_text(self.screen, mode_text, self.font_label, mode_color,
                  115, 160, center=False)

        # Правая панель — LIVE
        pygame.draw.circle(self.screen, COLOR_NEON_CYAN, (700, 160), 5)
        # Пульс
        pulse = abs(math.sin(time.time() * 2)) * 0.5 + 0.5
        pygame.draw.circle(self.screen, COLOR_NEON_CYAN, (700, 160), int(5 + pulse * 3), 1)
        draw_text(self.screen, "LIVE", self.font_label, COLOR_NEON_CYAN,
                  715, 160, center=False)

        # === ПОДСКАЗКИ ===
        hint_y = SCREEN_HEIGHT - 40
        pygame.draw.line(self.screen, COLOR_DARK_GRAY,
                         (50, hint_y - 15), (SCREEN_WIDTH - 50, hint_y - 15), 1)

        hints = [
            ("SPACE", "Авто/Ручной режим манометра"),
            ("R", "Сброс к 29 bar"),
            ("ESC", "Выход"),
        ]

        x_start = 80
        for key, desc in hints:
            # Кнопка
            key_font = pygame.font.SysFont("Consolas", 12, bold=True)
            key_img = key_font.render(key, True, COLOR_WHITE)
            key_rect = key_img.get_rect()
            key_rect.topleft = (x_start, hint_y)

            # Фон кнопки
            bg = pygame.Rect(key_rect.x - 6, key_rect.y - 3, key_rect.w + 12, key_rect.h + 6)
            pygame.draw.rect(self.screen, COLOR_PANEL_LIGHT, bg, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_DARK_GRAY, bg, 1, border_radius=4)

            self.screen.blit(key_img, key_rect)
            draw_text(self.screen, desc, self.font_hint, COLOR_SOFT_WHITE,
                      key_rect.right + 10, hint_y + key_rect.h // 2, center=False)

            x_start = key_rect.right + 15 + self.font_hint.size(desc)[0] + 40

        pygame.display.flip()

    def _draw_panel(self, rect, label):
        """Рисует панель с заголовком."""
        # Тень панели
        shadow = rect.copy()
        shadow.x += 6
        shadow.y += 6
        s = pygame.Surface((shadow.w, shadow.h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 80))
        self.screen.blit(s, shadow.topleft)

        # Основа панели
        pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=20)

        # Верхняя светлая полоса (эффект стекла)
        top_strip = pygame.Rect(rect.x, rect.y, rect.w, 4)
        pygame.draw.rect(self.screen, COLOR_NEON_BLUE, top_strip, border_radius=2)

        # Внутреннее свечение контура
        pygame.draw.rect(self.screen, COLOR_PANEL_LIGHT, rect, 2, border_radius=20)

        # Заголовок панели
        draw_text(self.screen, label, self.font_label, COLOR_SOFT_WHITE,
                  rect.centerx, rect.y + 25, center=True)

        # Тонкая линия под заголовком
        pygame.draw.line(self.screen, COLOR_DARK_GRAY,
                         (rect.x + 40, rect.y + 45),
                         (rect.right - 40, rect.y + 45), 1)

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
    print("PREMIUM GAUGES - Manometer & Clock")
    print("=" * 60)
    print("Управление:")
    print("  Мышка   - тяни стрелку манометра")
    print("  SPACE   - авто/ручной режим манометра")
    print("  R       - сброс к 29 bar")
    print("  ESC     - выход")
    print("=" * 60)
    App().run()


if __name__ == "__main__":
    main()