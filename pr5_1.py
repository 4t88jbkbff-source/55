import pygame
import math
import random

# Инициализация
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ferrari Dashboard Simulator")
clock = pygame.time.Clock()

# Цвета (Неоновая палитра)
BG_COLOR = (15, 15, 20)
NEON_RED = (255, 30, 50)
NEON_BLUE = (0, 200, 255)
NEON_YELLOW = (255, 220, 0)
WHITE = (240, 240, 240)
DARK_GRAY = (40, 40, 45)

# --- Класс Прибора (Спидометр/Тахометр) ---
class Gauge:
    def __init__(self, x, y, radius, max_value, label, unit, redline_start=0.8, color=NEON_BLUE):
        self.x = x
        self.y = y
        self.radius = radius
        self.max_value = max_value
        self.label = label
        self.unit = unit
        self.redline_start = redline_start
        self.color = color

        # Физика стрелки (для плавности)
        self.current_value = 0
        self.target_value = 0
        self.velocity = 0

        # Углы (от 135 градусов до 405 (45))
        self.start_angle = math.radians(135)
        self.end_angle = math.radians(405)
        self.angle_range = self.end_angle - self.start_angle

    def update(self, target):
        self.target_value = target
        # Пружинная физика стрелки (сочность)
        force = (self.target_value - self.current_value) * 0.15
        self.velocity += force
        self.velocity *= 0.85 # Трение
        self.current_value += self.velocity

    def draw(self, surface):
        # 1. Циферблат (фон)
        pygame.draw.circle(surface, (25, 25, 30), (self.x, self.y), self.radius)
        pygame.draw.circle(surface, (60, 60, 70), (self.x, self.y), self.radius, 4)

        # 2. Шкала и цифры
        font = pygame.font.SysFont("Arial", 18, bold=True)
        for i in range(0, int(self.max_value) + 1, int(self.max_value/10) if self.max_value > 10 else 1):
            angle = self.start_angle + (i / self.max_value) * self.angle_range
            # Линии делений
            x1 = self.x + math.cos(angle) * (self.radius - 20)
            y1 = self.y + math.sin(angle) * (self.radius - 20)
            x2 = self.x + math.cos(angle) * (self.radius - 35)
            y2 = self.y + math.sin(angle) * (self.radius - 35)

            # Красная зона
            if i >= self.max_value * self.redline_start:
                col = NEON_RED
            else:
                col = WHITE

            pygame.draw.line(surface, col, (x1, y1), (x2, y2), 3)

            # Цифры
            if i % (int(self.max_value/10) if self.max_value > 10 else 1) == 0:
                text_x = self.x + math.cos(angle) * (self.radius - 55)
                text_y = self.y + math.sin(angle) * (self.radius - 55)
                text = font.render(str(int(i)), True, WHITE)
                text_rect = text.get_rect(center=(text_x, text_y))
                surface.blit(text, text_rect)

        # 3. Название прибора
        label_font = pygame.font.SysFont("Arial", 20, bold=True)
        lbl = label_font.render(self.label, True, self.color)
        surface.blit(lbl, (self.x - lbl.get_width()//2, self.y + self.radius//2 - 20))

        unit_font = pygame.font.SysFont("Arial", 14)
        unt = unit_font.render(self.unit, True, (150, 150, 150))
        surface.blit(unt, (self.x - unt.get_width()//2, self.y + self.radius//2 + 5))

        # 4. Свечение стрелки (сочность)
        current_angle = self.start_angle + (self.current_value / self.max_value) * self.angle_range
        # Ограничение угла
        if self.current_value > self.max_value: current_angle = self.end_angle

        # Создаем поверхность для свечения
        glow_surf = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
        glow_center = (self.radius, self.radius)

        # Рисуем размытую стрелку (свечение)
        glow_end = (self.radius + math.cos(current_angle) * (self.radius - 40),
                    self.radius + math.sin(current_angle) * (self.radius - 40))
        pygame.draw.line(glow_surf, (*self.color, 50), glow_center, glow_end, 10)
        pygame.draw.line(glow_surf, (*self.color, 100), glow_center, glow_end, 5)

        surface.blit(glow_surf, (self.x - self.radius, self.y - self.radius))

        # Сама стрелка
        end_x = self.x + math.cos(current_angle) * (self.radius - 30)
        end_y = self.y + math.sin(current_angle) * (self.radius - 30)
        pygame.draw.line(surface, NEON_RED, (self.x, self.y), (end_x, end_y), 4)
        pygame.draw.circle(surface, WHITE, (self.x, self.y), 8)
        pygame.draw.circle(surface, DARK_GRAY, (self.x, self.y), 5)


# --- Основная логика ---
def main():
    # Создаем приборы
    speedometer = Gauge(WIDTH//2 + 200, HEIGHT//2, 200, 320, "km/h", "SPEED", redline_start=0.85, color=NEON_BLUE)
    tachometer = Gauge(WIDTH//2 - 200, HEIGHT//2, 160, 8, "RPM", "x1000", redline_start=0.75, color=NEON_YELLOW)

    speed = 0
    rpm = 0
    gear = 1

    running = True
    while running:
        dt = clock.tick(60) / 1000.0 # Дельта времени

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()

        # --- ФИЗИКА ---
        acceleration = 0

        if keys[pygame.K_UP]: # Газ
            acceleration = 150 # км/ч в секунду
        elif keys[pygame.K_DOWN]: # Тормоз
            acceleration = -250
        else:
            acceleration = -20 # Естественное замедление (трение)

        # Обновление скорости
        speed += acceleration * dt
        if speed < 0: speed = 0
        if speed > 320: speed = 320

        # Имитация коробки передач для оборотов
        # Чем выше скорость, тем выше передача (упрощенно)
        if speed < 40: gear = 1
        elif speed < 80: gear = 2
        elif speed < 130: gear = 3
        elif speed < 190: gear = 4
        elif speed < 250: gear = 5
        else: gear = 6

        # Формула оборотов (зависит от скорости и передачи)
        # При разгоне обороты прыгают вверх
        if acceleration > 0:
            target_rpm = (speed / (gear * 40)) * 1.5 + 2
        else:
            target_rpm = (speed / (gear * 45)) * 1.2 + 1

        # Ограничение RPM
        if target_rpm > 8: target_rpm = 8
        if target_rpm < 0.8: target_rpm = 0.8

        # Добавляем "дрожание" на холостых
        if speed < 5:
            target_rpm = 1.0 + math.sin(pygame.time.get_ticks() * 0.01) * 0.1

        # --- ОТРИСОВКА ---
        screen.fill(BG_COLOR)

        # Декоративная сетка на фоне (стиль Ferrari)
        for i in range(0, WIDTH, 50):
            pygame.draw.line(screen, (25, 25, 30), (i, 0), (i, HEIGHT))
        for i in range(0, HEIGHT, 50):
            pygame.draw.line(screen, (25, 25, 30), (0, i), (WIDTH, i))

        # Обновление и отрисовка приборов
        speedometer.update(speed)
        tachometer.update(target_rpm)

        speedometer.draw(screen)
        tachometer.draw(screen)

        # Инфо панель (Передача)
        font_gear = pygame.font.SysFont("Arial", 60, bold=True)
        gear_text = font_gear.render(str(gear), True, NEON_RED)
        screen.blit(gear_text, (WIDTH//2 - gear_text.get_width()//2, HEIGHT//2 - 40))

        font_label = pygame.font.SysFont("Arial", 20)
        lbl = font_label.render("GEAR", True, WHITE)
        screen.blit(lbl, (WIDTH//2 - lbl.get_width()//2, HEIGHT//2 + 20))

        # Подсказки управления
        font_small = pygame.font.SysFont("Arial", 16)
        screen.blit(font_small.render("UP ARROW: GAS", True, (100, 100, 100)), (20, HEIGHT - 40))
        screen.blit(font_small.render("DOWN ARROW: BRAKE", True, (100, 100, 100)), (20, HEIGHT - 20))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()