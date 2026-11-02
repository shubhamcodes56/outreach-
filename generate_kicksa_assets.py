"""
Generates Kicksa brand assets:
1. Minimal modern logo for header.
2. High-impact animated loop showcase GIF displaying recent client work & ROI metrics.
"""

import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
DIST_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "dashboard", "dist", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(DIST_ASSETS_DIR, exist_ok=True)


def draw_rounded_rect(draw, bbox, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)


def create_kicksa_logo():
    """Creates an ultra-minimal modern dark geometric logo for Kicksa."""
    size = (160, 48)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Minimal emblem: rounded square with sleek neon cyan accent
    draw_rounded_rect(draw, (4, 6, 38, 40), radius=8, fill=(18, 18, 22), outline=(39, 39, 42), width=1)
    
    # Stylized minimal 'K' symbol
    # Left vertical stem
    draw.rectangle((14, 14, 17, 32), fill=(255, 255, 255))
    # Upper right angle
    draw.line([(18, 23), (28, 14)], fill=(0, 242, 254), width=3)
    # Lower right angle
    draw.line([(18, 23), (28, 32)], fill=(255, 255, 255), width=3)

    # Save PNG
    path1 = os.path.join(ASSETS_DIR, "kicksa_logo.png")
    path2 = os.path.join(DIST_ASSETS_DIR, "kicksa_logo.png")
    img.save(path1, "PNG")
    img.save(path2, "PNG")
    print(f"Created logo: {path1}")


def create_showcase_loop_gif():
    """
    Creates an ultra-sleek, dark-mode animated GIF showcasing 3 real-world client upgrades
    and their direct business profit/revenue impact in a continuous smooth loop.
    """
    w, h = 540, 200
    frames = []

    slides_data = [
        {
            "tag": "CASE STUDY 01 • INDEPENDENT DINING & CAFE",
            "tag_color": (0, 242, 254),
            "title": "Mobile-First Ordering & Table Reservation",
            "sub": "Converted clunky PDF menu into instant 1-tap mobile experience.",
            "stat_val": "+42% Local Bookings",
            "stat_sub": "Zero commission lost to third-party aggregators",
            "accent": (0, 242, 254)
        },
        {
            "tag": "CASE STUDY 02 • PRIVATE CLINICS & DENTAL",
            "tag_color": (52, 211, 153),
            "title": "24/7 After-Hours Patient Consultation Portal",
            "sub": "Integrated live scheduling calendar & verified patient review proof.",
            "stat_val": "Zero Missed Patients",
            "stat_sub": "Automated WhatsApp & Email booking confirmations",
            "accent": (52, 211, 153)
        },
        {
            "tag": "CASE STUDY 03 • CONTRACTORS & TRADES",
            "tag_color": (251, 191, 36),
            "title": "Google Local SEO & Emergency Quote Funnel",
            "sub": "Engineered LocalBusiness Schema for immediate Google Maps discovery.",
            "stat_val": "2.8x Quote Inquiries",
            "stat_sub": "Sticky tap-to-call mobile buttons for instant jobs",
            "accent": (251, 191, 36)
        }
    ]

    for s_idx, data in enumerate(slides_data):
        # Create base slide
        base = Image.new("RGB", (w, h), (14, 14, 18))
        draw = ImageDraw.Draw(base)

        # Card outer border
        draw_rounded_rect(draw, (1, 1, w - 2, h - 2), radius=12, fill=(18, 18, 23), outline=(39, 39, 45), width=1)

        # Top tag pill
        tag_w = len(data["tag"]) * 6 + 18
        draw_rounded_rect(draw, (20, 16, 20 + tag_w, 34), radius=4, fill=(24, 24, 32), outline=data["accent"], width=1)
        draw.text((28, 19), data["tag"], fill=data["accent"])

        # Main Title
        draw.text((20, 48), data["title"], fill=(255, 255, 255))
        draw.text((20, 72), data["sub"], fill=(161, 161, 170))

        # Divider line
        draw.line([(20, 102), (w - 20, 102)], fill=(34, 34, 42), width=1)

        # Bottom Metric Box
        draw_rounded_rect(draw, (20, 114, w - 20, 180), radius=8, fill=(13, 13, 17), outline=(28, 28, 35), width=1)
        
        # Metric accent badge
        draw.rectangle((20, 114, 25, 180), fill=data["accent"])
        draw.text((38, 126), "PROFIT IMPACT:", fill=(113, 113, 122))
        draw.text((140, 124), data["stat_val"], fill=(255, 255, 255))
        draw.text((38, 150), data["stat_sub"], fill=data["accent"])

        # Slide indicator dots in corner
        for dot_i in range(3):
            dot_color = data["accent"] if dot_i == s_idx else (45, 45, 55)
            draw.ellipse((w - 55 + dot_i * 12, 22, w - 47 + dot_i * 12, 30), fill=dot_color)

        # Hold frame for 2.2 seconds (each frame is ~2200ms)
        frames.append((base, 2200))

    # Save as animated loop GIF
    path1 = os.path.join(ASSETS_DIR, "kicksa_showcase_loop.gif")
    path2 = os.path.join(DIST_ASSETS_DIR, "kicksa_showcase_loop.gif")

    imgs = [f[0] for f in frames]
    durations = [f[1] for f in frames]

    imgs[0].save(
        path1,
        save_all=True,
        append_images=imgs[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    imgs[0].save(
        path2,
        save_all=True,
        append_images=imgs[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    print(f"Created showcase loop GIF: {path1}")


if __name__ == "__main__":
    create_kicksa_logo()
    create_showcase_loop_gif()
