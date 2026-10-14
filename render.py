"""Işılda / Glowtrack TikTok slideshow renderer.

Usage: python3 render.py content/<id>.json [assets_dir] [out_dir]

A slideshow JSON has: id, style ("photo" | "clean"), caption, slides[].
Slide types:
  hook  -> big serif headline (+ optional "sub")
  point -> optional "num", "title", "body"
  list  -> "title", "items"[]
  cta   -> closing "text" (+ optional "sub")
  app   -> "title" + a real App Store screenshot of the app ("screenshot": index)
Wrap words in *stars* to highlight them.
Photo style: any slide may carry "photo" (a stock photo search query); fetch_assets.py
resolves it to assets_dir/<id>/<slide_no>.jpg before rendering.
"""
import json, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H = 1080, 1920
# TikTok UI safe zone: top bar, right action column, bottom caption area
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 96, 900, 260, 1380

ROOT = os.path.dirname(os.path.abspath(__file__))
BRAND = json.load(open(os.path.join(ROOT, "brand.json")))
C = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in BRAND["colors"].items()}
_font_cache = {}


def font(kind, size, weight):
    key = (kind, size, weight)
    if key in _font_cache:
        return _font_cache[key]
    f = ImageFont.truetype(os.path.join(ROOT, "fonts", BRAND["fonts"][kind]), size)
    axes = []
    for a in f.get_variation_axes():
        n = a["name"].decode().lower()
        if "weight" in n:
            axes.append(weight)
        elif "optical" in n:
            axes.append(min(a["maximum"], max(a["minimum"], size // 2)))
        elif "soft" in n:
            axes.append(50)
        elif "wonk" in n:
            axes.append(0)
        else:
            axes.append(a["default"])
    f.set_variation_by_axes(axes)
    _font_cache[key] = f
    return f


def tokens(text):
    out, hl = [], False
    for w in text.split():
        if w.startswith("*"):
            hl = True
        out.append((w.replace("*", ""), hl))
        if w.rstrip(".,!?:;").endswith("*"):
            hl = False
    return out


def wrap(draw, toks, f, width):
    lines, cur = [], []
    for t in toks:
        trial = " ".join(w for w, _ in cur + [t])
        if cur and draw.textlength(trial, font=f) > width:
            lines.append(cur)
            cur = [t]
        else:
            cur.append(t)
    if cur:
        lines.append(cur)
    return lines


def draw_rich(draw, x, y, text, f, color, hl_color, width, lh=1.12, shadow=False):
    for line in wrap(draw, tokens(text), f, width):
        cx = x
        for i, (w, hl) in enumerate(line):
            piece = w + (" " if i < len(line) - 1 else "")
            if shadow:
                draw.text((cx + 2, y + 3), piece, font=f, fill=(0, 0, 0, 110))
            draw.text((cx, y), piece, font=f, fill=hl_color if hl else color)
            cx += draw.textlength(piece, font=f)
        y += int(f.size * lh)
    return y


def fit(draw, text, kind, weight, width, max_h, start, minimum, lh):
    size = start
    while size > minimum:
        f = font(kind, size, weight)
        if len(wrap(draw, tokens(text), f, width)) * size * lh <= max_h:
            return f
        size -= 4
    return font(kind, minimum, weight)


def cover(path):
    im = Image.open(path).convert("RGB")
    return ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.4))


def darken(img, strength=0.5):
    """Uniform tint plus a stronger band behind the text area, keeps photo visible at edges."""
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    for y in range(H):
        # strongest around the text zone (y ~ 500-1300), lighter at top/bottom
        d = abs(y - 900) / 900
        a = int(255 * (strength + (1 - d) * 0.22))
        od.line([(0, y), (W, y)], fill=C["ink"] + (min(a, 235),))
    return Image.alpha_composite(img.convert("RGBA"), over)


def text_layer(s, t, dark_bg):
    """Draw the slide's text on a transparent layer starting at y=0. Returns (layer, height)."""
    width = SAFE_R - SAFE_L
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    main = C["cream"] if dark_bg else C["ink"]
    body_c = C["cream"] if dark_bg else C["ink_soft"]
    hl = C["accent_light"] if dark_bg else C["terracotta"]
    sh = dark_bg
    y = 0
    if t == "hook":
        f = fit(d, s["text"], "serif", 600, width, 900, 132, 72, 1.08)
        y = draw_rich(d, SAFE_L, y, s["text"], f, main, hl, width, 1.08, sh)
        if s.get("sub"):
            y = draw_rich(d, SAFE_L, y + 40, s["sub"], font("sans", 46, 500), C["muted_dark"] if dark_bg else C["muted"], hl, width, 1.3, sh)
    elif t in ("point", "list"):
        if t == "point" and s.get("num"):
            d.text((SAFE_L, y), str(s["num"]).zfill(2), font=font("serif", 170, 300), fill=hl)
            y += 220
        f = fit(d, s["title"], "serif", 600, width, 460, 108, 64, 1.1)
        y = draw_rich(d, SAFE_L, y, s["title"], f, main, hl, width, 1.1, sh)
        d.rectangle((SAFE_L, y + 30, SAFE_L + 90, y + 37), fill=hl)
        y += 100
        bf = font("sans", 54, 500 if dark_bg else 400)
        if t == "point":
            y = draw_rich(d, SAFE_L, y, s["body"], bf, body_c, hl, width, 1.38, sh)
        else:
            for item in s["items"]:
                d.ellipse((SAFE_L, y + 24, SAFE_L + 18, y + 42), fill=hl)
                y = draw_rich(d, SAFE_L + 48, y, item, bf, body_c, hl, width - 48, 1.3, sh) + 34
    elif t == "cta":
        f = fit(d, s["text"], "serif", 600, width, 700, 110, 64, 1.1)
        y = draw_rich(d, SAFE_L, y, s["text"], f, main, hl, width, 1.1, sh)
        if s.get("sub"):
            y = draw_rich(d, SAFE_L, y + 40, s["sub"], font("sans", 46, 500), body_c, hl, width, 1.35, sh)
    return layer, y


def counter(draw, i, n, color):
    draw.text((SAFE_L, SAFE_T - 90), f"{i}/{n}", font=font("sans", 32, 600), fill=color)


def render_app(s, shot_path):
    img = Image.new("RGBA", (W, H), C["cream"] + (255,))
    d = ImageDraw.Draw(img)
    width = SAFE_R - SAFE_L
    y = SAFE_T - 40
    f = fit(d, s["title"], "serif", 600, width, 260, 88, 56, 1.1)
    y = draw_rich(d, SAFE_L, y, s["title"], f, C["ink"], C["terracotta"], width, 1.1)
    shot = Image.open(shot_path).convert("RGB")
    max_h = SAFE_B + 120 - (y + 60)
    scale = min(max_h / shot.height, 700 / shot.width)
    shot = shot.resize((int(shot.width * scale), int(shot.height * scale)), Image.LANCZOS)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, shot.width, shot.height), radius=int(56 * scale * 2.4), fill=255)
    x = (W - shot.width) // 2
    top = y + 60
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x, top + 20, x + shot.width, top + 20 + shot.height), radius=60, fill=(0, 0, 0, 70))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(30)))
    img.paste(shot, (x, top), mask)
    return img


def render_slide(s, i, n, photo=None, shot=None):
    t = s["type"]
    if t == "app":
        if shot:
            return render_app(s, shot).convert("RGB")
        s, t = {"type": "cta", "text": s["title"], "sub": "on the App Store"}, "cta"  # fallback

    if photo:
        img = darken(cover(photo), 0.22 if t == "hook" else 0.30)
        dark = True
    elif t in ("hook",):
        img = Image.new("RGBA", (W, H), C["ink"] + (255,))
        dark = True
    elif t == "cta":
        img = Image.new("RGBA", (W, H), C["terracotta"] + (255,))
        dark = True
    else:
        img = Image.new("RGBA", (W, H), C["cream"] + (255,))
        dark = False

    layer, h = text_layer(s, t, dark)
    top = int(SAFE_T + max(0, (SAFE_B - SAFE_T - h) / 2) - 40)
    img.alpha_composite(layer, (0, top))
    d = ImageDraw.Draw(img)
    if t in ("point", "list"):
        counter(d, i, n, C["muted_dark"] if dark else C["muted"])
    if t == "hook" and s.get("swipe", True):
        d.text((SAFE_L, SAFE_B - 10), "swipe →", font=font("sans", 36, 700), fill=C["accent_light"])
    return img.convert("RGB")


def render(content_path, assets_dir=None, out_dir=None):
    data = json.load(open(content_path))
    sid = data["id"]
    assets = os.path.join(assets_dir or os.path.join(ROOT, "build", "assets"), sid)
    out = out_dir or os.path.join(ROOT, "site", "days", sid)
    os.makedirs(out, exist_ok=True)
    n = len(data["slides"])
    files = []
    for i, s in enumerate(data["slides"], 1):
        photo = os.path.join(assets, f"{i:02d}.jpg")
        shot = os.path.join(assets, f"{i:02d}-app.png")
        img = render_slide(
            s, i, n,
            photo=photo if (data.get("style", "photo") == "photo" and os.path.exists(photo)) else None,
            shot=shot if os.path.exists(shot) else None,
        )
        p = os.path.join(out, f"{i:02d}.jpg")
        img.save(p, quality=92, optimize=True)
        files.append(p)
    return out, files


if __name__ == "__main__":
    a = sys.argv[1:]
    print(render(a[0], a[1] if len(a) > 1 else None, a[2] if len(a) > 2 else None)[0])
