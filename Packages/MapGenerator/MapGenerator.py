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
        # Auto-crop transparent padding
        bounds = img.get_bounding_rect(min_alpha=1)
        img_cropped = img.subsurface(bounds).copy()
        draw_rect = pygame.Rect(px + bounds.x, py + bounds.y, bounds.width, bounds.height)
        # collision_scale: shrink hit box to a centred fraction of the drawn area
        scale = prop.get('collision_scale', 1.0)
        cw = int(bounds.width  * scale)
        ch = int(bounds.height * scale)
        col_rect = pygame.Rect(
            draw_rect.x + (bounds.width  - cw) // 2,
            draw_rect.y + (bounds.height - ch) // 2,
            cw, ch
        )
        props.append((img_cropped, draw_rect, col_rect))
    return obstacle_rectangles, render_images, props