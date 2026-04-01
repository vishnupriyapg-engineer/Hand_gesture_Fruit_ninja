import os
from PIL import Image, ImageDraw

def create_image(filename, drawing_func, size=(120, 120)):
    # Create image with transparent background (RGBA)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    drawing_func(d, size)
    img.save(filename)
    print(f"Generated {filename}")

def draw_apple(draw, size):
    w, h = size
    # Apple body (red circle)
    draw.ellipse([w*0.1, h*0.2, w*0.9, h*0.9], fill=(220, 20, 60, 255))
    # Leaf (green ellipse)
    draw.ellipse([w*0.4, h*0.0, w*0.6, h*0.3], fill=(34, 139, 34, 255))
    # Stem
    draw.line([w*0.5, h*0.1, w*0.5, h*0.3], fill=(139, 69, 19, 255), width=4)
    # Highlight
    draw.ellipse([w*0.2, h*0.3, w*0.4, h*0.5], fill=(255, 100, 120, 180))

def draw_banana(draw, size):
    w, h = size
    points = [
        (w*0.15, h*0.85),
        (w*0.35, h*0.95),
        (w*0.65, h*0.90),
        (w*0.85, h*0.65),
        (w*0.95, h*0.35),
        (w*0.85, h*0.45),
        (w*0.60, h*0.70),
        (w*0.30, h*0.75),
        (w*0.15, h*0.85)
    ]
    draw.polygon(points, fill=(255, 230, 0, 255))
    # Draw some detail lines
    draw.line([points[1], points[6], points[5]], fill=(200, 180, 0, 255), width=2)
    # Ends
    draw.ellipse([w*0.1, h*0.8, w*0.2, h*0.9], fill=(139, 69, 19, 255))
    draw.ellipse([w*0.9, h*0.3, w*0.98, h*0.4], fill=(139, 69, 19, 255))

def draw_watermelon(draw, size):
    w, h = size
    # Outer green rim
    draw.pieslice([w*0.05, h*0.05, w*0.95, h*0.95], start=0, end=180, fill=(34, 139, 34, 255))
    # Inner white-ish rim
    draw.pieslice([w*0.10, h*0.10, w*0.90, h*0.90], start=0, end=180, fill=(200, 255, 200, 255))
    # Inner red flesh
    draw.pieslice([w*0.15, h*0.15, w*0.85, h*0.85], start=0, end=180, fill=(255, 50, 50, 255))
    # Seeds
    seeds = [(w*0.3, h*0.6), (w*0.5, h*0.7), (w*0.7, h*0.6), (w*0.4, h*0.8), (w*0.6, h*0.8)]
    for sx, sy in seeds:
        draw.ellipse([sx, sy, sx+w*0.06, sy+h*0.08], fill=(0,0,0,255))

def draw_bomb(draw, size):
    w, h = size
    # Black body
    draw.ellipse([w*0.2, h*0.3, w*0.8, h*0.9], fill=(30, 30, 30, 255))
    # Highlight
    draw.ellipse([w*0.3, h*0.4, w*0.45, h*0.55], fill=(80, 80, 80, 200))
    # Fuse base
    draw.rectangle([w*0.42, h*0.2, w*0.58, h*0.32], fill=(100, 100, 100, 255))
    # Spark line
    draw.line([w*0.5, h*0.2, w*0.6, h*0.05], fill=(255, 165, 0, 255), width=4)
    # Spark fire
    draw.ellipse([w*0.55, h*0.0, w*0.65, h*0.1], fill=(255, 50, 0, 255))
    draw.ellipse([w*0.58, h*0.03, w*0.62, h*0.07], fill=(255, 255, 0, 255))

if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    create_image(os.path.join(assets_dir, 'apple.png'), draw_apple)
    create_image(os.path.join(assets_dir, 'banana.png'), draw_banana)
    create_image(os.path.join(assets_dir, 'watermelon.png'), draw_watermelon)
    create_image(os.path.join(assets_dir, 'bomb.png'), draw_bomb)
