import pygame
import math
import os
import random
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
WIN = pygame.display.set_mode((BB.WIDTH, BB.HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("The floor is lava")

map_name = 'Dark magic den'
obstacles_walls, renders, props = generate_map(BB.WIDTH, BB.HEIGHT, map_dict[map_name], image_dir)
obstacles_walls = obstacles_walls + [col_rect for (_, _draw, col_rect) in props]  # props are solid obstacles
obstacles_players = obstacles_walls

# Pre-bake static background — only non-lava layers (lava is animated separately)
# Renders are stored bottom→top, so iterate in reverse to blit bottom layer first
_static_bg = pygame.Surface((BB.WIDTH, BB.HEIGHT)).convert()
for (img, token, x, y) in reversed(renders):
    if token != 'lava':  # lava layer is scrolled live
        _static_bg.blit(img.convert_alpha() if img.get_flags() & pygame.SRCALPHA else img.convert(), (x, y))

# Lava rendering settings
LAVA_RADIUS        = 30   # px — blob radius, roughly half the baller width
lava_scroll_dx     = 0.4  # px per game-frame, horizontal flow speed (mutable)
lava_scroll_dy     = 0.2  # px per game-frame, vertical flow speed (mutable)
TRAIL_RENDER_STEP  = 8    # skip trail points closer than this many pixels

lava_scroll_x = 0.0
lava_scroll_y = 0.0

# Ambient pulse — warm orange glow that breathes over the background lava
_pulse_surface  = pygame.Surface((BB.WIDTH, BB.HEIGHT)).convert()
_pulse_frame    = 0
PULSE_SPEED     = 0.035   # radians per game-frame (~3 s cycle at 60 FPS)
PULSE_MAX_ADD   = 70      # max RGB added at peak (0 = invisible, 255 = blinding)

# Load lava texture — pre-tile enough to cover full screen + one extra tile for scroll offset
_raw_lava  = pygame.image.load(os.path.join(image_dir, 'lava.png')).convert()
lava_tex_w, lava_tex_h = _raw_lava.get_size()
_tile_cols = math.ceil(BB.WIDTH  / lava_tex_w) + 1
_tile_rows = math.ceil(BB.HEIGHT / lava_tex_h) + 1
_lava_tiled = pygame.Surface((_tile_cols * lava_tex_w, _tile_rows * lava_tex_h))
for _row in range(_tile_rows):
    for _col in range(_tile_cols):
        _lava_tiled.blit(_raw_lava, (_col * lava_tex_w, _row * lava_tex_h))

# Reusable SRCALPHA surface for lava texture masking — no numpy needed
# Strategy: fill transparent, draw white-opaque circles, BLEND_RGBA_MULT with texture
# → texture shows where circles are, fully transparent elsewhere
_lava_draw     = pygame.Surface((BB.WIDTH, BB.HEIGHT), pygame.SRCALPHA).convert_alpha()

movement_rotation = {0: 90, 1: 270, 2: 0, 3: 180}  # kept for reference; actual rotation pre-baked in BaseBaller
shots = []

# Shrinking zone — lava creeps in from all four edges
zone_shrink_speed = 0.04   # pixels per frame (~2.4 px/s at 60 FPS) — mutable
ZONE_LAVA_DAMAGE  = 0.25   # health lost per frame while standing in border lava
zone_inset        = 0.0    # current border width in pixels (grows every frame)

# --- Health pickup ---
PICKUP_HEAL            = 30          # HP restored on collection (capped at 100)
PICKUP_SIZE            = 45          # px — slightly smaller than the baller (60 px)
PICKUP_ANNOUNCE_FRAMES = 120          # frames of ripple indicator before spawning (~2 s)
PICKUP_ACTIVE_FRAMES   = 600         # frames before auto-despawn if uncollected (~10 s)
PICKUP_INTERVAL_MIN    = 3 * FPS    # min frames between spawns
PICKUP_INTERVAL_MAX    = 10 * FPS    # max frames between spawns
PICKUP_RING_MAX_R      = 55          # max radius of announcement ripple rings
PICKUP_GLOW_SPEED      = 0.20        # sin speed for active glow pulse

pickup_state          = None         # None | 'announcing' | 'active'
pickup_pos            = (0, 0)       # (cx, cy) centre of the pickup
pickup_announce_frame = 0
pickup_active_frame   = 0
pickup_next_in        = random.randint(PICKUP_INTERVAL_MIN, PICKUP_INTERVAL_MAX)

_heart_img = pygame.transform.scale(
    pygame.image.load(os.path.join(image_dir, 'heart.png')).convert_alpha(),
    (PICKUP_SIZE, PICKUP_SIZE)
)

# --- Speed pickups ---
SPEED_UP_AMOUNT              = 2     # added to movement_velocity on collect
SPEED_DOWN_AMOUNT            = 2     # subtracted from movement_velocity on collect
SPEED_PICKUP_INTERVAL_MIN    = 5  * FPS   # min frames between speed-pickup spawns
SPEED_PICKUP_INTERVAL_MAX    = 15 * FPS   # max frames between speed-pickup spawns
SPEED_UP_SCROLL_DELTA        = 0.15  # scroll speed added on speed-up collect
SPEED_UP_ZONE_DELTA          = 0.015 # zone shrink speed added on speed-up collect
SPEED_SCROLL_MIN             = 0.1   # minimum lava scroll dx/dy
SPEED_SCROLL_MAX             = 1.5   # maximum lava scroll dx/dy
SPEED_ZONE_MIN               = 0.01  # minimum zone shrink speed
SPEED_ZONE_MAX               = 0.15  # maximum zone shrink speed

speed_up_state          = None
speed_up_pos            = (0, 0)
speed_up_announce_frame = 0
speed_up_active_frame   = 0
speed_up_next_in        = random.randint(SPEED_PICKUP_INTERVAL_MIN, SPEED_PICKUP_INTERVAL_MAX)

speed_down_state          = None
speed_down_pos            = (0, 0)
speed_down_announce_frame = 0
speed_down_active_frame   = 0
speed_down_next_in        = random.randint(SPEED_PICKUP_INTERVAL_MIN, SPEED_PICKUP_INTERVAL_MAX)

_speed_up_img = pygame.transform.scale(
    pygame.image.load(os.path.join(image_dir, 'speed_up.png')).convert_alpha(),
    (PICKUP_SIZE, PICKUP_SIZE)
)
_speed_down_img = pygame.transform.scale(
    pygame.image.load(os.path.join(image_dir, 'speed_down.png')).convert_alpha(),
    (PICKUP_SIZE, PICKUP_SIZE)
)

# --- Teleport pickup ---
TELEPORT_PICKUP_INTERVAL_MIN = 8  * FPS
TELEPORT_PICKUP_INTERVAL_MAX = 20 * FPS

teleport_state          = None
teleport_pos            = (0, 0)
teleport_announce_frame = 0
teleport_active_frame   = 0
teleport_next_in        = random.randint(TELEPORT_PICKUP_INTERVAL_MIN, TELEPORT_PICKUP_INTERVAL_MAX)

_teleport_img = pygame.transform.scale(
    pygame.image.load(os.path.join(image_dir, 'teleport.png')).convert_alpha(),
    (PICKUP_SIZE, PICKUP_SIZE)
)

# --- Shield pickup ---
SHIELD_DURATION            = 5 * FPS   # frames of lava immunity (5 seconds)
SHIELD_PICKUP_INTERVAL_MIN = 8  * FPS
SHIELD_PICKUP_INTERVAL_MAX = 20 * FPS

shield_state          = None
shield_pos            = (0, 0)
shield_announce_frame = 0
shield_active_frame   = 0
shield_next_in        = random.randint(SHIELD_PICKUP_INTERVAL_MIN, SHIELD_PICKUP_INTERVAL_MAX)

_shield_img = pygame.transform.scale(
    pygame.image.load(os.path.join(image_dir, 'shield.png')).convert_alpha(),
    (PICKUP_SIZE, PICKUP_SIZE)
)

# --- Magnet weapon pickup ---
MAGNET_DURATION            = 10 * FPS  # frames the magnet weapon lasts (10 seconds)
MAGNET_PICKUP_INTERVAL_MIN = 10 * FPS
MAGNET_PICKUP_INTERVAL_MAX = 25 * FPS

magnet_pick_state          = None
magnet_pick_pos            = (0, 0)
magnet_pick_announce_frame = 0
magnet_pick_active_frame   = 0
magnet_pick_next_in        = random.randint(MAGNET_PICKUP_INTERVAL_MIN, MAGNET_PICKUP_INTERVAL_MAX)

_magnet_pick_img = pygame.transform.scale(
    pygame.image.load(os.path.join(image_dir, 'magnet.jpg')).convert(),
    (PICKUP_SIZE, PICKUP_SIZE)
)

''' ------ END OF GLOBAL VARIABLES ------ '''

def _random_safe_pos():
    """Return a random (cx, cy) well inside the current safe zone."""
    margin = int(zone_inset) + PICKUP_SIZE + 10
    cx = random.randint(margin, BB.WIDTH  - margin)
    cy = random.randint(margin, BB.HEIGHT - margin)
    return (cx, cy)

def draw_pickup(win):
    """Draw the ripple announcement or the glowing heart, depending on pickup_state."""
    if pickup_state is None:
        return
    cx, cy = pickup_pos

    if pickup_state == 'announcing':
        # 3 staggered expanding ripple rings
        phase = pickup_announce_frame / PICKUP_ANNOUNCE_FRAMES
        for i in range(3):
            t = (phase + i / 3.0) % 1.0
            r = int(PICKUP_RING_MAX_R * t)
            if r < 2:
                continue
            alpha = int(230 * (1.0 - t))
            ring_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255, 80, 80, alpha), (r + 2, r + 2), r, 3)
            win.blit(ring_surf, (cx - r - 2, cy - r - 2))
        # Pulsing centre dot
        dot_r = int(6 + 3 * math.sin(pickup_announce_frame * 0.25))
        pygame.draw.circle(win, (255, 120, 120), (cx, cy), dot_r)

    elif pickup_state == 'active':
        # Additive glow circle behind the heart
        glow_r = PICKUP_SIZE
        glow_t = 0.5 + 0.5 * math.sin(pickup_active_frame * PICKUP_GLOW_SPEED)
        glow_a = int(60 + 100 * glow_t)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (255, 60, 60, glow_a), (glow_r, glow_r), glow_r)
        win.blit(glow_surf, (cx - glow_r, cy - glow_r), special_flags=pygame.BLEND_ADD)
        # Heart image centred on (cx, cy)
        win.blit(_heart_img, (cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2))

def _draw_generic_pickup(win, state, pos, announce_frame, active_frame, img, ring_color, glow_color):
    """Shared draw helper for any timed pickup (ripple announcement + glowing icon)."""
    if state is None:
        return
    cx, cy = pos

    if state == 'announcing':
        phase = announce_frame / PICKUP_ANNOUNCE_FRAMES
        for i in range(3):
            t = (phase + i / 3.0) % 1.0
            r = int(PICKUP_RING_MAX_R * t)
            if r < 2:
                continue
            alpha = int(230 * (1.0 - t))
            ring_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*ring_color, alpha), (r + 2, r + 2), r, 3)
            win.blit(ring_surf, (cx - r - 2, cy - r - 2))
        dot_r = int(6 + 3 * math.sin(announce_frame * 0.25))
        pygame.draw.circle(win, ring_color, (cx, cy), dot_r)

    elif state == 'active':
        glow_r = PICKUP_SIZE
        glow_t = 0.5 + 0.5 * math.sin(active_frame * PICKUP_GLOW_SPEED)
        glow_a = int(60 + 100 * glow_t)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*glow_color, glow_a), (glow_r, glow_r), glow_r)
        win.blit(glow_surf, (cx - glow_r, cy - glow_r), special_flags=pygame.BLEND_ADD)
        win.blit(img, (cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2))


def draw_magnet_pickup(win):
    """Draw the magnet weapon pickup ripple or icon."""
    _draw_generic_pickup(win, magnet_pick_state, magnet_pick_pos,
                         magnet_pick_announce_frame, magnet_pick_active_frame,
                         _magnet_pick_img,
                         ring_color=(255, 220, 40),
                         glow_color=(220, 180, 20))


def draw_teleport_pickup(win):
    """Draw the teleport pickup ripple or icon."""
    _draw_generic_pickup(win, teleport_state, teleport_pos,
                         teleport_announce_frame, teleport_active_frame,
                         _teleport_img,
                         ring_color=(160, 80, 255),
                         glow_color=(120, 40, 220))


def draw_shield_pickup(win):
    """Draw the shield pickup ripple or icon."""
    _draw_generic_pickup(win, shield_state, shield_pos,
                         shield_announce_frame, shield_active_frame,
                         _shield_img,
                         ring_color=(80, 200, 255),
                         glow_color=(40, 160, 220))


def draw_speed_up_pickup(win):
    """Draw the speed-up pickup ripple or icon."""
    _draw_generic_pickup(win, speed_up_state, speed_up_pos,
                         speed_up_announce_frame, speed_up_active_frame,
                         _speed_up_img,
                         ring_color=(80, 220, 80),
                         glow_color=(40, 200, 40))


def draw_speed_down_pickup(win):
    """Draw the speed-down pickup ripple or icon."""
    _draw_generic_pickup(win, speed_down_state, speed_down_pos,
                         speed_down_announce_frame, speed_down_active_frame,
                         _speed_down_img,
                         ring_color=(255, 160, 40),
                         glow_color=(220, 100, 20))


def process_pickup(players):
    """Advance pickup state machine; heal player on collision."""
    global pickup_state, pickup_pos, pickup_announce_frame, pickup_active_frame, pickup_next_in

    if pickup_state is None:
        pickup_next_in -= 1
        if pickup_next_in <= 0:
            pickup_pos            = _random_safe_pos()
            pickup_state          = 'announcing'
            pickup_announce_frame = 0

    elif pickup_state == 'announcing':
        pickup_announce_frame += 1
        if pickup_announce_frame >= PICKUP_ANNOUNCE_FRAMES:
            pickup_state        = 'active'
            pickup_active_frame = 0

    elif pickup_state == 'active':
        pickup_active_frame += 1
        cx, cy = pickup_pos
        pickup_rect = pygame.Rect(cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2,
                                  PICKUP_SIZE, PICKUP_SIZE)
        for player in players:
            if player.get_rect().colliderect(pickup_rect):
                heal = min(PICKUP_HEAL, 100 - player.get_health())
                if heal > 0:
                    player.loose_health(-heal)   # loose_health(-n) → health += n
                pickup_state   = None
                pickup_next_in = random.randint(PICKUP_INTERVAL_MIN, PICKUP_INTERVAL_MAX)
                return
        if pickup_active_frame >= PICKUP_ACTIVE_FRAMES:
            pickup_state   = None
            pickup_next_in = random.randint(PICKUP_INTERVAL_MIN, PICKUP_INTERVAL_MAX)

def process_magnet_pickup(players):
    """Advance magnet pickup state machine; grant magnet weapon on collision."""
    global magnet_pick_state, magnet_pick_pos, magnet_pick_announce_frame
    global magnet_pick_active_frame, magnet_pick_next_in

    if magnet_pick_state is None:
        magnet_pick_next_in -= 1
        if magnet_pick_next_in <= 0:
            magnet_pick_pos            = _random_safe_pos()
            magnet_pick_state          = 'announcing'
            magnet_pick_announce_frame = 0

    elif magnet_pick_state == 'announcing':
        magnet_pick_announce_frame += 1
        if magnet_pick_announce_frame >= PICKUP_ANNOUNCE_FRAMES:
            magnet_pick_state        = 'active'
            magnet_pick_active_frame = 0

    elif magnet_pick_state == 'active':
        magnet_pick_active_frame += 1
        cx, cy = magnet_pick_pos
        pickup_rect = pygame.Rect(cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2,
                                  PICKUP_SIZE, PICKUP_SIZE)
        for player in players:
            if player.get_rect().colliderect(pickup_rect):
                player.activate_magnet(MAGNET_DURATION)
                magnet_pick_state   = None
                magnet_pick_next_in = random.randint(MAGNET_PICKUP_INTERVAL_MIN, MAGNET_PICKUP_INTERVAL_MAX)
                return
        if magnet_pick_active_frame >= PICKUP_ACTIVE_FRAMES:
            magnet_pick_state   = None
            magnet_pick_next_in = random.randint(MAGNET_PICKUP_INTERVAL_MIN, MAGNET_PICKUP_INTERVAL_MAX)


def process_teleport_pickup(players):
    """Advance teleport pickup state machine; swap all players' positions on collision."""
    global teleport_state, teleport_pos, teleport_announce_frame, teleport_active_frame, teleport_next_in

    if teleport_state is None:
        teleport_next_in -= 1
        if teleport_next_in <= 0:
            teleport_pos            = _random_safe_pos()
            teleport_state          = 'announcing'
            teleport_announce_frame = 0

    elif teleport_state == 'announcing':
        teleport_announce_frame += 1
        if teleport_announce_frame >= PICKUP_ANNOUNCE_FRAMES:
            teleport_state        = 'active'
            teleport_active_frame = 0

    elif teleport_state == 'active':
        teleport_active_frame += 1
        cx, cy = teleport_pos
        pickup_rect = pygame.Rect(cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2,
                                  PICKUP_SIZE, PICKUP_SIZE)
        for player in players:
            if player.get_rect().colliderect(pickup_rect):
                # Swap positions of all players in round-robin order
                if len(players) >= 2:
                    positions = [(p.x, p.y) for p in players]
                    for i, p in enumerate(players):
                        p.teleport_to(*positions[(i + 1) % len(players)])
                teleport_state   = None
                teleport_next_in = random.randint(TELEPORT_PICKUP_INTERVAL_MIN, TELEPORT_PICKUP_INTERVAL_MAX)
                return
        if teleport_active_frame >= PICKUP_ACTIVE_FRAMES:
            teleport_state   = None
            teleport_next_in = random.randint(TELEPORT_PICKUP_INTERVAL_MIN, TELEPORT_PICKUP_INTERVAL_MAX)


def process_shield_pickup(players):
    """Advance shield pickup state machine; grant lava immunity on collision."""
    global shield_state, shield_pos, shield_announce_frame, shield_active_frame, shield_next_in

    if shield_state is None:
        shield_next_in -= 1
        if shield_next_in <= 0:
            shield_pos            = _random_safe_pos()
            shield_state          = 'announcing'
            shield_announce_frame = 0

    elif shield_state == 'announcing':
        shield_announce_frame += 1
        if shield_announce_frame >= PICKUP_ANNOUNCE_FRAMES:
            shield_state        = 'active'
            shield_active_frame = 0

    elif shield_state == 'active':
        shield_active_frame += 1
        cx, cy = shield_pos
        pickup_rect = pygame.Rect(cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2,
                                  PICKUP_SIZE, PICKUP_SIZE)
        for player in players:
            if player.get_rect().colliderect(pickup_rect):
                player.activate_shield(SHIELD_DURATION)
                shield_state   = None
                shield_next_in = random.randint(SHIELD_PICKUP_INTERVAL_MIN, SHIELD_PICKUP_INTERVAL_MAX)
                return
        if shield_active_frame >= PICKUP_ACTIVE_FRAMES:
            shield_state   = None
            shield_next_in = random.randint(SHIELD_PICKUP_INTERVAL_MIN, SHIELD_PICKUP_INTERVAL_MAX)


def process_speed_up_pickup(players):
    """Advance speed-up pickup state machine; boost player and lava speed on collision."""
    global speed_up_state, speed_up_pos, speed_up_announce_frame, speed_up_active_frame, speed_up_next_in
    global lava_scroll_dx, lava_scroll_dy, zone_shrink_speed

    if speed_up_state is None:
        speed_up_next_in -= 1
        if speed_up_next_in <= 0:
            speed_up_pos            = _random_safe_pos()
            speed_up_state          = 'announcing'
            speed_up_announce_frame = 0

    elif speed_up_state == 'announcing':
        speed_up_announce_frame += 1
        if speed_up_announce_frame >= PICKUP_ANNOUNCE_FRAMES:
            speed_up_state        = 'active'
            speed_up_active_frame = 0

    elif speed_up_state == 'active':
        speed_up_active_frame += 1
        cx, cy = speed_up_pos
        pickup_rect = pygame.Rect(cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2,
                                  PICKUP_SIZE, PICKUP_SIZE)
        for player in players:
            if player.get_rect().colliderect(pickup_rect):
                player.adjust_speed(SPEED_UP_AMOUNT)
                lava_scroll_dx = min(SPEED_SCROLL_MAX, lava_scroll_dx + SPEED_UP_SCROLL_DELTA)
                lava_scroll_dy = min(SPEED_SCROLL_MAX, lava_scroll_dy + SPEED_UP_SCROLL_DELTA)
                zone_shrink_speed = min(SPEED_ZONE_MAX, zone_shrink_speed + SPEED_UP_ZONE_DELTA)
                speed_up_state   = None
                speed_up_next_in = random.randint(SPEED_PICKUP_INTERVAL_MIN, SPEED_PICKUP_INTERVAL_MAX)
                return
        if speed_up_active_frame >= PICKUP_ACTIVE_FRAMES:
            speed_up_state   = None
            speed_up_next_in = random.randint(SPEED_PICKUP_INTERVAL_MIN, SPEED_PICKUP_INTERVAL_MAX)


def process_speed_down_pickup(players):
    """Advance speed-down pickup state machine; reduce player and lava speed on collision."""
    global speed_down_state, speed_down_pos, speed_down_announce_frame, speed_down_active_frame, speed_down_next_in
    global lava_scroll_dx, lava_scroll_dy, zone_shrink_speed

    if speed_down_state is None:
        speed_down_next_in -= 1
        if speed_down_next_in <= 0:
            speed_down_pos            = _random_safe_pos()
            speed_down_state          = 'announcing'
            speed_down_announce_frame = 0

    elif speed_down_state == 'announcing':
        speed_down_announce_frame += 1
        if speed_down_announce_frame >= PICKUP_ANNOUNCE_FRAMES:
            speed_down_state        = 'active'
            speed_down_active_frame = 0

    elif speed_down_state == 'active':
        speed_down_active_frame += 1
        cx, cy = speed_down_pos
        pickup_rect = pygame.Rect(cx - PICKUP_SIZE // 2, cy - PICKUP_SIZE // 2,
                                  PICKUP_SIZE, PICKUP_SIZE)
        for player in players:
            if player.get_rect().colliderect(pickup_rect):
                player.adjust_speed(-SPEED_DOWN_AMOUNT)
                lava_scroll_dx = max(SPEED_SCROLL_MIN, lava_scroll_dx - SPEED_UP_SCROLL_DELTA)
                lava_scroll_dy = max(SPEED_SCROLL_MIN, lava_scroll_dy - SPEED_UP_SCROLL_DELTA)
                zone_shrink_speed = max(SPEED_ZONE_MIN, zone_shrink_speed - SPEED_UP_ZONE_DELTA)
                speed_down_state   = None
                speed_down_next_in = random.randint(SPEED_PICKUP_INTERVAL_MIN, SPEED_PICKUP_INTERVAL_MAX)
                return
        if speed_down_active_frame >= PICKUP_ACTIVE_FRAMES:
            speed_down_state   = None
            speed_down_next_in = random.randint(SPEED_PICKUP_INTERVAL_MIN, SPEED_PICKUP_INTERVAL_MAX)


def _zone_border_rects(inset):
    """Return the 4 lava border strips for a given inset (in whole pixels)."""
    i = max(0, inset)
    return [
        pygame.Rect(0,              0,              BB.WIDTH,     i),            # top
        pygame.Rect(0,              BB.HEIGHT - i,  BB.WIDTH,     i),            # bottom
        pygame.Rect(0,              i,              i,            BB.HEIGHT - 2*i),  # left
        pygame.Rect(BB.WIDTH - i,   i,              i,            BB.HEIGHT - 2*i),  # right
    ]

def draw_zone_lava(win, inset):
    """Draw creeping lava border strips using the shared scrolling lava texture."""
    i = int(inset)
    if i <= 0:
        return
    tx = int(lava_scroll_x) % lava_tex_w
    ty = int(lava_scroll_y) % lava_tex_h
    for strip in _zone_border_rects(i):
        if strip.width > 0 and strip.height > 0:
            win.set_clip(strip)
            # Tile _raw_lava to cover the full screen — works for any texture/screen size
            y = -ty
            while y < BB.HEIGHT:
                x = -tx
                while x < BB.WIDTH:
                    win.blit(_raw_lava, (x, y))
                    x += lava_tex_w
                y += lava_tex_h
            win.set_clip(None)

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
    global lava_scroll_x, lava_scroll_y, lava_scroll_dx, lava_scroll_dy, _pulse_frame
    lava_scroll_x    += lava_scroll_dx
    lava_scroll_y    += lava_scroll_dy
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

    # --- shrinking zone lava border ---
    draw_zone_lava(WIN, zone_inset)

    # --- props (stumps etc.) above background, below players ---
    for (img, draw_rect, _col) in props:
        WIN.blit(img, (draw_rect.x, draw_rect.y))

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
        # Weapon overlay (magnet cone, etc.)
        player.active_weapon.draw(WIN, player)
        # Shield bubble — pulsing cyan ring around shielded players
        if player.is_shielded():
            pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() * 0.008)
            shield_r = rect.width // 2 + 10
            cx_s = rect.x + rect.width  // 2
            cy_s = rect.y + rect.height // 2
            shield_surf = pygame.Surface((shield_r * 2 + 4, shield_r * 2 + 4), pygame.SRCALPHA)
            alpha = int(80 + 120 * pulse)
            pygame.draw.circle(shield_surf, (80, 200, 255, alpha), (shield_r + 2, shield_r + 2), shield_r, 4)
            WIN.blit(shield_surf, (cx_s - shield_r - 2, cy_s - shield_r - 2))
        pygame.draw.rect(WIN, GREEN, health_green)
        pygame.draw.rect(WIN, RED, health_red)

    # --- shots ---
    for idx, (id, rect) in enumerate(shots):
        if rect != None:
            pygame.draw.rect(WIN, (255, 0, 0), rect)

    # --- health pickup ---
    draw_pickup(WIN)

    # --- speed pickups ---
    draw_speed_up_pickup(WIN)
    draw_speed_down_pickup(WIN)

    # --- teleport & shield pickups ---
    draw_teleport_pickup(WIN)
    draw_shield_pickup(WIN)

    # --- magnet weapon pickup ---
    draw_magnet_pickup(WIN)

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
                    if event.key == player.get_shoot_key() and not player.get_shoot_block():
                        player.start_shooting()
            if event.type == pygame.KEYUP:
                for player in players:
                    if event.key == player.get_shoot_key():
                        player.release_shooting()

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
    global shots, obstacles_walls, obstacles_players, zone_inset, zone_shrink_speed

    zone_inset += zone_shrink_speed

    obstacles = obstacles_walls + obstacles_players
    [player.movement_handle(keys_pressed, obstacles) for player in players]
    get_player_obstacles(players)

    obstacles = obstacles_walls + obstacles_players
    shots = [player.update_shooting(keys_pressed, players) for player in players]
    [player.update_slide(obstacles_walls + obstacles_players) for player in players]
    get_player_obstacles(players)

    lava = [player.get_movement_lava_history() for player in players]

    # Lava damage — trail and border are mutually exclusive per frame (no double damage)
    # check_for_lava returns 0 when it dealt damage, None when it didn't
    border_rects = _zone_border_rects(int(zone_inset))
    for player in players:
        player.tick_shield()
        player.tick_weapon()
        if not player.is_shielded():
            trail_hit = player.check_for_lava(lava)
            if trail_hit is None and player.get_rect().collidelist(border_rects) != -1:
                player.loose_health(ZONE_LAVA_DAMAGE)

    # Health pickup logic
    process_pickup(players)

    # Speed pickup logic
    process_speed_up_pickup(players)
    process_speed_down_pickup(players)

    # Teleport & shield pickup logic
    process_teleport_pickup(players)
    process_shield_pickup(players)

    # Magnet weapon pickup logic
    process_magnet_pickup(players)

def get_player_obstacles(players):
    global obstacles_players

    obstacles_players = [player.get_rect() for player in players]

if __name__ == "__main__":
    while 1:
        main()
