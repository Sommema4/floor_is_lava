import pygame
import os
import numpy as np
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
surface = pygame.Surface((BB.WIDTH, BB.HEIGHT), pygame.SRCALPHA)
pygame.display.set_caption("The floor is lava")

movement_rotation = {0: 90, 1: 270, 2: 0, 3: 180}
shots = []
''' ------ END OF GLOBAL VARIABLES ------ '''

def draw_window(renders, players, shots):
    print('draw')
    render = renders[1]
    (image, token, x, y) = render
    WIN.blit(image, (x, y))

    render = renders[0]
    (image, token, x, y) = render
    WIN.blit(image, (x, y))

    l, e = [], []
    for player in players:
        rect = player.get_rect()
        health_green, health_red = player.get_health_bar()
        movement_direction = player.get_movement_direction()
        action = player.get_action()
        images = player.get_images()
        WIN.blit(pygame.transform.rotate(images[action], movement_rotation[movement_direction]), (rect.x, rect.y))
        pygame.draw.rect(WIN, GREEN, health_green)
        pygame.draw.rect(WIN, RED, health_red)

        lava = player.get_movement_lava_history()
        erosion = player.get_movement_erosion_history()
        l.extend(lava)
        e.extend(erosion)

        if len(erosion) >= 2:
            tt = pygame.draw.lines(WIN, (0, 0, 0), False, erosion, width=5)
            WIN.blit(surface, tt)
            print(tt)
        if len(lava) >= 2:
            pygame.draw.lines(WIN, (255, 0, 0), False, lava, width=5)
        #WIN.blit(surface, (0,0))
            

    for idx, (id, rect) in enumerate(shots):
        if rect != None:
            pygame.draw.rect(WIN, (255, 0, 0), rect)

    # Set the pixels at the specified coordinates to be transparent
    # mask = pygame.mask.Mask(size=(BB.WIDTH, BB.HEIGHT))
    # for coord in e:
    #     mask.set_at((coord[1], coord[0]), value=1)

    # mask_kernel = pygame.mask.Mask(size=(20, 20), fill=True)
    # mask = mask.convolve(mask_kernel)
    # mask.to_surface(surface)

    #mask_surface = pygame.surfarray.blit_array(surface, mask_array)

    #surface.blit(mask, (0, 0))
   

    # for render in renders[1:]:
    #     (image, token, x, y) = render
    #     if token == 'lava':
    #         #surface.set_alpha(128)
    #         surface.blit(image, (x, y))
    #     for render in renders:
    #         for (x, y) in erosion:
    #             print(x, y)
    #             surface.blit(image, (x, y))

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
