"""
Generates Kicksa brand assets:
1. Actual Minimalist Retina Logo (kicksa_logo.png)
2. Real Selected Work Showcase Loop GIF (kicksa_showcase_loop.gif)
   Featuring real projects: ONYX, PDR WORLD, KAKTUS, SALVAS.
   Matches the aesthetic of portfolio selected work (no fake claims).
"""

import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
DIST_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "dashboard", "dist", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(DIST_ASSETS_DIR, exist_ok=True)


def get_font(name="segoeui.ttf", size=14, bold=False):
    try:
        font_file = "segoeuib.ttf" if bold else "segoeui.ttf"
        return ImageFont.truetype(font_file, size)
    except Exception:
        try:
            font_file = "arialbd.ttf" if bold else "arial.ttf"
            return ImageFont.truetype(font_file, size)
        except Exception:
            return ImageFont.load_default()


def create_kicksa_logo():
    """Creates a high-resolution retina logo for Kicksa Studio."""
    w, h = 360, 72
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Minimal emblem box (rounded square)
    draw.rounded_rectangle((4, 8, 56, 60), radius=12, fill=(16, 16, 22), outline=(42, 42, 54), width=2)

    # Stylized minimal 'K' symbol
    # Vertical bar
    draw.rectangle((20, 20, 25, 48), fill=(255, 255, 255))
    # Upper cyan diagonal
    draw.line([(26, 34), (41, 20)], fill=(0, 242, 254), width=4)
    # Lower white diagonal
    draw.line([(26, 34), (41, 48)], fill=(255, 255, 255), width=4)

    # Typography: KICKSA STUDIO
    font_bold = get_font(size=24, bold=True)
    font_sub = get_font(size=14, bold=True)

    draw.text((70, 20), "KICKSA", fill=(255, 255, 255), font=font_bold)
    draw.text((176, 26), "STUDIO", fill=(113, 113, 122), font=font_sub)

    path1 = os.path.join(ASSETS_DIR, "kicksa_logo.png")
    path2 = os.path.join(DIST_ASSETS_DIR, "kicksa_logo.png")
    img.save(path1, "PNG")
    img.save(path2, "PNG")
    print(f"Created logo: {path1}")


def create_showcase_loop_gif():
    """
    Creates an ultra-clean, portfolio-authentic animated GIF showcasing
    real engineering & design projects: ONYX, PDR WORLD, KAKTUS, SALVAS.
    """
    w, h = 540, 215

    # 4 Real Portfolio Projects
    projects = [
        {
            "num": "01",
            "name": "ONYX · DIGITAL EXPERIENCE",
            "category": "BRAND / COMMERCE",
            "headline": "High-contrast product storytelling & dark commerce architecture.",
            "tags": ["BRAND EXPERIENCE", "COMMERCE", "DESIGN"],
            "color": (0, 242, 254)  # Cyan
        },
        {
            "num": "02",
            "name": "PDR WORLD · PLATFORM",
            "category": "WORKFLOW / CLOUD",
            "headline": "Enterprise workflow ecosystem, repair telemetry & dispatch platform.",
            "tags": ["ENTERPRISE", "REACT/NODE", "SYSTEMS"],
            "color": (255, 180, 0)  # Amber
        },
        {
            "num": "03",
            "name": "KAKTUS · SAAS INTERFACE",
            "category": "DEVELOPER TOOLING",
            "headline": "Next-gen cloud IDE interface, telemetry & automated agent pipelines.",
            "tags": ["SAAS", "INTERFACE", "REALTIME"],
            "color": (16, 185, 129)  # Emerald
        },
        {
            "num": "04",
            "name": "SALVAS · RESCUE ECOSYSTEM",
            "category": "CRITICAL SYSTEMS",
            "headline": "Emergency response telemetry, hospital ping & offline fail-safe architecture.",
            "tags": ["IOT/EDGE", "CRITICAL INFRA", "MOBILE"],
            "color": (239, 68, 68)  # Crimson/Coral
        }
    ]

    font_label = get_font(size=10, bold=True)
    font_title = get_font(size=14, bold=True)
    font_desc = get_font(size=12, bold=False)
    font_tag = get_font(size=9, bold=True)
    font_ticker = get_font(size=10, bold=True)

    frames = []

    for idx, proj in enumerate(projects):
        img = Image.new("RGB", (w, h), (9, 9, 12))
        draw = ImageDraw.Draw(img)

        # Main Card background with subtle outline
        draw.rounded_rectangle((10, 10, w - 10, h - 10), radius=10, fill=(17, 17, 23), outline=(36, 36, 48), width=1)

        # Header bar of card (matches user portfolio screenshot)
        draw.text((26, 22), "06 SELECTED PROJECTS", fill=(161, 161, 170), font=font_label)
        draw.text((345, 22), "BRAND / PRODUCT / INTERFACE", fill=(113, 113, 122), font=font_label)
        draw.line([(26, 38), (w - 26, 38)], fill=(28, 28, 38), width=1)

        # Project number badge & slide dots
        draw.rectangle((26, 50, 142, 68), fill=(24, 24, 34), outline=(42, 42, 56), width=1)
        draw.text((32, 53), f"FEATURED / {proj['num']}", fill=proj["color"], font=font_tag)

        # Dot indicators
        dot_start_x = w - 80
        for d in range(len(projects)):
            dot_color = proj["color"] if d == idx else (50, 50, 65)
            draw.ellipse((dot_start_x + (d * 14), 56, dot_start_x + (d * 14) + 6, 62), fill=dot_color)

        # Project Title
        draw.text((26, 80), proj["name"], fill=(255, 255, 255), font=font_title)

        # Project Description
        draw.text((26, 105), proj["headline"], fill=(180, 180, 195), font=font_desc)

        # Project Tags
        tag_x = 26
        for tag in proj["tags"]:
            tag_w = draw.textlength(tag, font=font_tag) + 14
            draw.rounded_rectangle((tag_x, 134, tag_x + tag_w, 150), radius=4, fill=(24, 24, 34), outline=(42, 42, 56), width=1)
            draw.text((tag_x + 7, 136), tag, fill=(161, 161, 170), font=font_tag)
            tag_x += int(tag_w + 8)

        # Ticker line at the bottom (like user portfolio screenshot)
        draw.rectangle((10, h - 38, w - 10, h - 10), fill=(12, 12, 16))
        draw.line([(10, h - 38), (w - 10, h - 38)], fill=(28, 28, 38), width=1)
        ticker_text = "✦  DIGITAL EXPERIENCES   ✦   PRODUCT STORYTELLING   ✦   COMMERCE   ✦   SYSTEM ARCHITECTURE  ✦"
        draw.text((26, h - 28), ticker_text, fill=(113, 113, 122), font=font_ticker)

        # 20 frames per project at 100ms = 2.0s per project
        for _ in range(20):
            frames.append(img)

    path1 = os.path.join(ASSETS_DIR, "kicksa_showcase_loop.gif")
    path2 = os.path.join(DIST_ASSETS_DIR, "kicksa_showcase_loop.gif")
    frames[0].save(
        path1,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=True
    )
    frames[0].save(
        path2,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        optimize=True
    )
    print(f"Created showcase GIF: {path1} ({len(frames)} frames)")


if __name__ == "__main__":
    create_kicksa_logo()
    create_showcase_loop_gif()
