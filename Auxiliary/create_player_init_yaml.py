import yaml
import pygame
import os

data = {
    '1':{
        'id': 1,
        'name': 'Bob the baseballer',
        'color': 'RED',
        'x': 100,
        'y': 100,
        'width': 64,
        'height': 64,
        'health': 100,
        'inventory': {},
        'weapon': 'baseball_bat',
        'effect': '',
        'movement_velocity': 5,
        'movement_direction': 0,
        'movement_block': False,
        'hit_progress': 0,
        'images': {'movement': os.path.join('.Assetes', 'guy_red.png')},
        'sound_effect': {},
        'keys': {'LEFT': pygame.K_a, 'RIGHT': pygame.K_d, 'UP': pygame.K_w, 'DOWN': pygame.K_s, 'SHOOT': pygame.K_LCTRL}
    },
    '2':{
        'id': 1,
        'name': 'Bill the baseballer',
        'color': 'BLUE',
        'x': 600,
        'y': 100,
        'width': 64,
        'height': 64,
        'health': 100,
        'inventory': {},
        'weapon': 'baseball_bat',
        'effect': '',
        'movement_velocity': 5,
        'movement_direction': 0,
        'movement_block': False,
        'hit_progress': 0,
        'images': {'movement': os.path.join('.Assetes', 'guy_blue.png')},
        'sound_effect': {},
        'keys': {'LEFT': pygame.K_LEFT, 'RIGHT': pygame.K_RIGHT, 'UP': pygame.K_UP, 'DOWN': pygame.K_DOWN, 'SHOOT': pygame.K_RCTRL}
    },

}

# Convert dictionary to YAML
with open('Baseballers.yaml', 'w') as outfile:
    yaml.dump(data, outfile, default_flow_style=False)