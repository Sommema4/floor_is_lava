import pygame
from .BaseWeapon import BaseWeapon

# All tunable bat parameters live here — no longer scattered across BaseBaller
BAT_PARAMS = {
    'height':    60,
    'width':     60,
    'velocity':  10,
    'max_frames': 6,
    'damage':    10,
    'slide':     20,
}


class BaseballBat(BaseWeapon):
    """Classic melee swing.  Blocks movement for the duration of the swing."""

    def on_press(self, owner):
        owner.movement_block = True
        owner.shoot_block    = True

    def update(self, owner, keys_pressed, players):
        if not owner.shoot_block:
            return (None, None)
        return self._swing(owner, players)

    def on_release(self, owner):
        # The swing completes by itself via max_frames — key release is ignored
        pass

    # ------------------------------------------------------------------
    def _swing(self, owner, players):
        bat = BAT_PARAMS
        if owner.hit_progress == bat['max_frames']:
            owner.reset_shoot_block()
            owner.reset_movement_block()
            owner.reset_hit_progress()

        d = owner.movement_direction
        if d == 0:   # LEFT
            bat_x      = owner.x - owner.hit_progress * bat['velocity']
            bat_y      = owner.y
            bat_width  = owner.hit_progress * bat['velocity']
            bat_height = bat['width']
        elif d == 1:  # RIGHT
            bat_x      = owner.x + owner.width
            bat_y      = owner.y
            bat_width  = owner.hit_progress * bat['velocity']
            bat_height = bat['height']
        elif d == 2:  # UP
            bat_x      = owner.x
            bat_y      = owner.y - owner.hit_progress * bat['velocity']
            bat_width  = bat['width']
            bat_height = owner.hit_progress * bat['velocity']
        else:         # DOWN
            bat_x      = owner.x
            bat_y      = owner.y + owner.height
            bat_width  = bat['width']
            bat_height = owner.hit_progress * bat['velocity']

        owner.hit_progress += 1
        bat_rect = pygame.Rect(bat_x, bat_y, bat_width, bat_height)

        for player in players:
            if player.get_rect().colliderect(bat_rect):
                owner.score += 1
                owner.reset_shoot_block()
                owner.reset_movement_block()
                owner.reset_hit_progress()
                player.loose_health(bat['damage'])
                player.start_slide(owner.movement_direction, bat['slide'], bat['velocity'])

        return (owner.get_id(), bat_rect)
