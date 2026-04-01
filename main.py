import cv2
import mediapipe as mp
import pygame
import numpy as np
import random
import math
import os
import sys
import json

# Initialize Pygame and Mixer
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()

# Game Constants
WIDTH, HEIGHT = 1280, 720
FPS = 30
HIGH_SCORE_FILE = "highscore.json"

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 50, 50)
GREEN = (50, 200, 50)
BLUE = (50, 100, 255)
YELLOW = (255, 220, 0)
GRAY = (100, 100, 100)
DARK_GRAY = (40, 40, 40)
CYAN = (0, 255, 255)

# Setup Display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hand-Gesture Fruit Ninja")
clock = pygame.time.Clock()

# Fonts
try:
    font = pygame.font.SysFont('Arial', 40, bold=True)
    large_font = pygame.font.SysFont('Arial', 80, bold=True)
    title_font = pygame.font.SysFont('Arial', 100, bold=True)
    small_font = pygame.font.SysFont('Arial', 30, bold=True)
except:
    font = pygame.font.Font(None, 40)
    large_font = pygame.font.Font(None, 80)
    title_font = pygame.font.Font(None, 100)
    small_font = pygame.font.Font(None, 30)

# Sound Synthesis
def generate_beep_sound(frequency=440, duration=0.1, volume=0.5):
    sample_rate = 44100
    n_samples = int(round(duration * sample_rate))
    buf = np.zeros((n_samples, 2), dtype=np.int16)
    max_sample = 2**(16 - 1) - 1
    
    for s in range(n_samples):
        t = float(s) / sample_rate
        # generate sine wave
        val = int(volume * math.sin(2 * math.pi * frequency * t) * max_sample)
        buf[s][0] = val # Left
        buf[s][1] = val # Right
    return pygame.sndarray.make_sound(buf)

try:
    sound_hover = generate_beep_sound(600, 0.05, 0.2)
    sound_click = generate_beep_sound(800, 0.1, 0.4)
except Exception as e:
    print(f"Audio fallback error: {e}")
    # Dummy sound class fallback
    class DummySound:
        def play(self): pass
    sound_hover = DummySound()
    sound_click = DummySound()

# OpenCV / MediaPipe Setup
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence=0.7, 
    min_tracking_confidence=0.7, 
    max_num_hands=1
)

# Load Assets
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
images = {}
try:
    images['apple'] = pygame.image.load(os.path.join(ASSETS_DIR, 'apple.png')).convert_alpha()
    images['banana'] = pygame.image.load(os.path.join(ASSETS_DIR, 'banana.png')).convert_alpha()
    images['watermelon'] = pygame.image.load(os.path.join(ASSETS_DIR, 'watermelon.png')).convert_alpha()
    images['bomb'] = pygame.image.load(os.path.join(ASSETS_DIR, 'bomb.png')).convert_alpha()
except pygame.error as e:
    print(f"Error loading images: {e}. Falling back to default shapes.")
    for k in ['apple', 'banana', 'watermelon', 'bomb']:
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        pygame.draw.circle(surf, RED if k=='apple' else YELLOW if k=='banana' else GREEN if k=='watermelon' else BLACK, (50, 50), 50)
        images[k] = surf

def scale_image(img, scale):
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))

for k in images:
    images[k] = scale_image(images[k], 0.8)

try:
    bg_path = os.path.join(ASSETS_DIR, 'background.png')
    images['background'] = pygame.image.load(bg_path).convert()
    images['background'] = pygame.transform.scale(images['background'], (WIDTH, HEIGHT))
except Exception as e:
    print(f"Error loading background: {e}")
    bg_surf = pygame.Surface((WIDTH, HEIGHT))
    bg_surf.fill(DARK_GRAY)
    images['background'] = bg_surf

# Persistence functions
def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                return json.load(f).get("high_score", 0)
        except:
            return 0
    return 0

def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, 'w') as f:
            json.dump({"high_score": score}, f)
    except:
        pass

# UI Components
class Button:
    def __init__(self, text, x, y, width, height, base_color, hover_color):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.base_color = base_color
        self.hover_color = hover_color
        self.is_hovered = False
        self.hover_start_time = 0
        self.selection_time = 1500  # 1.5 seconds to select
        self.played_hover_sound = False
        self.scale = 1.0

    def check_hover(self, finger_x, finger_y, is_hand_detected, current_time):
        """Checks if hand is over the button and processes timer."""
        if not is_hand_detected:
            self.reset_hover()
            return False

        if self.rect.collidepoint(finger_x, finger_y):
            if not self.is_hovered:
                self.is_hovered = True
                self.hover_start_time = current_time
                if not self.played_hover_sound:
                    sound_hover.play()
                    self.played_hover_sound = True
            
            # Target scale animation
            self.scale = min(1.1, self.scale + 0.05)
            
            # Check selection condition
            hover_duration = current_time - self.hover_start_time
            if hover_duration >= self.selection_time:
                sound_click.play()
                self.reset_hover()
                return True
        else:
            self.reset_hover()
            
        return False
        
    def reset_hover(self):
        """Resets the hover states and scaling."""
        self.is_hovered = False
        self.hover_start_time = 0
        self.played_hover_sound = False
        self.scale = max(1.0, self.scale - 0.05)

    def draw(self, surface, current_time):
        """Draws the button including hover scaling and circular progress bar if hovered."""
        color = self.hover_color if self.is_hovered else self.base_color
        
        # Apply scaling logic
        center = self.rect.center
        w = int(self.rect.width * self.scale)
        h = int(self.rect.height * self.scale)
        scaled_rect = pygame.Rect(0, 0, w, h)
        scaled_rect.center = center

        # Draw Button with Glow if hovered
        if self.is_hovered:
            glow_rect = scaled_rect.inflate(20, 20)
            pygame.draw.rect(surface, (255, 255, 255, 100), glow_rect, border_radius=25)
            
        pygame.draw.rect(surface, color, scaled_rect, border_radius=20)
        pygame.draw.rect(surface, WHITE, scaled_rect, width=3, border_radius=20) # border

        # Draw Text
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=center)
        surface.blit(text_surf, text_rect)
        
        # Draw Progress Indicator (Timer arc)
        if self.is_hovered and self.hover_start_time > 0:
            hover_duration = current_time - self.hover_start_time
            progress = min(1.0, hover_duration / self.selection_time) # 0.0 to 1.0
            
            # Draw arc
            arc_rect = pygame.Rect(scaled_rect.right - 50, scaled_rect.centery - 20, 40, 40)
            start_angle = math.pi/2
            end_angle = start_angle + (progress * 2 * math.pi)
            pygame.draw.arc(surface, WHITE, arc_rect, start_angle, end_angle, 5)

# Game Entities
class GameObject:
    def __init__(self, x, y, type_name, difficulty, level=1):
        self.x = x
        self.y = y
        self.type_name = type_name
        if type_name in images:
            self.image = images[type_name]
        else:
            self.image = images['apple']
        self.radius = self.image.get_width() // 2
        
        # Velocity initialization based on level and difficulty
        self.vx = random.uniform(-2, 2)
        base_speed = 4 + (level * 1.5)
        if difficulty == "HARD":
            base_speed += 3
        
        self.vy = random.uniform(base_speed, base_speed + 4)
        self.is_sliced = False

    def update(self):
        self.vy += 0.2 # low gravity pulling down
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        if not self.is_sliced:
            rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(self.image, rect)

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-8, 8)
        self.vy = random.uniform(-8, 8)
        self.radius = random.uniform(4, 10)
        self.color = color
        self.life = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 8
        self.radius *= 0.95

    def draw(self, surface):
        if self.life > 0:
            surf = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, self.life), (int(self.radius), int(self.radius)), int(self.radius))
            surface.blit(surf, (int(self.x - self.radius), int(self.y - self.radius)))

def draw_text_center(surface, text, font_obj, color, y_offset=0):
    """Helper method to neatly print centered text"""
    text_surface = font_obj.render(text, True, color)
    text_rect = text_surface.get_rect(center=(WIDTH//2, HEIGHT//2 + y_offset))
    surface.blit(text_surface, text_rect)

def get_color_from_type(type_name):
    if type_name == 'apple': return RED
    if type_name == 'banana': return YELLOW
    if type_name == 'watermelon': return GREEN
    if type_name == 'bomb': return BLACK
    return GRAY

class HandGestureFruitNinja:
    """Main Game Class bounding States and Main Loop Logic"""
    def __init__(self):
        self.state = "HOME"
        self.score = 0
        self.level = 1
        self.high_score = load_high_score()
        self.objects = []
        self.particles = []
        self.spawn_timer = 0
        self.difficulty = "NORMAL"
        
        self.finger_x, self.finger_y = 0, 0
        self.prev_finger_x, self.prev_finger_y = 0, 0
        self.is_hand_detected = False
        self.slice_path = [] # For drawing slice effect
        
        self.running = True
        
        # UI Buttons setup
        btn_w, btn_h = 350, 80
        # Button("Text", X, Y, W, H, BaseColor, HoverColor)
        self.btn_start = Button("Start Game", WIDTH//2 - btn_w//2, HEIGHT//2 - 40, btn_w, btn_h, DARK_GRAY, GREEN)
        self.btn_highscore = Button("High Score", WIDTH//2 - btn_w//2, HEIGHT//2 + 60, btn_w, btn_h, DARK_GRAY, BLUE)
        self.btn_exit = Button("Exit", WIDTH//2 - btn_w//2, HEIGHT//2 + 160, btn_w, btn_h, DARK_GRAY, RED)
        
        self.btn_back = Button("Back", WIDTH//2 - btn_w//2, HEIGHT//2 + 160, btn_w, btn_h, DARK_GRAY, GRAY)
        self.btn_home = Button("Main Menu", WIDTH//2 - btn_w//2, HEIGHT//2 + 150, btn_w, btn_h, DARK_GRAY, GRAY)

    def draw_cursor(self, screen):
        """Draws the player's index finger indicator"""
        if self.is_hand_detected:
            # Glow logic
            glow = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 255, 255, 100), (30, 30), 20)
            screen.blit(glow, (self.finger_x - 30, self.finger_y - 30))
            
            # Core cursor
            pygame.draw.circle(screen, CYAN, (self.finger_x, self.finger_y), 10)
            pygame.draw.circle(screen, WHITE, (self.finger_x, self.finger_y), 10, 2)
            
            # Tracing effect in game (helps visualize slicing motion)
            if self.state == "GAME":
                self.slice_path.append((self.finger_x, self.finger_y))
                if len(self.slice_path) > 10:
                    self.slice_path.pop(0)
                if len(self.slice_path) > 1:
                    pygame.draw.lines(screen, (255, 255, 255, 150), False, self.slice_path, 4)
            else:
                self.slice_path.clear()

    def process_camera(self):
        """Reads frame, runs MediaPipe Hand Tracking, returns RGB Frame."""
        ret, frame = cap.read()
        if not ret:
            return None
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        self.is_hand_detected = False
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.is_hand_detected = True
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                # Map 0.1-0.9 coordinate from MediaPipe to screen dimensions for easier reach to corners
                clamped_x = max(0.1, min(0.9, index_tip.x))
                clamped_y = max(0.1, min(0.9, index_tip.y))
                hx = int(np.interp(clamped_x, [0.1, 0.9], [0, WIDTH]))
                hy = int(np.interp(clamped_y, [0.1, 0.9], [0, HEIGHT]))
                
                # Smoothen cursor using linear interpolation
                self.finger_x = int(self.finger_x * 0.4 + hx * 0.6)
                self.finger_y = int(self.finger_y * 0.4 + hy * 0.6)
                break # Process only first found hand
                
        return rgb_frame

    def draw_background(self, screen, blur=False):
        """Draws the generated game background (optional dark overlay for menus)"""
        screen.blit(images['background'], (0, 0))
        if blur:
            # Draw semi-transparent dark overlay for better text readability on menus
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

    # --- STATE FUNCTIONS ---
    def show_home_screen(self, screen, current_time):
        draw_text_center(screen, "FRUIT NINJA", title_font, WHITE, -200)
        draw_text_center(screen, "Hover with your index finger for 1.5s to select", small_font, YELLOW, -120)

        # Process and Draw Buttons
        if self.btn_start.check_hover(self.finger_x, self.finger_y, self.is_hand_detected, current_time):
            self.state = "GAME"
            self.score = 0
            self.level = 1
            self.objects.clear()
            self.particles.clear()
            self.slice_path.clear()
            
        elif self.btn_highscore.check_hover(self.finger_x, self.finger_y, self.is_hand_detected, current_time):
            self.state = "HIGH_SCORE"
            
        elif self.btn_exit.check_hover(self.finger_x, self.finger_y, self.is_hand_detected, current_time):
            self.running = False

        self.btn_start.draw(screen, current_time)
        self.btn_highscore.draw(screen, current_time)
        self.btn_exit.draw(screen, current_time)

    def show_high_score_screen(self, screen, current_time):
        draw_text_center(screen, "HIGH SCORE", title_font, WHITE, -150)
        draw_text_center(screen, str(self.high_score), large_font, YELLOW, 0)
        
        if self.btn_back.check_hover(self.finger_x, self.finger_y, self.is_hand_detected, current_time):
            self.state = "HOME"
            
        self.btn_back.draw(screen, current_time)

    def show_game_screen(self, screen, current_time):
        # Spawning mechanism
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            # Spawn rate increases with level
            spawn_count = random.randint(1, 2 + min(3, self.level // 2))
            for _ in range(spawn_count):
                x_pos = random.randint(100, WIDTH - 100)
                bomb_chance = min(0.4, 0.15 + (self.level * 0.02)) # Bomb chance maxes at 40%
                type_name = 'bomb' if random.random() < bomb_chance else random.choice(['apple', 'banana', 'watermelon'])
                # Spawn ABOVE screen (y = -100)
                self.objects.append(GameObject(x_pos, -100, type_name, self.difficulty, self.level))
            
            # Decrease spawn timer based on level
            base_time = max(20, 60 - (self.level * 5))
            self.spawn_timer = random.randint(base_time, base_time + 30)

        # Object Loop
        for obj in self.objects[:]:
            obj.update()
            obj.draw(screen)
            
            # Slicing detection
            if self.is_hand_detected and not obj.is_sliced:
                dist = math.hypot(self.finger_x - obj.x, self.finger_y - obj.y)
                if dist < obj.radius + 30: # Provide marginal leeway error
                    obj.is_sliced = True
                    if obj.type_name == 'bomb':
                        self.state = "GAME_OVER"
                        if self.score > self.high_score:
                            self.high_score = self.score
                            save_high_score(self.high_score)
                            
                        # Bomb effect
                        sound_click.play()
                        for _ in range(60):
                            self.particles.append(Particle(obj.x, obj.y, RED))
                            self.particles.append(Particle(obj.x, obj.y, YELLOW))
                    else:
                        self.score += 10
                        # Fruit slice effect
                        sound_hover.play()
                        for _ in range(20):
                            self.particles.append(Particle(obj.x, obj.y, get_color_from_type(obj.type_name)))
            
            # Remove entities that have dropped too low or got sliced
            if obj.is_sliced or obj.y > HEIGHT + 200:
                try:
                    self.objects.remove(obj)
                except ValueError:
                    pass
        
        # Particle System Draw Loop
        for p in self.particles[:]:
            p.update()
            p.draw(screen)
            if p.life <= 0:
                try: self.particles.remove(p)
                except ValueError: pass

        # Level Up Logic
        new_level = (self.score // 100) + 1
        if new_level > self.level:
            self.level = new_level
            sound_click.play()

        # Draw Score and Level
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        level_text = font.render(f"Level: {self.level}", True, YELLOW)
        screen.blit(score_text, (20, 20))
        screen.blit(level_text, (20, 60))

    def show_game_over_screen(self, screen, current_time):
        draw_text_center(screen, "GAME OVER", title_font, RED, -150)
        draw_text_center(screen, f"Final Score: {self.score}", large_font, WHITE, -30)
        
        if self.score >= self.high_score and self.score > 0:
            draw_text_center(screen, "NEW HIGH SCORE!", font, YELLOW, 50)
        
        if self.btn_home.check_hover(self.finger_x, self.finger_y, self.is_hand_detected, current_time):
            self.state = "HOME"
            
        self.btn_home.draw(screen, current_time)

    def run(self):
        """Main PyGame Loop"""
        while self.running:
            current_time = pygame.time.get_ticks()
            
            # Input Events (mostly fallback or closing event)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                
            rgb_frame = self.process_camera()
            
            # Rendering Process depending on game active state
            if self.state in ["HOME", "HIGH_SCORE", "GAME_OVER"]:
                self.draw_background(screen, blur=True)
            else:
                self.draw_background(screen, blur=False)

            # State delegation
            if self.state == "HOME":
                self.show_home_screen(screen, current_time)
            elif self.state == "GAME":
                self.show_game_screen(screen, current_time)
            elif self.state == "HIGH_SCORE":
                self.show_high_score_screen(screen, current_time)
            elif self.state == "GAME_OVER":
                self.show_game_over_screen(screen, current_time)

            # Draw cursor on top layer
            self.draw_cursor(screen)
            
            # Backup pos
            self.prev_finger_x, self.prev_finger_y = self.finger_x, self.finger_y

            # Flip buffer & Set Frames
            pygame.display.flip()
            clock.tick(FPS)

        cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = HandGestureFruitNinja()
    game.run()
