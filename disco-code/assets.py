"""SVG costumes and synthesized WAV sounds for Disco Code (all original art)."""
import io, math, random, struct, wave
import numpy as np

FONT = "Sans Serif"   # one of Scratch's built-in font names, so it renders everywhere

CAT_COLORS = {
    "motion":  "#29d9ff",
    "looks":   "#b45cff",
    "sound":   "#ff4fd8",
    "control": "#ffa62e",
    "pen":     "#3dff8f",
    "disco":   "#fff15c",
    "events":  "#ffe94f",
}

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))

def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join("%02x" % round(a[i] * (1 - t) + b[i] * t) for i in range(3))

# rough bold 10px width table (calibrated against Scratch's Sans Serif)
def tw(text, size=9):
    w = 0
    for ch in text:
        if ch == " ": w += .28
        elif ch in "il.,:;!|'": w += .27
        elif ch in "jtfrI()[]°-": w += .36
        elif ch in "mwMW": w += .86
        elif ch.isupper(): w += .66
        elif ch.isdigit(): w += .58
        else: w += .57
    return w * size * 1.13

def svg(w, h, body):
    # transparent rect pins the bounding box so rotation centres are exact
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'version="1.1" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="#000" fill-opacity="0"/>{body}</svg>')

def neon_path(d, color, fill):
    return (f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="0.16" stroke-width="7" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-opacity="0.35" stroke-width="3.5" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="1.5" stroke-linejoin="round"/>')

def text(x, y, s, size=9, fill="#fff", anchor="start", weight="bold", font=FONT, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}" {extra}>{esc(s)}</text>')

M = 5   # margin for glow
H = 20  # block body height
SLOT_W = {"n": 26, "t": 56}

def block_path(L, T, W, top="notch", tab_x=8, top_x=8):
    r = 3
    p = []
    if top == "hat":
        p.append(f"M {L} {T} C {L+14} {T-13} {L+48} {T-13} {L+64} {T}")
    else:
        nx = L + top_x
        p.append(f"M {L+r} {T} L {nx} {T} L {nx+3} {T+3} L {nx+9} {T+3} L {nx+12} {T}")
    bx = L + tab_x
    p.append(f"L {L+W-r} {T} Q {L+W} {T} {L+W} {T+r} L {L+W} {T+H-r} Q {L+W} {T+H} {L+W-r} {T+H} "
             f"L {bx+12} {T+H} L {bx+9} {T+H+3} L {bx+3} {T+H+3} L {bx} {T+H} L {L+r} {T+H} "
             f"Q {L} {T+H} {L} {T+H-r} L {L} {T+r if top != 'hat' else T}")
    if top != "hat":
        p.append(f"Q {L} {T} {L+r} {T}")
    p.append("Z")
    return " ".join(p)

def flag_icon(x, y, s=1.0, color="#3dff8f"):
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<path d="M0 0 L0 13" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>'
            f'<path d="M0 1 C3 -1 6 3 10 1 L10 7 C6 9 3 5 0 7 Z" fill="{color}" stroke="{color}" stroke-width="1" stroke-linejoin="round"/></g>')

def block_costume(before, kind, after, color, shape="stack"):
    """Returns (svg, rotation_center, slot_offset). slot_offset is from the block's left edge."""
    x0 = 7
    if shape == "hat":
        before = "when"
    tb = tw(before) if before else 0
    if kind:
        sx = x0 + tb + 4
        sw = SLOT_W[kind]
        ax = sx + sw + 4
        W = ax + (tw(after) + 7 if after else 3)
    else:
        sx = -1
        W = x0 + tb + 8
    if shape == "hat":
        W = x0 + tw("when") + 18 + tw("clicked") + 8
    if shape == "end":
        W = 46
    W = max(W, 38 if shape != "hat" else 70)
    W = round(W)
    top_pad = 13 if shape == "hat" else 0
    L, T = M, M + top_pad
    cw, ch = W + 2 * M, T + H + 3 + M
    fill = mix(color, "#0d0220", .8)
    if shape == "hat":
        d = block_path(L, T, W, top="hat")
    elif shape == "c":
        d = block_path(L, T, W, tab_x=20)
    elif shape == "end":
        d = block_path(L, T, W, top_x=20)
    else:
        d = block_path(L, T, W)
    body = neon_path(d, color, fill)
    ty = T + 14
    if shape == "hat":
        body += text(L + x0, ty, "when")
        fx = L + x0 + tw("when") + 4
        body += flag_icon(fx, T + 4, 0.95)
        body += text(fx + 15, ty, "clicked")
    elif shape == "end":
        # little loop arrow
        body += (f'<path d="M {L+30} {T+6} A 5 5 0 1 0 {L+35} {T+12}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>'
                 f'<path d="M {L+27} {T+4} L {L+31} {T+6.5} L {L+28} {T+10}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    else:
        if before:
            body += text(L + x0, ty, before)
        if kind and after:
            body += text(L + ax, ty, after)
    return svg(cw, ch, body), (L, T + H / 2), (sx if kind else -1)

def bar_costume(color):
    L, T = M, M
    fill = mix(color, "#0d0220", .8)
    cw, ch = 12 + 2 * M, H + 2 * M
    body = (f'<rect x="{L}" y="{T-2}" width="12" height="{H+4}" fill="{fill}"/>'
            f'<path d="M {L} {T-2} L {L} {T+H+2}" stroke="{color}" stroke-opacity=".3" stroke-width="4"/>'
            f'<path d="M {L} {T-2} L {L} {T+H+2}" stroke="{color}" stroke-width="1.5"/>'
            f'<path d="M {L+12} {T-2} L {L+12} {T+H+2}" stroke="{color}" stroke-width="1.5"/>')
    return svg(cw, ch, body), (L, T + H / 2)

def slot_costume(kind):
    sw = SLOT_W[kind]
    body = (f'<rect x="2" y="2" width="{sw}" height="14" rx="7" fill="#07010f" stroke="#ffffff" stroke-opacity=".9" stroke-width="1"/>')
    return svg(sw + 4, 18, body), (2, 9)

def char_costume(ch):
    return svg(8, 16, text(4, 12.2, ch, size=10, anchor="middle")), (4, 9)

def cat_costume(name, color):
    lab = name.capitalize()
    body = ""
    if name == "disco":
        stops = "".join(f'<stop offset="{i/5}" stop-color="{c}"/>' for i, c in
                        enumerate(["#ff4fd8", "#ffa62e", "#fff15c", "#3dff8f", "#29d9ff", "#b45cff"]))
        body += f'<defs><linearGradient id="rb" x1="0" y1="0" x2="1" y2="1">{stops}</linearGradient></defs>'
        fill = "url(#rb)"
    else:
        fill = color
    body += (f'<circle cx="20" cy="12" r="11" fill="{color}" fill-opacity=".25"/>'
             f'<circle cx="20" cy="12" r="8" fill="{fill}" stroke="#ffffff" stroke-width="1.2"/>'
             + text(20, 31, lab, size=7.5, anchor="middle", fill="#f3e9ff"))
    return svg(40, 35, body), (20, 17)

def groovy(pose):
    """Groovy: an original disco blob with a rainbow afro and star shades."""
    afro_cols = ["#7a2cff", "#b45cff", "#ff4fd8", "#29d9ff"]
    rnd = random.Random(7)
    afro = ""
    for i in range(16):
        a = math.pi * (0.95 + 1.1 * i / 15)
        x = 45 + 27 * math.cos(a); y = 36 + 20 * math.sin(a)
        afro += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(9,12):.1f}" fill="{afro_cols[i%4]}"/>'
    afro += '<ellipse cx="45" cy="26" rx="24" ry="14" fill="#7a2cff"/>'
    arms = ('<path d="M18 58 Q6 48 4 34" stroke="#ff4fd8" stroke-width="6" fill="none" stroke-linecap="round"/>'
            '<path d="M72 58 Q84 48 86 34" stroke="#ff4fd8" stroke-width="6" fill="none" stroke-linecap="round"/>'
            if pose == 2 else
            '<path d="M18 60 Q6 66 6 76" stroke="#ff4fd8" stroke-width="6" fill="none" stroke-linecap="round"/>'
            '<path d="M72 58 Q86 52 88 40" stroke="#ff4fd8" stroke-width="6" fill="none" stroke-linecap="round"/>')
    def star(cx, cy, r):
        pts = []
        for k in range(10):
            rr = r if k % 2 == 0 else r * .5
            a = -math.pi / 2 + k * math.pi / 5
            pts.append(f"{cx + rr*math.cos(a):.1f},{cy + rr*math.sin(a):.1f}")
        return f'<polygon points="{" ".join(pts)}" fill="#0b0218" stroke="#29d9ff" stroke-width="1.6" stroke-linejoin="round"/>'
    mouth = ('<ellipse cx="45" cy="66" rx="6" ry="5" fill="#2a0638"/>' if pose == 2 else
             '<path d="M35 63 Q45 72 55 63" stroke="#2a0638" stroke-width="3" fill="none" stroke-linecap="round"/>')
    body = (f'<defs><radialGradient id="bg" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#ffb3f0"/>'
            f'<stop offset="1" stop-color="#ff2fc0"/></radialGradient></defs>'
            + arms + afro +
            '<ellipse cx="34" cy="86" rx="9" ry="4" fill="#fff15c"/><ellipse cx="56" cy="86" rx="9" ry="4" fill="#fff15c"/>'
            '<circle cx="45" cy="56" r="27" fill="url(#bg)" stroke="#ffffff" stroke-width="1.5"/>'
            + star(35, 50, 9) + star(55, 50, 9) +
            '<path d="M42 50 L48 50" stroke="#29d9ff" stroke-width="2"/>' + mouth +
            '<circle cx="28" cy="60" r="3" fill="#ff8ad8"/><circle cx="62" cy="60" r="3" fill="#ff8ad8"/>')
    return svg(90, 92, body), (45, 56)

def ball_costume(phase):
    rnd = random.Random(phase)
    tiles = ""
    for gy in range(-12, 13, 4):
        for gx in range(-12, 13, 4):
            if gx * gx + gy * gy < 12 * 12:
                c = rnd.choice(["#e9e4ff", "#b9b0d9", "#8f86b8", "#ffffff", "#d7c9ff"])
                tiles += f'<rect x="{20+gx-1.8}" y="{20+gy-1.8}" width="3.6" height="3.6" fill="{c}"/>'
    sp = ""
    for _ in range(3):
        x, y = rnd.uniform(10, 30), rnd.uniform(10, 30)
        sp += f'<path d="M{x} {y-4} L{x+1} {y-1} L{x+4} {y} L{x+1} {y+1} L{x} {y+4} L{x-1} {y+1} L{x-4} {y} L{x-1} {y-1} Z" fill="#fff"/>'
    body = ('<path d="M20 0 L20 7" stroke="#d7c9ff" stroke-width="1"/>'
            '<defs><clipPath id="cb"><circle cx="20" cy="20" r="12.5"/></clipPath></defs>'
            '<circle cx="20" cy="20" r="13" fill="#5e558a"/>'
            f'<g clip-path="url(#cb)">{tiles}</g>'
            '<circle cx="20" cy="20" r="13" fill="none" stroke="#ff4fd8" stroke-opacity=".6" stroke-width="1.5"/>' + sp)
    return svg(40, 40, body), (20, 20)

def flag_btn():
    body = ('<rect x="1" y="1" width="18" height="16" rx="4" fill="#0d0220" stroke="#3dff8f" stroke-opacity=".5"/>'
            + flag_icon(5.5, 2.5, 1.0))
    return svg(20, 18, body), (10, 9)

def stop_btn():
    pts = " ".join(f"{10+6*math.cos(math.pi/8+k*math.pi/4):.1f},{9+6*math.sin(math.pi/8+k*math.pi/4):.1f}" for k in range(8))
    body = ('<rect x="1" y="1" width="18" height="16" rx="4" fill="#0d0220" stroke="#ff3b6b" stroke-opacity=".5"/>'
            f'<polygon points="{pts}" fill="#ff3b6b" stroke="#ff8aa6" stroke-width="1"/>')
    return svg(20, 18, body), (10, 9)

def turbo_label():
    body = ('<path d="M6 2 L2 9 L5.5 9 L3.5 15 L9.5 6.5 L6 6.5 L8 2 Z" fill="#fff15c"/>'
            + text(12, 12, "Turbo Mode", size=8.5, fill="#fff15c"))
    return svg(64, 17, body), (32, 8.5)

def tool_costume(name):
    if name in ("up", "down"):
        tri = "M6 13 L11 6 L16 13 Z" if name == "up" else "M6 7 L11 14 L16 7 Z"
        body = ('<circle cx="11" cy="10" r="9" fill="#170733" stroke="#29d9ff" stroke-width="1.3"/>'
                f'<path d="{tri}" fill="#29d9ff"/>')
        return svg(22, 20, body), (11, 10)
    if name == "clear":
        body = ('<circle cx="11" cy="10" r="9" fill="#170733" stroke="#ff4fd8" stroke-width="1.3"/>'
                '<path d="M7 7 L15 7 M10 5.5 L12 5.5 M8 7 L8.8 15 L13.2 15 L14 7" stroke="#ff4fd8" stroke-width="1.4" fill="none" stroke-linejoin="round"/>')
        return svg(22, 20, body), (11, 10)
    lab = "RESET GROOVY"
    body = ('<rect x="2" y="2" width="80" height="16" rx="8" fill="#170733" stroke="#3dff8f" stroke-width="1.3"/>'
            + text(42, 13.5, lab, size=8, anchor="middle", fill="#3dff8f"))
    return svg(84, 20, body), (42, 10)

def beam_costume():
    body = ('<defs><linearGradient id="bm" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#ffffff" stop-opacity=".9"/>'
            '<stop offset=".5" stop-color="#ff4fd8" stop-opacity=".35"/>'
            '<stop offset="1" stop-color="#29d9ff" stop-opacity="0"/></linearGradient></defs>'
            '<path d="M2 30 L440 2 L440 58 Z" fill="url(#bm)"/>')
    return svg(442, 60, body), (2, 30)

def backdrop(dark=False):
    W, Hh = 480, 360
    X = lambda x: x + 240
    Y = lambda y: 180 - y
    b = []
    b.append(f'<rect x="0" y="0" width="{W}" height="{Hh}" fill="#0b0218"/>')
    # header
    b.append('<defs><linearGradient id="hd" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="#5a0f9e"/><stop offset=".5" stop-color="#b0127f"/>'
             '<stop offset="1" stop-color="#3a0b7a"/></linearGradient>'
             '<pattern id="dots" width="12" height="12" patternUnits="userSpaceOnUse">'
             '<circle cx="6" cy="6" r=".8" fill="#ff4fd8" fill-opacity=".35"/></pattern>'
             '<linearGradient id="logo" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff15c"/>'
             '<stop offset=".5" stop-color="#ff4fd8"/><stop offset="1" stop-color="#29d9ff"/></linearGradient></defs>')
    b.append(f'<rect x="0" y="0" width="{W}" height="24" fill="url(#hd)"/>')
    b.append(f'<path d="M0 24 L{W} 24" stroke="#ff4fd8" stroke-width="1.5"/>')
    b.append(text(8, 17, "DISCO", size=15, fill="url(#logo)", font="Marker", weight="normal"))
    b.append(text(64, 17, "CODE", size=15, fill="#ffffff", font="Marker", weight="normal"))
    # globe-ish icon + menus
    for i, (lab, x) in enumerate([("File", 120), ("Edit", 148), ("Tutorials", 176)]):
        b.append(text(x, 16, lab, size=8.5, fill="#f3e9ff"))
    b.append('<rect x="290" y="5" width="44" height="14" rx="7" fill="#ffa62e"/>' + text(312, 15, "Share", 8, anchor="middle", fill="#1a0533"))
    b.append('<rect x="340" y="5" width="74" height="14" rx="7" fill="none" stroke="#fff" stroke-opacity=".8"/>'
             + text(377, 15, "See Project Page", 7.5, anchor="middle", fill="#fff"))
    b.append('<circle cx="433" cy="12" r="7" fill="#29d9ff"/><circle cx="433" cy="10" r="2.6" fill="#0b0218"/>'
             '<path d="M428.5 16.5 Q433 12 437.5 16.5" fill="#0b0218"/>')
    b.append(text(444, 15.5, "JAY", 8.5, fill="#fff"))
    b.append('<path d="M467 10 L470 13.5 L473 10" stroke="#fff" stroke-width="1.2" fill="none"/>')
    # tabs row (y 156..140)
    b.append(f'<rect x="0" y="24" width="{W}" height="16" fill="#12042a"/>')
    for lab, x, w, act in [("Code", 4, 40, True), ("Costumes", 46, 52, False), ("Sounds", 100, 44, False)]:
        b.append(f'<rect x="{x}" y="26" width="{w}" height="14" rx="3" fill="{"#2a0b52" if act else "#170733"}" '
                 f'stroke="{"#ff4fd8" if act else "#3b1a6b"}"/>'
                 + text(x + w / 2, 36, lab, 7.5, anchor="middle", fill="#ff4fd8" if act else "#a58ccf"))
    # stage-size buttons (decor)
    b.append('<rect x="440" y="27" width="14" height="11" rx="2" fill="#170733" stroke="#29d9ff" stroke-width=".8"/>'
             '<rect x="456" y="27" width="20" height="11" rx="2" fill="#2a0b52" stroke="#29d9ff" stroke-width=".8"/>')
    # category column x -240..-200
    b.append(f'<rect x="0" y="40" width="40" height="{Hh-40}" fill="#120428"/>')
    # palette x -200..-100
    b.append(f'<rect x="40" y="40" width="110" height="{Hh-40}" fill="#170733"/>')
    b.append(f'<path d="M40 40 L40 {Hh}" stroke="#3b1a6b"/>')
    # code area x -100..62
    b.append(f'<rect x="150" y="40" width="152" height="{Hh-40}" fill="#0f0322"/>')
    b.append(f'<rect x="150" y="40" width="152" height="{Hh-40}" fill="url(#dots)"/>')
    b.append(f'<rect x="150.75" y="40.75" width="150.5" height="{Hh-41.5}" fill="none" stroke="#ff4fd8" stroke-opacity=".7" stroke-width="1.5"/>')
    # right column
    b.append(f'<rect x="302" y="40" width="178" height="{Hh-40}" fill="#12042a"/>')
    # mini stage x 63..239, y 138..6  -> svg x 303..479, y 42..174
    sx, sy, sw, sh = 303, 42, 176, 132
    b.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#1a0533"/>')
    cols = ["#ff4fd8", "#29d9ff", "#b45cff", "#fff15c", "#3dff8f", "#ffa62e"]
    rnd = random.Random(3)
    tile = 22
    for ty in range(0, 6):
        for tx in range(0, 8):
            if ty >= 3:
                c = cols[(tx + ty * 3) % 6]
                b.append(f'<rect x="{sx+tx*tile+1}" y="{sy+ty*tile+1}" width="{tile-2}" height="{tile-2}" fill="{c}" fill-opacity="{0.10 + 0.06*((tx+ty)%3)}"/>')
    for _ in range(26):
        x, y = rnd.uniform(sx + 4, sx + sw - 4), rnd.uniform(sy + 4, sy + 60)
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(.4,1.2):.1f}" fill="#fff" fill-opacity="{rnd.uniform(.3,.9):.2f}"/>')
    b.append(f'<rect x="{sx-.5}" y="{sy-.5}" width="{sw+1}" height="{sh+1}" fill="none" stroke="#29d9ff" stroke-width="1.5"/>')
    # sprite panel y 2..-180 -> svg 178..360
    b.append(f'<rect x="303" y="179" width="176" height="180" rx="4" fill="#170733" stroke="#3b1a6b"/>')
    b.append(text(310, 192, "Sprite", 8, fill="#a58ccf") +
             f'<rect x="338" y="183" width="60" height="13" rx="3" fill="#0b0218" stroke="#3b1a6b"/>' +
             text(342, 192.5, "Groovy", 8, fill="#fff"))
    b.append(f'<path d="M303 202 L479 202" stroke="#3b1a6b"/>')
    # sprite tile
    g, _ = groovy(1)
    inner = g.split(">", 1)[1].rsplit("</svg>", 1)[0]
    b.append(f'<rect x="312" y="210" width="50" height="54" rx="5" fill="#2a0b52" stroke="#ff4fd8" stroke-width="2"/>')
    b.append(f'<g transform="translate(317,213) scale(.44)">{inner}</g>')
    b.append(text(337, 259, "Groovy", 7, anchor="middle", fill="#fff"))
    # stage tile
    b.append(f'<rect x="420" y="210" width="50" height="54" rx="5" fill="#170733" stroke="#3b1a6b"/>'
             f'<rect x="426" y="216" width="38" height="28" fill="#1a0533" stroke="#29d9ff" stroke-width=".8"/>'
             + "".join(f'<rect x="{427+i*4.7:.1f}" y="{231+j*4.3:.1f}" width="4" height="3.6" fill="{["#ff4fd8","#29d9ff","#fff15c","#3dff8f"][(i+j)%4]}" fill-opacity=".45"/>' for i in range(8) for j in range(3))
             + text(445, 254, "Stage", 7, anchor="middle", fill="#a58ccf"))
    b.append(text(391, 350, "some blocks are still in the closet...", 6, anchor="middle", fill="#5b3f8a", weight="normal"))
    return svg(W, Hh, "".join(b)), (240, 180)

# ---------------------------------------------------------------- sounds
RATE = 22050

def to_wav(sig):
    sig = np.clip(sig, -1, 1)
    data = (sig * 32000).astype("<i2").tobytes()
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(data)
    return bio.getvalue(), len(sig)

def t_axis(sec):
    return np.arange(int(RATE * sec)) / RATE

def kick(sec=.35):
    t = t_axis(sec)
    f = 45 + 110 * np.exp(-t * 30)
    ph = 2 * np.pi * np.cumsum(f) / RATE
    return np.sin(ph) * np.exp(-t * 9) * .95

def snare(sec=.22):
    t = t_axis(sec); rng = np.random.default_rng(1)
    return (rng.uniform(-1, 1, len(t)) * .6 + np.sin(2 * np.pi * 185 * t) * .4) * np.exp(-t * 18) * .8

def hat(sec=.07):
    t = t_axis(sec); rng = np.random.default_rng(2)
    n = rng.uniform(-1, 1, len(t)); n = np.diff(n, prepend=0)
    return n * np.exp(-t * 60) * .45

def clap(sec=.25):
    t = t_axis(sec); rng = np.random.default_rng(3)
    env = np.zeros_like(t)
    for d in (0, .012, .024):
        env += (t >= d) * np.exp(-np.maximum(t - d, 0) * 70)
    env += (t >= .03) * np.exp(-np.maximum(t - .03, 0) * 14) * .6
    return rng.uniform(-1, 1, len(t)) * env * .5

def synth(freq=261.63, sec=.45):
    t = t_axis(sec)
    s = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 6))
    return s * np.exp(-t * 6) * .45 * np.minimum(1, t * 400)

def pop():
    t = t_axis(.08)
    f = 400 + 900 * t / .08
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 40) * .6

def disco_loop():
    bpm = 120; beat = 60 / bpm; bars = 2
    total = int(RATE * beat * 4 * bars)
    out = np.zeros(total)
    def put(sig, at):
        i = int(at * RATE); j = min(total, i + len(sig)); out[i:j] += sig[:j - i]
    bass = [41.2, 82.4, 41.2, 82.4, 55.0, 110.0, 49.0, 98.0]  # E1/E2, A1/A2, G1/G2 octave-bass
    for b in range(4 * bars):
        put(kick(), b * beat)
        put(hat(.12) * 1.3, b * beat + beat / 2)
        if b % 2 == 1:
            put(clap(), b * beat)
        for e in range(2):
            f = bass[(b * 2 + e) % 8 if b < 4 else (b * 2 + e) % 8]
            tt = t_axis(beat / 2 * .9)
            s = np.sign(np.sin(2 * np.pi * f * tt)) * .18 * np.exp(-tt * 5)
            put(s, b * beat + e * beat / 2)
    for b in (1, 3, 5, 7):      # chord stabs
        for f in (329.6, 392.0, 493.9):
            put(synth(f, .2) * .35, b * beat + beat * .75)
    return out * .8
