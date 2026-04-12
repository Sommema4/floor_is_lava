import pygame
import math
from .BaseWeapon import BaseWeapon

# ---- Tunable constants ------------------------------------------------
MAGNET_MAX_RANGE  = 350    # px  — cone reach
MAGNET_HALF_ANGLE = 50     # deg — half-angle either side of facing direction
MAGNET_MAX_PULL   = 3.5    # px/frame at point-blank distance
MAGNET_NUM_LINES  = 7      # animated arc lines drawn in the cone
MAGNET_CONE_COLOR = (180, 80, 255)   # purple

# Facing-direction → unit vector (screen coords: y grows downward)
_DIR = {
    0: (-1,  0),   # LEFT
    1: ( 1,  0),   # RIGHT
    2: ( 0, -1),   # UP
    3: ( 0,  1),   # DOWN
}
# -----------------------------------------------------------------------


class Magnet(BaseWeapon):
    """Hold-to-activate weapon that pulls opponents into the cone toward the caster.

    - Allows the caster to move freely while active.
    - Pull strength scales linearly with proximity: full force at 0, zero at max range.
    - The target can resist by running away; the net effect is a movement slowdown rather than
      a hard lock.
    """

    def __init__(self):
        self._active = False

    # ------------------------------------------------------------------
    def on_press(self, owner):
        self._active      = True
        owner.shoot_block = True
        # Deliberately NOT setting owner.movement_block so the caster can move

    def update(self, owner, keys_pressed, players):
        if not self._active:
            return (None, None)
        self._apply_pull(owner, players)
        return (None, None)

    def on_release(self, owner):
        self._active      = False
        owner.shoot_block = False

    # ------------------------------------------------------------------
    def draw(self, win, owner):
        if not self._active:
            return

        cx = owner.x + owner.width  // 2
        cy = owner.y + owner.height // 2
        fdx, fdy = _DIR[owner.movement_direction]

        # base_angle: angle of facing direction in standard math degrees
        # (negate fdy because pygame y-axis points down)
        base_angle = math.degrees(math.atan2(-fdy, fdx))

        # One shared SRCALPHA surface — draw all lines then blit once
        surf = pygame.Surface((win.get_width(), win.get_height()), pygame.SRCALPHA)

        # Animated scan: lines scroll across the cone every 600 ms
        t = (pygame.time.get_ticks() % 600) / 600.0

        for i in range(MAGNET_NUM_LINES):
            frac      = (i + t) % MAGNET_NUM_LINES / MAGNET_NUM_LINES   # 0.0 → 1.0
            angle_rad = math.radians(
                base_angle - MAGNET_HALF_ANGLE + frac * MAGNET_HALF_ANGLE * 2
            )
            end_x = cx + int(MAGNET_MAX_RANGE * math.cos(angle_rad))
            end_y = cy - int(MAGNET_MAX_RANGE * math.sin(angle_rad))

            # Brightest at the centre of the cone, fades to the edges
            centre_dist = abs(frac - 0.5) * 2   # 0 = centre, 1 = edges
            alpha = int(220 * (1.0 - centre_dist))
            pygame.draw.line(surf, (*MAGNET_CONE_COLOR, alpha), (cx, cy), (end_x, end_y), 2)

        win.blit(surf, (0, 0))

    # ------------------------------------------------------------------
    def _apply_pull(self, owner, players):
        cx = owner.x + owner.width  // 2
        cy = owner.y + owner.height // 2
        fdx, fdy   = _DIR[owner.movement_direction]
        cos_limit  = math.cos(math.radians(MAGNET_HALF_ANGLE))

        for other in players:
            if other is owner:
                continue

            ox    = other.x + other.width  // 2
            oy    = other.y + other.height // 2
            to_dx = ox - cx
            to_dy = oy - cy
            dist  = math.sqrt(to_dx * to_dx + to_dy * to_dy)

            if dist == 0 or dist > MAGNET_MAX_RANGE:
                continue

            # Cone check: dot product of normalised "to-other" with facing direction
            dot = (to_dx / dist) * fdx + (to_dy / dist) * fdy
            if dot < cos_limit:
                continue

            # Pull force scales linearly: full at 0 px, zero at max range
            force  = MAGNET_MAX_PULL * (1.0 - dist / MAGNET_MAX_RANGE)

            # Vector pointing FROM other TOWARD owner (i.e. the pull direction)
            other.x = int(other.x - (to_dx / dist) * force)
            other.y = int(other.y - (to_dy / dist) * force)
            other.rect.x, other.rect.y = other.x, other.y
