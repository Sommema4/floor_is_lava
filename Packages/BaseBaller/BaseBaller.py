import pygame
import os
from dataclasses import dataclass
import tkinter as tk
from collections import deque

__all__ = ['BaseBaller', 'WIDTH', 'HEIGHT', 'colors', 'weapons']

root = tk.Tk()
WIDTH = root.winfo_screenwidth()
HEIGHT = root.winfo_screenheight() - 50
root.destroy()

current_dir = os.getcwd()

weapons = {'baseball_bat': {'height':60, 'width': 60, 'velocity': 10, 'max_frames': 6, 'damage': 10, 'slide': 20},
           }

colors = {'RED': (255, 0, 0), 'BLUE': (0, 0, 255)}

@dataclass
class BaseBaller():
    id: int
    name: str
    color: str
    x: int
    y: int
    inventory: dict
    effect: str
    action:str
    images: dict
    sound_effect: dict
    keys: dict # [pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_LCTRL]
    movement_history_lenght: int = 240
    lava_delay: int = 60
    score: int = 0
    width: int = 60
    height: int = 60
    health: int = 100
    weapon: str = 'baseball_bat'
    hit_progress: int = 0
    movement_velocity: int = 5
    movement_direction: int = 0
    movement_block: bool = False
    movement_erosion_history: any = None
    movement_lava_history: any = None
    shoot_block: bool = False
    slide_bool: bool = False
    slide_progress: int = 0
    slide_direction: int = 0
    slide_distance: int = 0
    slide_velocity: int = 0

    ''' ----------POST INITIALIZATION METHODS---------- '''

    def post_init(self):
        self.generate_rect()
        self.generate_images()
        self.fill_movement_lava_history()

    def fill_movement_lava_history(self):
        # maxlen ensures both deques self-manage their size with no manual .pop() needed
        self.movement_lava_history = deque([], maxlen=self.movement_history_lenght - self.lava_delay)
        self.movement_erosion_history = deque([], maxlen=self.lava_delay)

    def generate_rect(self):
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        return self.get_rect()

    def generate_images(self):
        keys = list(self.images.keys())
        scaled_images = []
        for key, item in self.images.items():
            image = pygame.image.load(os.path.join(current_dir, 'Assets', item))
            scaled = pygame.transform.scale(image, (self.width, self.height))
            # Pre-rotate for all 4 movement directions so draw_window can blit directly
            # direction: 0=LEFT(90°), 1=RIGHT(270°), 2=UP(0°), 3=DOWN(180°)
            rotated = {
                0: pygame.transform.rotate(scaled, 90),
                1: pygame.transform.rotate(scaled, 270),
                2: pygame.transform.rotate(scaled, 0),
                3: pygame.transform.rotate(scaled, 180),
            }
            scaled_images.append(rotated)
        res = {keys[i]: scaled_images[i] for i in range(len(keys))}
        self.images = res

    ''' ----------GETTERS---------- '''

    def get_action(self):
        return self.action
    
    def get_images(self):
        return self.images

    def get_rect(self): # What a great method name :-)
        return self.rect
    
    def get_movement_direction(self):
        return self.movement_direction
    
    def get_shoot_block(self):
        return self.shoot_block
    
    def get_movement_lava_history(self):
        return self.movement_lava_history
    
    def get_movement_erosion_history(self):
        return self.movement_erosion_history
    
    def get_movement_history_lenght(self):
        return self.movement_history_lenght
    
    def get_id(self):
        return self.id
    
    def get_health(self):
        return self.health
    
    def get_name(self):
        return self.name
    
    def get_color(self):
        return self.color

    def get_shoot_key(self):
        return self.keys['SHOOT']
    
    def get_health_bar(self):
        health = self.get_health()
        green_pixel = int((self.height * (health / 100.0)) + 0.5)
        red_pixel = self.height - green_pixel
        rect_green = pygame.Rect(self.x + 50, self.y, 10, green_pixel)
        rect_red = pygame.Rect(self.x + 50, self.y + green_pixel, 10, red_pixel)
        return rect_green, rect_red
    
    ''' ----------OTHERS---------- '''

    def movement_handle(self, keys_pressed, obstacles):
        ''' MOVE WITH THE CHARACTER AND CHECK FOR OBSTACLES '''
        other_obstacles = obstacles.copy()
        other_obstacles.remove(self.rect)
        if not self.movement_block:
            if keys_pressed[self.keys['LEFT']] and self.x - self.movement_velocity > 0:  # LEFT
                self.x -= self.movement_velocity
                self.movement_direction = 0
            elif keys_pressed[self.keys['RIGHT']] and self.x + self.movement_velocity + self.width < WIDTH:  # RIGHT
                self.x += self.movement_velocity
                self.movement_direction = 1
            elif keys_pressed[self.keys['UP']] and self.y - self.movement_velocity > 0:  # UP
                self.y -= self.movement_velocity
                self.movement_direction = 2
            elif keys_pressed[self.keys['DOWN']] and self.y + self.movement_velocity + self.height < HEIGHT - 15:  # DOWN
                self.y += self.movement_velocity
                self.movement_direction = 3

            self.rect.x, self.rect.y = self.x, self.y # update the rectangle
            self.check_for_collision(other_obstacles, self.movement_direction)

        # Trail always advances at constant speed, regardless of movement_block
        self._record_trail_point(self.x + self.width // 2, self.y + self.height // 2)

        return self.rect

    def _record_trail_point(self, cx, cy):
        """Record current position every frame.
        When the erosion buffer (maxlen=lava_delay) is full, the oldest point
        is about to be auto-dropped — graduate it to lava first.
        This ensures lava advances at a constant one-point-per-frame rate
        regardless of whether the player is moving or standing still."""
        if len(self.movement_erosion_history) >= self.lava_delay:
            self.movement_lava_history.appendleft(self.movement_erosion_history[-1])
        self.movement_erosion_history.appendleft((cx, cy))

    def slide_handle(self, obstacles):
        other_obstacles = obstacles.copy()
        other_obstacles.remove(self.rect)

        if self.slide_progress == self.slide_distance:
            self.slide_progress = 0
            self.slide_bool = False
        
        if self.slide_direction == 0:  # LEFT
            self.x -= self.slide_velocity
        elif self.slide_direction == 1:  # RIGHT
            self.x += self.slide_velocity
        elif self.slide_direction == 2:  # UP
            self.y -= self.slide_velocity
        elif self.slide_direction == 3:  # DOWN
            self.y += self.slide_velocity

        self.slide_progress += 1
        self.rect.x, self.rect.y = self.x, self.y # update the rectangle

        self.check_for_collision(other_obstacles, self.slide_direction)

    def check_for_collision(self, obstacles, direction):
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if direction == 0:
                    self.x = obstacle.x + obstacle.width
                if direction == 1:
                    self.x = obstacle.x - self.width
                if direction == 2:
                    self.y = obstacle.y + obstacle.height
                if direction == 3:
                    self.y = obstacle.y - self.height
        self.rect.x, self.rect.y = self.x, self.y

    def start_slide(self, slide_direction, slide_dist, slide_velocity):
        self.slide_bool = True
        self.slide_direction = slide_direction
        self.slide_distance = slide_dist
        self.slide_velocity = slide_velocity

    def update_slide(self, obstacles):
        if self.slide_bool:
            self.slide_handle(obstacles)

    def reset_slide_progress(self):
        self.slide_progress = 0

    def reset_movement_block(self):
        self.movement_block = False

    def reset_shoot_block(self):
        self.shoot_block = False

    def reset_hit_progress(self):
        self.hit_progress = 0

    def loose_health(self, x):
        self.health -= x

    def start_shooting(self):
        self.movement_block = True
        self.shoot_block = True
        
    def update_shooting(self, players):
        if not self.shoot_block:
            return (None, None)
        if self.weapon == 'baseball_bat':
            return self.baseball_bat_movement(players)
    
    def check_for_lava(self, lavas):
        rx1 = self.rect.x
        ry1 = self.rect.y
        rx2 = rx1 + self.rect.width
        ry2 = ry1 + self.rect.height
        for lava in lavas:
            pts = lava  # deque, iterate directly
            prev = None
            for pt in pts:
                if prev is not None:
                    # Bounding-box rejection: skip segment if it can't possibly touch player rect
                    sx1 = min(prev[0], pt[0])
                    sy1 = min(prev[1], pt[1])
                    sx2 = max(prev[0], pt[0])
                    sy2 = max(prev[1], pt[1])
                    if sx2 >= rx1 and sx1 <= rx2 and sy2 >= ry1 and sy1 <= ry2:
                        if self.rect.clipline(prev, pt):
                            self.loose_health(1)
                            return 0
                prev = pt
    
    def baseball_bat_movement(self, players):
        bat = weapons[self.weapon]
        if self.hit_progress == bat['max_frames']:
            self.reset_shoot_block()
            self.reset_movement_block()
            self.reset_hit_progress()
        if self.movement_direction == 0: # LEFT
            bat_x = self.x - self.hit_progress * bat['velocity']
            bat_y = self.y
            bat_width = self.hit_progress * bat['velocity']
            bat_height = bat['width']
        if self.movement_direction == 1: # RIGHT
            bat_x = self.x + self.width
            bat_y = self.y 
            bat_width = + self.hit_progress * bat['velocity']
            bat_height = bat['height']
        if self.movement_direction == 2: # UP
            bat_x = self.x
            bat_y = self.y - self.hit_progress * bat['velocity']
            bat_width = bat['width']
            bat_height = self.hit_progress * bat['velocity']
        if self.movement_direction == 3: # DOWN
            bat_x = self.x
            bat_y = self.y + self.height
            bat_width = bat['width']
            bat_height = + self.hit_progress * bat['velocity']
        
        self.hit_progress += 1
        bat_rect = pygame.Rect(bat_x, bat_y, bat_width, bat_height)
        
        for player in players:
            if player.get_rect().colliderect(bat_rect):
                self.score += 1
                self.reset_shoot_block()
                self.reset_movement_block()
                self.reset_hit_progress()
                player.loose_health(bat['damage'])
                player.start_slide(self.movement_direction, bat['slide'], bat['velocity'])

        return (self.get_id(), bat_rect)

