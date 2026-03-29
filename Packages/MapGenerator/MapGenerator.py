import pygame
import yaml
import os

__all__ = ['yaml2dict', 'generate_map']

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
        rend = pygame.transform.scale(rend, (width, height))
        render_images.append((rend, token, x, y))
    # Props — textured obstacles with their own collision rect
    props = []
    for prop in map_dict.get('props', []):
        px = int(prop['x'] * width)
        py = int(prop['y'] * height)
        pw = int(prop['w'] * width)
        ph = int(prop['h'] * height)
        img = pygame.image.load(os.path.join(image_dir, prop['name'])).convert_alpha()
        img = pygame.transform.scale(img, (pw, ph))
        # Pre-bake a 2 px bright outline for contrast against dark backgrounds
        outline = pygame.Surface((pw + 4, ph + 4), pygame.SRCALPHA)
        for ox, oy in ((-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)):
            outline.blit(img, (2 + ox, 2 + oy))
        # Tint the offset copies to a warm yellow outline colour
        tint = pygame.Surface((pw + 4, ph + 4), pygame.SRCALPHA)
        tint.fill((220, 180, 60, 180))
        outline.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        outline.blit(img, (2, 2))  # original image on top, unmodified
        rect = pygame.Rect(px, py, pw, ph)
        props.append((outline, rect))
    return obstacle_rectangles, render_images, props