import pygame
import math
import random
import sys
import time

# =============================================================================
# КОНФИГУРАЦИЯ
# =============================================================================

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
FPS = 60
TITLE = "THERMOMETER - Измерительный Прибор"

# Цвета
COLOR_BG = (12, 14, 20)
COLOR_PANEL = (25, 28, 38)
COLOR_PANEL_LIGHT = (35, 40, 55)
COLOR_GLASS = (230, 240, 255)
COLOR_GLASS_DARK = (180, 200, 220)
COLOR_WHITE = (240, 240, 240)
COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (100, 105, 120)
COLOR_DARK_GRAY = (45, 50, 65)
COLOR_GREEN = (50, 255, 100)  # <-- ЭТО БЫЛО ПРОПУЩЕНО
COLOR_RED = (255, 60, 60)

# Температурные цвета
COLOR_FREEZING = (100, 180, 255)
COLOR_COLD = (50, 200, 220)
COLOR_NORMAL = (50, 255, 100)
COLOR_WARM = (255, 220, 0)
COLOR_HOT = (255, 140, 0)
COLOR_VERY_HOT = (255, 50, 50)

# Пределы температуры
TEMP_MIN = -40.0
TEMP_MAX = 100.0


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def clamp(v, mn, mx): return max(mn, min(v, mx))


def lerp(a, b, t): return a + (b - a) * t


def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32


def draw_text(surface, text, font, color, x, y, center=False, shadow=False):
    if shadow:
        s = font.render(text, True, COLOR_BLACK)
        r = s.get_rect()
        if center:
            r.center = (x + 2, y + 2)
        else:
            r.topleft = (x + 2, y + 2)
        surface.blit(s, r)
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)
    return rect


def get_temp_color(temp):
    if temp <= -20:
        return COLOR_FREEZING
    elif temp <= 0:
        return COLOR_COLD
    elif temp <= 25:
        return COLOR_NORMAL
    elif temp <= 50:
        return COLOR_WARM
    elif temp <= 80:
        return COLOR_HOT
    else:
        return COLOR_VERY_HOT


# =============================================================================
# ОБЪЕКТ ИЗМЕРЕНИЯ
# =============================================================================

class MeasurableObject:
    """Объект, у которого можно измерить температуру."""

    def __init__(self, x, y, name, base_temp, temp_range, color, icon_type):
        self.x = x
        self.y = y
        self.name = name
        self.base_temp = base_temp
        self.temp_range = temp_range
        self.color = color
        self.icon_type = icon_type
        self.radius = 45
        self.current_temp = base_temp + random.uniform(-5, 5)
        self.temp_timer = 0
        self.temp_interval = random.uniform(2, 4)
        self.hovered = False
        self.measured_temp = None
        self.measure_timer = 0
        self.pulse = 0

    def update(self, dt, mouse_pos):
        self.hovered = math.hypot(mouse_pos[0] - self.x, mouse_pos[1] - self.y) < self.radius
        self.pulse += dt * 3

        self.temp_timer += dt
        if self.temp_timer > self.temp_interval:
            self.temp_timer = 0
            self.temp_interval = random.uniform(2, 4)
            target = self.base_temp + random.uniform(self.temp_range[0], self.temp_range[1])
            self.current_temp = lerp(self.current_temp, target, 0.5)

        if self.measure_timer > 0:
            self.measure_timer -= dt

    def measure(self):
        self.measured_temp = self.current_temp + random.uniform(-1, 1)
        self.measure_timer = 3.0
        return self.measured_temp

    def draw(self, surface, font_small, font_tiny):
        # Тень
        pygame.draw.ellipse(surface, (0, 0, 0, 80),
                            (self.x - self.radius, self.y + self.radius - 10,
                             self.radius * 2, 20))

        # Пульс при наведении
        if self.hovered:
            glow_size = self.radius + 8 + math.sin(self.pulse) * 3
            for i in range(3, 0, -1):
                alpha = 60 // i
                s = pygame.Surface((glow_size * 2 + 20, glow_size * 2 + 20), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color, alpha),
                                   (glow_size + 10, glow_size + 10), glow_size + i)
                surface.blit(s, (self.x - glow_size - 10, self.y - glow_size - 10))

        # Основа
        pygame.draw.circle(surface, self.color, (self.x, self.y), self.radius)
        pygame.draw.circle(surface, COLOR_WHITE, (self.x, self.y), self.radius, 3)

        # Иконка
        self._draw_icon(surface)

        # Подпись
        draw_text(surface, self.name, font_small, COLOR_WHITE,
                  self.x, self.y + self.radius + 20, center=True, shadow=True)

        # Показание
        if self.measured_temp is not None and self.measure_timer > 0:
            temp_color = get_temp_color(self.measured_temp)
            draw_text(surface, f"{self.measured_temp:+.1f}°C", font_small, temp_color,
                      self.x, self.y - self.radius - 20, center=True, shadow=True)

    def _draw_icon(self, surface):
        c = self.color
        cx, cy = self.x, self.y

        if self.icon_type == "fire":
            pts = [(cx, cy - 25), (cx - 15, cy + 10), (cx + 15, cy + 10)]
            pygame.draw.polygon(surface, (255, 100, 0), pts)
            pts2 = [(cx, cy - 15), (cx - 8, cy + 8), (cx + 8, cy + 8)]
            pygame.draw.polygon(surface, (255, 220, 0), pts2)

        elif self.icon_type == "ice":
            for angle in range(0, 360, 60):
                a = math.radians(angle)
                x1 = cx + math.cos(a) * 25
                y1 = cy + math.sin(a) * 25
                pygame.draw.line(surface, COLOR_WHITE, (cx, cy), (x1, y1), 3)
                x2 = cx + math.cos(a) * 15
                y2 = cy + math.sin(a) * 15
                for da in [-30, 30]:
                    a2 = math.radians(angle + da)
                    x3 = x2 + math.cos(a2) * 8
                    y3 = y2 + math.sin(a2) * 8
                    pygame.draw.line(surface, COLOR_WHITE, (x2, y2), (x3, y3), 2)

        elif self.icon_type == "water":
            pts = [(cx, cy - 25), (cx - 15, cy + 5), (cx + 15, cy + 5)]
            pygame.draw.polygon(surface, (100, 180, 255), pts)
            pygame.draw.circle(surface, (100, 180, 255), (cx, cy + 5), 15)
            pygame.draw.circle(surface, (200, 230, 255), (cx - 5, cy), 4)

        elif self.icon_type == "body":
            pygame.draw.circle(surface, (255, 220, 180), (cx, cy - 15), 10)
            pygame.draw.rect(surface, (200, 150, 100), (cx - 10, cy - 5, 20, 25), border_radius=5)

        elif self.icon_type == "metal":
            for angle in range(0, 360, 45):
                a = math.radians(angle)
                x1 = cx + math.cos(a) * 25
                y1 = cy + math.sin(a) * 25
                pygame.draw.line(surface, (200, 200, 220), (cx, cy), (x1, y1), 5)
            pygame.draw.circle(surface, (200, 200, 220), (cx, cy), 12)
            pygame.draw.circle(surface, (100, 100, 120), (cx, cy), 6)

        elif self.icon_type == "sun":
            pygame.draw.circle(surface, (255, 220, 0), (cx, cy), 15)
            for angle in range(0, 360, 45):
                a = math.radians(angle)
                x1 = cx + math.cos(a) * 20
                y1 = cy + math.sin(a) * 20
                x2 = cx + math.cos(a) * 28
                y2 = cy + math.sin(a) * 28
                pygame.draw.line(surface, (255, 220, 0), (x1, y1), (x2, y2), 3)

        elif self.icon_type == "steam":
            for i, offset in enumerate([-15, 0, 15]):
                for j in range(3):
                    px = cx + offset + math.sin(time.time() * 3 + j) * 5
                    py = cy + 10 - j * 12
                    pygame.draw.circle(surface, (220, 220, 220), (int(px), int(py)), 8 - j)

        elif self.icon_type == "fridge":
            pygame.draw.rect(surface, COLOR_WHITE, (cx - 15, cy - 25, 30, 50), border_radius=4)
            pygame.draw.rect(surface, COLOR_GRAY, (cx - 15, cy - 25, 30, 20), border_radius=4)
            pygame.draw.circle(surface, COLOR_GRAY, (cx + 8, cy - 15), 2)


# =============================================================================
# ГРАДУСНИК
# =============================================================================

class Thermometer:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.w = width
        self.h = height
        self.temp = 20.0
        self.target_temp = 20.0
        self.velocity = 0.0
        self.bubbles = []
        self._bubble_spawn_timer = 0.0
        self.measure_active = False
        self.measure_target = None
        self.measure_countdown = 0.0
        self.measure_result = None

    def measure(self, target_temp):
        self.measure_active = True
        self.measure_target = target_temp
        self.measure_countdown = 2.0
        self.measure_result = None

    def update(self, dt):
        if self.measure_active:
            self.measure_countdown -= dt
            if self.measure_target is not None:
                self.target_temp = self.measure_target
            if self.measure_countdown <= 0:
                self.measure_active = False
                self.measure_result = self.target_temp

        force = (self.target_temp - self.temp) * 0.08
        self.velocity += force
        self.velocity *= 0.85
        self.temp += self.velocity
        self.temp = clamp(self.temp, TEMP_MIN, TEMP_MAX)

        self._bubble_spawn_timer += dt
        if self._bubble_spawn_timer > 0.1 and self.temp > 0:
            self._bubble_spawn_timer = 0
            self.bubbles.append({
                'y': random.uniform(0, 1),
                'size': random.uniform(1, 3),
                'speed': random.uniform(0.3, 0.8),
                'x_offset': random.uniform(-3, 3),
            })

        for b in self.bubbles[:]:
            b['y'] -= b['speed'] * dt
            if b['y'] < 0:
                self.bubbles.remove(b)

    def draw(self, surface, font_big, font_med, font_small):
        tube_x = self.x
        tube_y = self.y
        tube_w = self.w
        tube_h = self.h
        bulb_radius = 50
        bulb_x = tube_x + tube_w // 2
        bulb_y = tube_y + tube_h + bulb_radius - 10

        # Тень
        pygame.draw.rect(surface, (0, 0, 0, 100),
                         (tube_x + 5, tube_y + 5, tube_w, tube_h), border_radius=15)

        # Стекло
        pygame.draw.rect(surface, COLOR_GLASS, (tube_x, tube_y, tube_w, tube_h), border_radius=15)
        inner_x = tube_x + 6
        inner_y = tube_y + 6
        inner_w = tube_w - 12
        inner_h = tube_h - 12
        pygame.draw.rect(surface, (20, 22, 30), (inner_x, inner_y, inner_w, inner_h), border_radius=10)

        # Ртуть
        temp_ratio = (self.temp - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)
        temp_ratio = clamp(temp_ratio, 0, 1)
        mercury_h = inner_h * temp_ratio
        mercury_y = inner_y + inner_h - mercury_h
        mercury_color = get_temp_color(self.temp)

        if mercury_h > 0:
            for i in range(int(mercury_h)):
                t = i / max(1, mercury_h)
                r = int(mercury_color[0] * (0.7 + 0.3 * (1 - t)))
                g = int(mercury_color[1] * (0.7 + 0.3 * (1 - t)))
                b = int(mercury_color[2] * (0.7 + 0.3 * (1 - t)))
                pygame.draw.line(surface, (r, g, b),
                                 (inner_x + 2, mercury_y + i),
                                 (inner_x + inner_w - 2, mercury_y + i))

        # Блик
        pygame.draw.line(surface, (255, 255, 255, 100),
                         (inner_x + 8, mercury_y),
                         (inner_x + 8, mercury_y + mercury_h), 3)

        # Шарик
        pygame.draw.circle(surface, (0, 0, 0, 100), (bulb_x + 5, bulb_y + 5), bulb_radius)
        pygame.draw.circle(surface, COLOR_GLASS, (bulb_x, bulb_y), bulb_radius)
        pygame.draw.circle(surface, (20, 22, 30), (bulb_x, bulb_y), bulb_radius - 5)
        pygame.draw.circle(surface, mercury_color, (bulb_x, bulb_y), bulb_radius - 8)
        pygame.draw.circle(surface, (255, 255, 255, 120),
                           (bulb_x - 15, bulb_y - 15), 12)

        # Пузырьки
        for b in self.bubbles:
            bubble_y = mercury_y + mercury_h * b['y']
            if mercury_y < bubble_y < inner_y + inner_h:
                bx = inner_x + inner_w // 2 + b['x_offset']
                pygame.draw.circle(surface, (255, 255, 255, 150),
                                   (int(bx), int(bubble_y)), int(b['size']))

        # Шкала
        scale_x = tube_x + tube_w + 20
        for t in range(int(TEMP_MIN), int(TEMP_MAX) + 1, 10):
            my = tube_y + tube_h - ((t - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)) * tube_h
            pygame.draw.line(surface, COLOR_WHITE,
                             (scale_x, my), (scale_x + 15, my), 2)
            color = COLOR_WHITE
            if t <= -20:
                color = COLOR_FREEZING
            elif t <= 0:
                color = COLOR_COLD
            elif t <= 25:
                color = COLOR_NORMAL
            elif t <= 50:
                color = COLOR_WARM
            else:
                color = COLOR_HOT
            draw_text(surface, f"{t}°", font_small, color,
                      scale_x + 22, my - 7, center=False)

        # Стрелка
        indicator_y = tube_y + tube_h - temp_ratio * tube_h
        pygame.draw.polygon(surface, mercury_color, [
            (tube_x + tube_w, indicator_y),
            (tube_x + tube_w + 15, indicator_y - 8),
            (tube_x + tube_w + 15, indicator_y + 8),
        ])

        # Цифры
        temp_color = get_temp_color(self.temp)
        draw_text(surface, f"{self.temp:+.1f}°C", font_big, temp_color,
                  tube_x + tube_w // 2 + 80, self.y - 60, center=True, shadow=True)
        draw_text(surface, f"{celsius_to_fahrenheit(self.temp):+.1f}°F", font_small,
                  COLOR_GRAY, tube_x + tube_w // 2 + 80, self.y - 20, center=True)

        # Статус
        if self.measure_active:
            blink = int(time.time() * 5) % 2 == 0
            if blink:
                draw_text(surface, "ИЗМЕРЕНИЕ...", font_med, COLOR_WARM,
                          tube_x + tube_w // 2 + 80, self.y + tube_h + 30, center=True, shadow=True)
        elif self.measure_result is not None:
            draw_text(surface, "ГОТОВО", font_med, COLOR_GREEN,
                      tube_x + tube_w // 2 + 80, self.y + tube_h + 30, center=True, shadow=True)


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

        self.font_big = pygame.font.SysFont("Consolas", 56, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 22, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_tiny = pygame.font.SysFont("Arial", 11)
        self.font_title = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_hint = pygame.font.SysFont("Arial", 14)

        self.thermo = Thermometer(80, 250, 70, 350)

        # Объекты для измерения
        self.objects = [
            MeasurableObject(500, 180, "Огонь", 350, (-20, 50), (255, 80, 0), "fire"),
            MeasurableObject(700, 180, "Лёд", -15, (-10, 10), (100, 180, 255), "ice"),
            MeasurableObject(880, 180, "Солнце", 45, (-5, 15), (255, 200, 0), "sun"),
            MeasurableObject(500, 380, "Вода", 20, (-5, 15), (50, 150, 255), "water"),
            MeasurableObject(700, 380, "Человек", 36.6, (-1, 2), (255, 200, 150), "body"),
            MeasurableObject(880, 380, "Металл", 60, (-10, 20), (180, 180, 200), "metal"),
            MeasurableObject(600, 580, "Холодильник", 4, (-2, 3), (200, 240, 255), "fridge"),
            MeasurableObject(800, 580, "Пар", 95, (-10, 5), (220, 220, 220), "steam"),
        ]

        self.hover_object = None

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_r:
                    self.thermo.target_temp = 20.0
                    self.thermo.measure_result = None
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for obj in self.objects:
                        if obj.hovered:
                            temp = obj.measure()
                            self.thermo.measure(temp)
                            break

        self.hover_object = None
        for obj in self.objects:
            obj.update(0.016, mouse_pos)
            if obj.hovered:
                self.hover_object = obj

    def update(self, dt):
        self.thermo.update(dt)

    def draw(self):
        self.screen.fill(COLOR_BG)

        draw_text(self.screen, "🌡 ИЗМЕРИТЕЛЬНЫЙ ГРАДУСНИК 🌡", self.font_title, COLOR_WHITE,
                  SCREEN_WIDTH // 2, 30, center=True, shadow=True)

        hint = "Кликни мышкой по объекту — градусник измерит его температуру!"
        draw_text(self.screen, hint, self.font_hint, COLOR_GRAY,
                  SCREEN_WIDTH // 2, 70, center=True)

        if self.hover_object:
            draw_text(self.screen, f"→ {self.hover_object.name} (нажми для измерения)",
                      self.font_med, COLOR_WARM, SCREEN_WIDTH // 2, 105, center=True, shadow=True)

        self.thermo.draw(self.screen, self.font_big, self.font_med, self.font_small)

        for obj in self.objects:
            obj.draw(self.screen, self.font_small, self.font_tiny)

        draw_text(self.screen, "R — сброс  |  ESC — выход",
                  self.font_hint, COLOR_GRAY, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20, center=True)

        pygame.display.flip()

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
    print("THERMOMETER - ИЗМЕРИТЕЛЬНЫЙ ПРИБОР")
    print("=" * 60)
    print("Нажми мышкой на объект — градусник его измерит!")
    print("Объекты: огонь, лёд, солнце, вода, человек, металл, холодильник, пар")
    print("R — сброс  |  ESC — выход")
    print("=" * 60)
    App().run()


if __name__ == "__main__":
    main()