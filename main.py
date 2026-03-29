import pygame
import math
import os
from Packages import BaseBaller as BB
from Packages.MapGenerator import yaml2dict, generate_map
pygame.font.init()
pygame.mixer.init()

current_dir = os.getcwd()
map_dict = yaml2dict(os.path.join(current_dir, 'Maps.yaml'))
image_dir = os.path.join(current_dir, 'Assets')

''' ------ GLOBAL VARIABLES ------ '''
WINNER_FONT = pygame.font.SysFont('comicsans', 100)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
FPS = 60
map_name = 'Dark magic den'
obstacles_walls, renders = generate_map(BB.WIDTH, BB.HEIGHT, map_dict[map_name], image_dir)
obstacles_players = obstacles_walls

WIN = pygame.display.set_mode((BB.WIDTH, BB.HEIGHT))
pygame.display.set_caption("The floor is lava")

# Pre-bake static background — only non-lava layers (lava is animated separately)
# Renders are stored bottom→top, so iterate in reverse to blit bottom layer first
_static_bg = pygame.Surface((BB.WIDTH, BB.HEIGHT)).convert()
for (img, token, x, y) in reversed(renders):
    if token != 'lava':  # lava layer is scrolled live
        _static_bg.blit(img.convert_alpha() if img.get_flags() & pygame.SRCALPHA else img.convert(), (x, y))

# Lava rendering settings
LAVA_RADIUS        = 30   # px — blob radius, roughly half the baller width
LAVA_SCROLL_DX     = 0.4  # px per game-frame, horizontal flow speed
LAVA_SCROLL_DY     = 0.2  # px per game-frame, vertical flow speed
TRAIL_RENDER_STEP  = 8    # skip trail points closer than this many pixels

lava_scroll_x = 0.0
lava_scroll_y = 0.0

# Ambient pulse — warm orange glow that breathes over the background lava
_pulse_surface  = pygame.Surface((BB.WIDTH, BB.HEIGHT)).convert()
_pulse_frame    = 0
PULSE_SPEED     = 0.035   # radians per game-frame (~3 s cycle at 60 FPS)
PULSE_MAX_ADD   = 70      # max RGB added at peak (0 = invisible, 255 = blinding)

# Load lava texture — pre-tile 2x2 so any scroll offset crop stays in bounds
_raw_lava  = pygame.image.load(os.path.join(image_dir, 'lava.png')).convert()
lava_tex_w, lava_tex_h = _raw_lava.get_size()
_lava_tiled = pygame.Surface((lava_tex_w * 2, lava_tex_h * 2))
for _ox, _oy in ((0,0),(lava_tex_w,0),(0,lava_tex_h),(lava_tex_w,lava_tex_h)):
    _lava_tiled.blit(_raw_lava, (_ox, _oy))

# Reusable SRCALPHA surface for lava texture masking — no numpy needed
# Strategy: fill transparent, draw white-opaque circles, BLEND_RGBA_MULT with texture
# → texture shows where circles are, fully transparent elsewhere
_lava_draw     = pygame.Surface((BB.WIDTH, BB.HEIGHT), pygame.SRCALPHA).convert_alpha()

movement_rotation = {0: 90, 1: 270, 2: 0, 3: 180}  # kept for reference; actual rotation pre-baked in BaseBaller
shots = []

''' ------ END OF GLOBAL VARIABLES ------ '''

def draw_lava_textured(win, players, scroll_x, scroll_y):
    """Render all lava trails as one seamless animated textured body.
    Uses SRCALPHA surface + BLEND_RGBA_MULT — pure SDL, no numpy, no pixel lock.
    Pipeline:
      1. Fill _lava_draw transparent
      2. Draw white+opaque circles at trail points
      3. BLEND_RGBA_MULT blit of scrolled texture → texture only where circles were
      4. Blit result (transparent areas don't cover background)"""
    tx = int(scroll_x) % lava_tex_w
    ty = int(scroll_y) % lava_tex_h

    # 1. Clear to fully transparent
    _lava_draw.fill((0, 0, 0, 0))

    # 2. Draw opaque white circles at each lava trail point
    step_sq = TRAIL_RENDER_STEP ** 2
    for player in players:
        last = None
        for (x, y) in player.get_movement_lava_history():
            if last is None or (x-last[0])**2 + (y-last[1])**2 >= step_sq:
                pygame.draw.circle(_lava_draw, (255, 255, 255, 255), (x, y), LAVA_RADIUS)
                last = (x, y)

    # 3. Multiply texture onto circles: transparent areas stay (0,0,0,0)
    _lava_draw.blit(_lava_tiled, (0, 0), area=(tx, ty, BB.WIDTH, BB.HEIGHT),
                    special_flags=pygame.BLEND_RGBA_MULT)

    # 4. Composite onto window (transparent areas show background)
    win.blit(_lava_draw, (0, 0))

def draw_window(renders, players, shots):
    global lava_scroll_x, lava_scroll_y, _pulse_frame
    lava_scroll_x    += LAVA_SCROLL_DX
    lava_scroll_y    += LAVA_SCROLL_DY
    _pulse_frame     += 1

    # --- background (basalt) ---
    WIN.blit(_static_bg, (0, 0))

    # --- ambient glow pulse over background lava ---
    # Fill surface each frame with pulsed brightness so BLEND_ADD adds the right amount.
    # BLEND_ADD ignores set_alpha(), so we modulate the fill color instead.
    t = 0.5 + 0.5 * math.sin(_pulse_frame * PULSE_SPEED)   # 0.0 → 1.0
    glow = int(PULSE_MAX_ADD * t)
    _pulse_surface.fill((glow, glow // 3, 0))              # warm orange-red
    WIN.blit(_pulse_surface, (0, 0), special_flags=pygame.BLEND_ADD)

    # --- lava trails ---
    draw_lava_textured(WIN, players, lava_scroll_x, lava_scroll_y)

    # --- players ---
    for player in players:
        rect = player.get_rect()
        health_green, health_red = player.get_health_bar()
        movement_direction = player.get_movement_direction()
        action = player.get_action()
        images = player.get_images()
        WIN.blit(images[action][movement_direction], (rect.x, rect.y))
        pygame.draw.rect(WIN, GREEN, health_green)
        pygame.draw.rect(WIN, RED, health_red)

    # --- shots ---
    for idx, (id, rect) in enumerate(shots):
        if rect != None:
            pygame.draw.rect(WIN, (255, 0, 0), rect)

    pygame.display.update()

def main():
    baseballers_dict = yaml2dict('Baseballers.yaml')

    players = []
    for key, item in baseballers_dict.items():
        players.append(BB.BaseBaller(**item))

    [player.post_init() for player in players]
    #[player.generate_rect() for player in players]
    #[player.generate_images() for player in players]
    get_player_obstacles(players)

    clock = pygame.time.Clock()
    run = True
    while run:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
            if event.type == pygame.KEYDOWN:
                pass
                for player in players:
                    if event.key == player.get_shoot_key() and not player.get_shoot_block(): # check if shoot key was pressed and if the player is already not in the middle of a swing with its baseball bat
                        player.start_shooting()

        keys_pressed = pygame.key.get_pressed()

        process_frame(players, keys_pressed)

        draw_window(renders, players, shots)

        looser_text = ''
        for player in players:
            if player.get_health() <= 0:
                #name = player.get_name()
                color = player.get_color()
                looser_text = color + ' player lost!'

        if looser_text != '': 
            draw_looser(looser_text)
            break

def draw_looser(text):
    draw_text = WINNER_FONT.render(text, 1, BLACK)
    WIN.blit(draw_text, (BB.WIDTH/2 - draw_text.get_width() /
                         2, BB.HEIGHT/2 - draw_text.get_height()/2))
    pygame.display.update()
    pygame.time.delay(5000)

def process_frame(players, keys_pressed):
    global shots, obstacles_walls, obstacles_players

    obstacles = obstacles_walls + obstacles_players
    [player.movement_handle(keys_pressed, obstacles) for player in players]
    get_player_obstacles(players)

    obstacles = obstacles_walls + obstacles_players
    shots = [player.update_shooting(players) for player in players]
    [player.update_slide(obstacles_walls + obstacles_players) for player in players]
    get_player_obstacles(players)

    lava = [player.get_movement_lava_history() for player in players]
    [player.check_for_lava(lava) for player in players]

def get_player_obstacles(players):
    global obstacles_players

    obstacles_players = [player.get_rect() for player in players]

if __name__ == "__main__":
    while 1:
        main()
