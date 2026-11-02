"""
Generates Kicksa brand assets:
1. Retina Minimalist Logo (kicksa_logo.png)
2. Ultra-Smooth Cinematic Showcase Loop GIF (kicksa_showcase_loop.gif)
   Using actual high-res screenshots uploaded by user:
   - ONYX (Dark Luxury Fragrance & Commerce)
   - VESPERA (Amber Cinematic Dining & Wine Vault)
   - SKYBOUND (High-Altitude Hydration Storefront)
   - L'ECLAT VENDOME (Place Vendome High Jewelry & Bespoke)
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DIST_ASSETS_DIR = os.path.join(BASE_DIR, "dashboard", "dist", "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(DIST_ASSETS_DIR, exist_ok=True)

USER_UPLOADED_DIR = r"C:/Users/shubham dixit/.gemini/antigravity/brain/d5f1b436-85b6-49d7-8afb-de99f04d427d/.user_uploaded"

SCREENSHOTS = [
    {
        "file": os.path.join(USER_UPLOADED_DIR, "media_1793631284467_6754c5c1.png"),
        "title": "ONYX · DIGITAL EXPERIENCE",
        "category": "Brand & Commerce",
        "url": "onyx.studio / experience",
        "tag": "01 / 04",
        "accent": (0, 242, 254)  # Cyan
    },
    {
        "file": os.path.join(USER_UPLOADED_DIR, "media_1793631309398_d750007f.png"),
        "title": "VESPERA · LUXURY DINING & WINE",
        "category": "Hospitality & Vault",
        "url": "vespera.london / table-request",
        "tag": "02 / 04",
        "accent": (245, 175, 40)  # Amber Gold
    },
    {
        "file": os.path.join(USER_UPLOADED_DIR, "media_1793631346464_85c1a3ae.png"),
        "title": "SKYBOUND · PRODUCT STOREFRONT",
        "category": "Hydration & Storytelling",
        "url": "skybound.co / collection",
        "tag": "03 / 04",
        "accent": (96, 165, 250)  # Sky Blue
    },
    {
        "file": os.path.join(USER_UPLOADED_DIR, "media_1793631367698_be9a467b.jpg"),
        "title": "L'ÉCLAT VENDÔME · HIGH JEWELRY",
        "category": "Bespoke Luxury Retail",
        "url": "leclatvendome.paris / bespoke",
        "tag": "04 / 04",
        "accent": (212, 175, 55)  # Place Vendome Gold
    }
]


def get_font(size=12, bold=False):
    font_file = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(font_file, size)
    except Exception:
        try:
            fallback = "arialbd.ttf" if bold else "arial.ttf"
            return ImageFont.truetype(fallback, size)
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


def render_mockup_slide(item, width=524, height=290):
    """
    Renders an individual project slide framed in a premium dark browser viewport mockup.
    """
    canvas = Image.new("RGB", (width, height), (10, 10, 14))
    draw = ImageDraw.Draw(canvas)

    header_h = 30
    footer_h = 32
    view_h = height - header_h - footer_h  # 228

    # Outer rounded container
    draw.rounded_rectangle((2, 2, width - 2, height - 2), radius=10, fill=(16, 16, 22), outline=(38, 38, 50), width=1)

    # --- Header Bar (Browser Top Bar) ---
    draw.rounded_rectangle((2, 2, width - 2, header_h), radius=10, fill=(20, 20, 28))
    # Cover bottom corners of top bar
    draw.rectangle((2, header_h - 10, width - 2, header_h), fill=(20, 20, 28))
    draw.line([(2, header_h), (width - 2, header_h)], fill=(34, 34, 46), width=1)

    # Browser window control dots
    dots = [(14, (255, 95, 86)), (26, (255, 189, 46)), (38, (39, 201, 63))]
    for x_pos, dot_c in dots:
        draw.ellipse((x_pos, 11, x_pos + 7, 18), fill=dot_c)

    # Center URL Pill
    url_font = get_font(size=10, bold=False)
    url_box_w = 200
    url_box_x = (width - url_box_w) // 2
    draw.rounded_rectangle((url_box_x, 6, url_box_x + url_box_w, 24), radius=5, fill=(13, 13, 18), outline=(32, 32, 42), width=1)
    # Subtle lock icon dot
    draw.ellipse((url_box_x + 8, 13, url_box_x + 12, 17), fill=(0, 242, 254))
    draw.text((url_box_x + 20, 9), item["url"], fill=(156, 163, 175), font=url_font)

    # Right Tag Badge
    tag_font = get_font(size=9, bold=True)
    draw.text((width - 62, 10), item["tag"], fill=(156, 163, 175), font=tag_font)

    # --- Viewport Content (Resized High-Res Screenshot) ---
    if os.path.exists(item["file"]):
        src_img = Image.open(item["file"]).convert("RGB")
        # Resize to fill viewport width and height
        screen_img = src_img.resize((width - 4, view_h), Image.Resampling.LANCZOS)
        canvas.paste(screen_img, (2, header_h))

    # --- Footer Bar (Project Info & Indicator) ---
    footer_y = height - footer_h
    draw.line([(2, footer_y), (width - 2, footer_y)], fill=(34, 34, 46), width=1)
    draw.rectangle((2, footer_y + 1, width - 2, height - 2), fill=(14, 14, 20))

    # Project Title & Category
    title_font = get_font(size=11, bold=True)
    cat_font = get_font(size=10, bold=False)
    draw.text((16, footer_y + 8), item["title"], fill=(255, 255, 255), font=title_font)
    draw.text((16 + draw.textlength(item["title"], font=title_font) + 12, footer_y + 9), f"•  {item['category']}", fill=(140, 140, 155), font=cat_font)

    # Live Active Indicator on the right
    curr_idx = SCREENSHOTS.index(item)
    bar_start_x = width - 84
    for i in range(len(SCREENSHOTS)):
        bx = bar_start_x + (i * 18)
        bar_color = item["accent"] if i == curr_idx else (45, 45, 58)
        bar_w = 14 if i == curr_idx else 10
        draw.rounded_rectangle((bx, footer_y + 13, bx + bar_w, footer_y + 17), radius=2, fill=bar_color)

    return canvas


def create_smooth_showcase_loop_gif():
    """
    Generates an ultra-smooth GIF loop transitioning seamlessly
    between the 4 screenshots with silky crossfade blending.
    """
    width, height = 524, 290
    print("Rendering base mockup slides for screenshots...")
    base_slides = [render_mockup_slide(item, width, height) for item in SCREENSHOTS]

    frames = []

    # Number of hold frames (steady view) and transition frames (crossfade)
    HOLD_FRAMES = 16       # 16 * 75ms = ~1.2s hold
    TRANSITION_STEPS = 8   # 8 * 75ms = ~0.6s smooth crossfade

    for i in range(len(base_slides)):
        current_slide = base_slides[i]
        next_slide = base_slides[(i + 1) % len(base_slides)]

        # 1. Steady Hold frames
        for _ in range(HOLD_FRAMES):
            frames.append(current_slide)

        # 2. Smooth Crossfade Transition frames
        for step in range(1, TRANSITION_STEPS + 1):
            alpha = step / (TRANSITION_STEPS + 1)
            # Smooth ease-in-out formula for alpha
            ease_alpha = 0.5 * (1.0 - (1.0 - alpha) ** 2) if alpha < 0.5 else 0.5 * (1.0 + alpha ** 2)
            blended = Image.blend(current_slide, next_slide, ease_alpha)
            frames.append(blended)

    print(f"Total animation frames generated: {len(frames)}. Optimizing palette...")

    # Quantize frames to clean 128-color web palette to keep GIF silky & light
    quantized_frames = []
    # Sample a representative composite for optimal global palette
    palette_sample = Image.new("RGB", (width * 2, height * 2))
    palette_sample.paste(base_slides[0], (0, 0))
    palette_sample.paste(base_slides[1], (width, 0))
    palette_sample.paste(base_slides[2], (0, height))
    palette_sample.paste(base_slides[3], (width, height))
    global_palette = palette_sample.quantize(colors=128, method=Image.Resampling.BILINEAR)

    for fr in frames:
        quantized = fr.quantize(palette=global_palette, dither=Image.Dither.FLOYDSTEINBERG)
        quantized_frames.append(quantized)

    path1 = os.path.join(ASSETS_DIR, "kicksa_showcase_loop.gif")
    path2 = os.path.join(DIST_ASSETS_DIR, "kicksa_showcase_loop.gif")

    quantized_frames[0].save(
        path1,
        save_all=True,
        append_images=quantized_frames[1:],
        duration=75,  # 75ms per frame = ~13 fps, feels very smooth
        loop=0,
        optimize=True
    )
    quantized_frames[0].save(
        path2,
        save_all=True,
        append_images=quantized_frames[1:],
        duration=75,
        loop=0,
        optimize=True
    )

    size_kb = os.path.getsize(path1) / 1024
    print(f"Created smooth showcase loop GIF: {path1} | Size: {size_kb:.1f} KB | Frames: {len(quantized_frames)}")


if __name__ == "__main__":
    create_kicksa_logo()
    create_smooth_showcase_loop_gif()
