import pygame
import os
from dataclasses import dataclass
from collections import deque

__all__ = ['BaseBaller', 'WIDTH', 'HEIGHT', 'colors']

pygame.display.init()
_info = pygame.display.Info()
WIDTH  = _info.current_w
HEIGHT = _info.current_h

current_dir = os.getcwd()

from Packages.Weapons import make_weapon
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
    shield_frames: int = 0
    magnet_frames: int = 0
    active_weapon: object = None   # set to a BaseWeapon instance in post_init

    ''' ----------POST INITIALIZATION METHODS---------- '''

    def post_init(self):
        self.generate_rect()
        self.generate_images()
        self.fill_movement_lava_history()
        self.active_weapon = make_weapon(self.weapon)

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

    def is_shielded(self):
        return self.shield_frames > 0

    def activate_shield(self, frames):
        """Grant lava immunity for the given number of frames (stacks by taking the max)."""
        self.shield_frames = max(self.shield_frames, frames)

    def tick_shield(self):
        """Call once per frame to count down the shield."""
        if self.shield_frames > 0:
            self.shield_frames -= 1

    def has_magnet(self):
        return self.magnet_frames > 0

    def activate_magnet(self, frames):
        """Switch to the magnet weapon for the given number of frames."""
        from Packages.Weapons import Magnet
        self.magnet_frames = max(self.magnet_frames, frames)
        # Only swap if not already holding the magnet
        if not isinstance(self.active_weapon, Magnet):
            # Cleanly release whatever is currently active
            self.active_weapon.on_release(self)
            self.shoot_block = False
            self.active_weapon = Magnet()

    def tick_weapon(self):
        """Count down the magnet timer; revert to default weapon when it expires."""
        if self.magnet_frames > 0:
            self.magnet_frames -= 1
            if self.magnet_frames == 0:
                # Release magnet cleanly then restore the player's base weapon
                self.active_weapon.on_release(self)
                self.shoot_block = False
                self.active_weapon = make_weapon(self.weapon)

    def teleport_to(self, x, y):
        """Instantly move the player to (x, y) and sync the collision rect."""
        self.x, self.y = x, y
        self.rect.x, self.rect.y = x, y

    def adjust_speed(self, delta):
        """Permanently adjust movement_velocity by delta, clamped to [1, 10]."""
        self.movement_velocity = max(1, min(10, self.movement_velocity + delta))

    def start_shooting(self):
        """Called on KEYDOWN — delegate to the active weapon's on_press hook."""
        self.active_weapon.on_press(self)

    def release_shooting(self):
        """Called on KEYUP — delegate to the active weapon's on_release hook."""
        self.active_weapon.on_release(self)

    def update_shooting(self, keys_pressed, players):
        """Called every frame — delegate to the active weapon's update hook."""
        if not self.shoot_block:
            return (None, None)
        return self.active_weapon.update(self, keys_pressed, players)
    
    def check_for_lava(self, lavas):
        if self.is_shielded():
            return
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
                            self.loose_health(0.25)
                            return 0
                prev = pt

