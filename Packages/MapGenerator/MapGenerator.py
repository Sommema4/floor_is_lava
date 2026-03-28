import pygame
import yaml
import os

def yaml2dict(file):
    print(file)
    with open(file, 'r') as f:
        try:
            d = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)
    return d

def generate_map(width, height, map_dict, image_dir):
    obstacles = map_dict['obstacles']
    renders = map_dict['renders']
    obstacle_rectangles = []
    for obstacle in obstacles:
        (x, y, w, h) = obstacle
        x = int(x * width)
        y = int(y * height)
        w = int(w * width)
        h = int(h * height)
        rect = pygame.Rect(x, y, w, h)
        obstacle_rectangles.append(rect)
    render_images = [] 
    for render in renders:
        (name, token, x, y) = render
        rend = pygame.image.load(os.path.join(image_dir, name))
        render_images.append((rend, token, x, y))
    return obstacle_rectangles, render_images