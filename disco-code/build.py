"""Builds disco-code.sb3: a neon-disco block-coding editor that runs inside Scratch.

    python3 build.py   ->  disco-code.sb3
"""
import hashlib, json, random, string, zipfile, os
import assets as A

random.seed(42)
def uid():
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(20))

# ============================================================ block DSL
class Blk:
    def __init__(s, op, inputs=None, fields=None, mutation=None):
        s.op, s.inputs, s.fields, s.mutation = op, inputs or {}, fields or {}, mutation

class Menu:
    def __init__(s, op, field, value, expr=None):
        s.op, s.field, s.value, s.expr = op, field, value, expr

class Bc:
    def __init__(s, name): s.name = name

class Color:
    def __init__(s, c): s.c = c

BOOL = {("control_if", "CONDITION"), ("control_if_else", "CONDITION"), ("control_repeat_until", "CONDITION"),
        ("control_wait_until", "CONDITION"), ("operator_and", "OPERAND1"), ("operator_and", "OPERAND2"),
        ("operator_or", "OPERAND1"), ("operator_or", "OPERAND2"), ("operator_not", "OPERAND")}

GVARS, GLISTS, BCASTS = {}, {}, {}
CUR = None

def bcid(name):
    if name not in BCASTS: BCASTS[name] = uid()
    return BCASTS[name]

def vref(name):
    if CUR is not None and name in CUR.lvars: return [name, CUR.lvars[name][0]]
    if name not in GVARS: raise KeyError("unknown var " + name)
    return [name, GVARS[name][0]]

def lref(name):
    return [name, GLISTS[name][0]]

class Target:
    def __init__(s, name, stage=False, layer=0):
        s.name, s.stage, s.layer = name, stage, layer
        s.blocks, s.lvars, s.costumes, s.sounds = {}, {}, [], []
        s.y = 0
        s.props = {}

    def local(s, *names):
        for n in names: s.lvars[n] = (uid(), 0)

    def emit(s, node, parent):
        bid = uid()
        d = {"opcode": node.op, "next": None, "parent": parent, "inputs": {}, "fields": dict(node.fields),
             "shadow": False, "topLevel": False}
        if node.mutation: d["mutation"] = node.mutation
        s.blocks[bid] = d
        for k, v in node.inputs.items():
            if isinstance(v, list):
                if v: d["inputs"][k] = [2, s.emit_seq(v, bid)]
            elif isinstance(v, Menu):
                sid = uid()
                s.blocks[sid] = {"opcode": v.op, "next": None, "parent": bid, "inputs": {},
                                 "fields": {v.field: [v.value, None]}, "shadow": True, "topLevel": False}
                if v.expr is not None:
                    d["inputs"][k] = [3, s.emit(v.expr, bid), sid]
                else:
                    d["inputs"][k] = [1, sid]
            elif isinstance(v, Bc):
                d["inputs"][k] = [1, [11, v.name, bcid(v.name)]]
            elif isinstance(v, Color):
                d["inputs"][k] = [1, [9, v.c]]
            elif isinstance(v, Blk):
                rid = s.emit(v, bid)
                d["inputs"][k] = [2, rid] if (node.op, k) in BOOL else [3, rid, [10, ""]]
            else:
                if isinstance(v, float) and v.is_integer(): v = int(v)
                d["inputs"][k] = [1, [10, str(v)]]
        return bid

    def emit_seq(s, nodes, parent):
        first = prev = None
        for n in nodes:
            if n is None: continue
            if isinstance(n, list):           # allow nested helper lists
                for m in n:
                    bid = s.emit(m, prev or parent)
                    if prev: s.blocks[prev]["next"] = bid
                    else: first = bid
                    prev = bid
                continue
            bid = s.emit(n, prev or parent)
            if prev: s.blocks[prev]["next"] = bid
            else: first = bid
            prev = bid
        return first

    def script(s, hat, body):
        hid = s.emit(hat, None)
        s.blocks[hid].update(topLevel=True, x=0, y=s.y)
        s.y += 60 + 30 * len(body)
        first = s.emit_seq(body, hid)
        s.blocks[hid]["next"] = first
        return hid

    def proc(s, name, body, warp=True):
        did, pid = uid(), uid()
        s.blocks[did] = {"opcode": "procedures_definition", "next": None, "parent": None,
                         "inputs": {"custom_block": [1, pid]}, "fields": {}, "shadow": False,
                         "topLevel": True, "x": 600, "y": s.y}
        s.y += 60 + 30 * len(body)
        s.blocks[pid] = {"opcode": "procedures_prototype", "next": None, "parent": did, "inputs": {},
                         "fields": {}, "shadow": True, "topLevel": False,
                         "mutation": {"tagName": "mutation", "children": [], "proccode": name,
                                      "argumentids": "[]", "argumentnames": "[]",
                                      "argumentdefaults": "[]", "warp": "true" if warp else "false"}}
        s.blocks[did]["next"] = s.emit_seq(body, did)

def call(name, warp=True):
    return Blk("procedures_call", mutation={"tagName": "mutation", "children": [], "proccode": name,
                                            "argumentids": "[]", "warp": "true" if warp else "false"})

# ---- events / control
flag = lambda: Blk("event_whenflagclicked")
recv = lambda n: Blk("event_whenbroadcastreceived", fields={"BROADCAST_OPTION": [n, bcid(n)]})
clicked = lambda: Blk("event_whenthisspriteclicked")
keyhat = lambda k: Blk("event_whenkeypressed", fields={"KEY_OPTION": [k, None]})
asclone = lambda: Blk("control_start_as_clone")
bcast = lambda n: Blk("event_broadcast", {"BROADCAST_INPUT": Bc(n)})
bcastw = lambda n: Blk("event_broadcastandwait", {"BROADCAST_INPUT": Bc(n)})
forever = lambda *b: Blk("control_forever", {"SUBSTACK": list(b)})
repeat = lambda n, *b: Blk("control_repeat", {"TIMES": n, "SUBSTACK": list(b)})
until = lambda c, *b: Blk("control_repeat_until", {"CONDITION": c, "SUBSTACK": list(b)})
IF = lambda c, *b: Blk("control_if", {"CONDITION": c, "SUBSTACK": list(b)})
def IFELSE(c, a, b):
    return Blk("control_if_else", {"CONDITION": c, "SUBSTACK": a, "SUBSTACK2": b})
wait = lambda t: Blk("control_wait", {"DURATION": t})
waituntil = lambda c: Blk("control_wait_until", {"CONDITION": c})
def stop(opt):
    return Blk("control_stop", fields={"STOP_OPTION": [opt, None]},
               mutation={"tagName": "mutation", "children": [],
                         "hasnext": "true" if opt == "other scripts in sprite" else "false"})
clone = lambda: Blk("control_create_clone_of", {"CLONE_OPTION": Menu("control_create_clone_of_menu", "CLONE_OPTION", "_myself_")})
delclone = lambda: Blk("control_delete_this_clone")
# ---- data
var = lambda n: Blk("data_variable", fields={"VARIABLE": vref(n)})
setv = lambda n, v: Blk("data_setvariableto", {"VALUE": v}, {"VARIABLE": vref(n)})
chg = lambda n, v: Blk("data_changevariableby", {"VALUE": v}, {"VARIABLE": vref(n)})
item = lambda i, l: Blk("data_itemoflist", {"INDEX": i}, {"LIST": lref(l)})
llen = lambda l: Blk("data_lengthoflist", fields={"LIST": lref(l)})
addl = lambda v, l: Blk("data_addtolist", {"ITEM": v}, {"LIST": lref(l)})
dell = lambda i, l: Blk("data_deleteoflist", {"INDEX": i}, {"LIST": lref(l)})
delall = lambda l: Blk("data_deletealloflist", fields={"LIST": lref(l)})
insl = lambda v, i, l: Blk("data_insertatlist", {"ITEM": v, "INDEX": i}, {"LIST": lref(l)})
repl = lambda i, l, v: Blk("data_replaceitemoflist", {"INDEX": i, "ITEM": v}, {"LIST": lref(l)})
itemnum = lambda v, l: Blk("data_itemnumoflist", {"ITEM": v}, {"LIST": lref(l)})
# ---- operators
def _b(op, a, b, n1="NUM1", n2="NUM2"): return Blk(op, {n1: a, n2: b})
plus = lambda a, b: _b("operator_add", a, b)
minus = lambda a, b: _b("operator_subtract", a, b)
times = lambda a, b: _b("operator_multiply", a, b)
div = lambda a, b: _b("operator_divide", a, b)
mod = lambda a, b: _b("operator_mod", a, b)
rand = lambda a, b: Blk("operator_random", {"FROM": a, "TO": b})
gt = lambda a, b: _b("operator_gt", a, b, "OPERAND1", "OPERAND2")
lt = lambda a, b: _b("operator_lt", a, b, "OPERAND1", "OPERAND2")
eq = lambda a, b: _b("operator_equals", a, b, "OPERAND1", "OPERAND2")
AND = lambda a, b: _b("operator_and", a, b, "OPERAND1", "OPERAND2")
OR = lambda a, b: _b("operator_or", a, b, "OPERAND1", "OPERAND2")
NOT = lambda a: Blk("operator_not", {"OPERAND": a})
join = lambda a, b: Blk("operator_join", {"STRING1": a, "STRING2": b})
letter = lambda i, s: Blk("operator_letter_of", {"LETTER": i, "STRING": s})
slen = lambda s: Blk("operator_length", {"STRING": s})
rnd = lambda a: Blk("operator_round", {"NUM": a})
mathop = lambda f, x: Blk("operator_mathop", {"NUM": x}, {"OPERATOR": [f, None]})
def ORS(*cs):
    r = cs[0]
    for c in cs[1:]: r = OR(r, c)
    return r
def ANDS(*cs):
    r = cs[0]
    for c in cs[1:]: r = AND(r, c)
    return r
# ---- motion / looks / sound / sensing / pen
gotoxy = lambda x, y: Blk("motion_gotoxy", {"X": x, "Y": y})
point = lambda d: Blk("motion_pointindirection", {"DIRECTION": d})
turnr = lambda d: Blk("motion_turnright", {"DEGREES": d})
turnl = lambda d: Blk("motion_turnleft", {"DEGREES": d})
xpos = lambda: Blk("motion_xposition")
ypos = lambda: Blk("motion_yposition")
dirn = lambda: Blk("motion_direction")
rotstyle = lambda s: Blk("motion_setrotationstyle", fields={"STYLE": [s, None]})
def costume(expr, default):
    if isinstance(expr, str):
        return Blk("looks_switchcostumeto", {"COSTUME": Menu("looks_costume", "COSTUME", expr)})
    return Blk("looks_switchcostumeto", {"COSTUME": Menu("looks_costume", "COSTUME", default, expr)})
nextcos = lambda: Blk("looks_nextcostume")
show = lambda: Blk("looks_show")
hide = lambda: Blk("looks_hide")
setsize = lambda v: Blk("looks_setsizeto", {"SIZE": v})
chgeff = lambda e, v: Blk("looks_changeeffectby", {"CHANGE": v}, {"EFFECT": [e, None]})
seteff = lambda e, v: Blk("looks_seteffectto", {"VALUE": v}, {"EFFECT": [e, None]})
cleareff = lambda: Blk("looks_cleargraphiceffects")
say = lambda m: Blk("looks_say", {"MESSAGE": m})
front = lambda: Blk("looks_gotofrontback", fields={"FRONT_BACK": ["front", None]})
back = lambda: Blk("looks_gotofrontback", fields={"FRONT_BACK": ["back", None]})
cosname = lambda: Blk("looks_costumenumbername", fields={"NUMBER_NAME": ["name", None]})
def playsnd(expr, default=None):
    if isinstance(expr, str):
        return Blk("sound_play", {"SOUND_MENU": Menu("sound_sounds_menu", "SOUND_MENU", expr)})
    return Blk("sound_play", {"SOUND_MENU": Menu("sound_sounds_menu", "SOUND_MENU", default, expr)})
playuntil = lambda n: Blk("sound_playuntildone", {"SOUND_MENU": Menu("sound_sounds_menu", "SOUND_MENU", n)})
sndeff = lambda e, v: Blk("sound_seteffectto", {"VALUE": v}, {"EFFECT": [e, None]})
stopsounds = lambda: Blk("sound_stopallsounds")
mx = lambda: Blk("sensing_mousex")
my = lambda: Blk("sensing_mousey")
mdown = lambda: Blk("sensing_mousedown")
ask = lambda q: Blk("sensing_askandwait", {"QUESTION": q})
answer = lambda: Blk("sensing_answer")
timer = lambda: Blk("sensing_timer")
pendown = lambda: Blk("pen_penDown")
penup = lambda: Blk("pen_penUp")
penclear = lambda: Blk("pen_clear")
pensize = lambda v: Blk("pen_setPenSizeTo", {"SIZE": v})
penhue = lambda v: Blk("pen_changePenColorParamBy", {"COLOR_PARAM": Menu("pen_menu_colorParam", "colorParam", "color"), "VALUE": v})
pencolor = lambda c: Blk("pen_setPenColorToColor", {"COLOR": Color(c)})

# ============================================================ editor data
# op, category, text-before, slot kind, default, text-after
OPS = [
    ("move", "motion", "move", "n", 10, "steps"),
    ("turnR", "motion", "turn right", "n", 15, "°"),
    ("turnL", "motion", "turn left", "n", 15, "°"),
    ("point", "motion", "point", "n", 90, "°"),
    ("changex", "motion", "change x", "n", 10, ""),
    ("changey", "motion", "change y", "n", 10, ""),
    ("home", "motion", "go home", "", "", ""),
    ("bounce", "motion", "bounce", "", "", ""),
    ("say", "looks", "say", "t", "Hi!", ""),
    ("nextcos", "looks", "next costume", "", "", ""),
    ("color", "looks", "color +", "n", 25, ""),
    ("grow", "looks", "size +", "n", 10, ""),
    ("show", "looks", "show", "", "", ""),
    ("hide", "looks", "hide", "", "", ""),
    ("drum", "sound", "play drum", "n", 1, ""),
    ("note", "sound", "play note", "n", 60, ""),
    ("stopsnd", "sound", "stop sounds", "", "", ""),
    ("wait", "control", "wait", "n", 1, "secs"),
    ("repeat", "control", "repeat", "n", 10, ""),
    ("forever", "control", "forever", "", "", ""),
    ("stopall", "control", "stop all", "", "", ""),
    ("pendown", "pen", "pen down", "", "", ""),
    ("penup", "pen", "pen up", "", "", ""),
    ("erase", "pen", "erase all", "", "", ""),
    ("pencolor", "pen", "pen hue +", "n", 10, ""),
    ("pensize", "pen", "pen size", "n", 2, ""),
    ("boogie", "disco", "boogie", "n", 3, "x"),
    ("spin", "disco", "spin", "n", 2, ""),
    ("moonwalk", "disco", "moonwalk", "n", 60, ""),
    ("rainbow", "disco", "rainbow", "", "", ""),
]
OPENERS = ("repeat", "forever")
CATS = ["motion", "looks", "sound", "control", "pen", "disco"]
QUIPS = ["Groovy, baby!", "Feel the beat!", "Let's boogie!", "Disco never dies!", "Far out!", "Shake it!", "Dance floor's open!"]

# layout constants (Scratch stage coords)
PX, PY0, PSTEP = -195, 124, 23          # palette
CX, ROW0, ROWH = -84, 98, 20            # code area
HAT_Y = ROW0 + 23
STX, STY, SC = 151, 72, 176 / 480       # mini stage centre + scale

# costumes for the block sprites
BLOCK_COSTUMES = []   # (name, svg, center)
SLOT_X = {}
for op, cat, before, kind, dflt, after in OPS:
    shape = "c" if op in OPENERS else "stack"
    s, c, sx = A.block_costume(before, kind or None, after, A.CAT_COLORS[cat], shape)
    BLOCK_COSTUMES.append((op, s, c))
    SLOT_X[op] = sx
s, c, _ = A.block_costume("", None, "", A.CAT_COLORS["events"], "hat"); HAT = ("hat", s, c)
s, c, _ = A.block_costume("", None, "", A.CAT_COLORS["control"], "end"); END = ("end", s, c)
s, c = A.bar_costume(A.CAT_COLORS["control"]); BAR = ("bar", s, c)

# ============================================================ project
stage = Target("Stage", stage=True, layer=0)
CUR = stage

def gv(name, val=0):
    GVARS[name] = (uid(), val)
def gl(name, val=None):
    GLISTS[name] = (uid(), list(val or []))

for n, v in [("CAT", "motion"), ("SCROLL", 0), ("RUNNING", 0), ("PC", 1), ("OP", ""), ("A", ""),
             ("YIELD", ""), ("WAITT", 0), ("TURBO", 0), ("TC", 0), ("PARTY", 0), ("UNLOCKED", 0),
             ("KEYPOS", 0), ("KEYCH", ""), ("DRAGOP", ""), ("DRAGARG", ""), ("DRAGFROM", 0),
             ("DRAGDX", 0), ("DRAGDY", 0), ("DRAGSX", 0), ("DRAGSY", 0), ("EDITROLE", ""), ("EDITIDX", 0),
             ("VX", 0), ("VY", 0), ("VSIZE", 100), ("SC", SC), ("STX", STX), ("STY", STY)]:
    gv(n, v)
demo = [("pendown", ""), ("repeat", 36), ("move", 10), ("turnR", 10), ("pencolor", 5), ("end", ""),
        ("penup", ""), ("say", "Groovy!")]
gl("S_OP", [d[0] for d in demo]); gl("S_ARG", [d[1] for d in demo])
for n in ["P_OP", "P_ARG", "L_ROLE", "L_IDX", "L_X", "L_Y", "L_OP", "L_ARG", "B_X", "B_Y", "LS", "LC"]:
    gl(n)
gl("D_OP", [o[0] for o in OPS]); gl("D_CAT", [o[1] for o in OPS]); gl("D_ARG", [o[4] for o in OPS])
gl("D_KIND", [o[3] for o in OPS]); gl("D_SLOT", [round(SLOT_X[o[0]], 1) for o in OPS])
gl("CATS", CATS); gl("QUIPS", QUIPS)

# ---- stage scripts
stage.local("li", "depth", "dd", "yy", "hy", "op", "ans", "kk", "tmp", "maxc")
stage.script(flag(), [
    setv("CAT", "motion"), setv("SCROLL", 0), setv("RUNNING", 0), setv("TURBO", 0), setv("PARTY", 0),
    setv("UNLOCKED", 0), setv("KEYPOS", 0), cleareff(), penclear(),
    call("build palette"), call("layout"),
    bcastw("setup"), bcastw("unrender"), bcast("render"),
])
stage.script(recv("palette"), [call("build palette"), call("layout"), bcastw("unrender"), bcast("render")])
stage.script(recv("relayout"), [call("layout"), bcastw("unrender"), bcast("render")])

def addL(role, idx, x, y, op, arg):
    return [addl(role, "L_ROLE"), addl(idx, "L_IDX"), addl(x, "L_X"), addl(y, "L_Y"), addl(op, "L_OP"), addl(arg, "L_ARG")]

stage.proc("build palette", [
    delall("P_OP"), delall("P_ARG"), setv("li", 1),
    repeat(llen("D_OP"),
        IF(eq(item(var("li"), "D_CAT"), var("CAT")),
           addl(item(var("li"), "D_OP"), "P_OP"), addl(item(var("li"), "D_ARG"), "P_ARG")),
        chg("li", 1)),
])
stage.proc("layout", [
    *[delall(n) for n in ["L_ROLE", "L_IDX", "L_X", "L_Y", "L_OP", "L_ARG", "B_X", "B_Y"]],
    setv("li", 1),
    repeat(llen("P_OP"),
        addL("p", var("li"), PX, minus(PY0, times(minus(var("li"), 1), PSTEP)),
             item(var("li"), "P_OP"), item(var("li"), "P_ARG")),
        chg("li", 1)),
    setv("hy", plus(HAT_Y, times(var("SCROLL"), ROWH))),
    IF(lt(var("hy"), 128), addL("h", 0, CX, var("hy"), "hat", "")),
    setv("depth", 0), setv("li", 1),
    repeat(llen("S_OP"),
        setv("op", item(var("li"), "S_OP")),
        IF(AND(eq(var("op"), "end"), gt(var("depth"), 0)), chg("depth", -1)),
        setv("yy", plus(minus(ROW0, times(minus(var("li"), 1), ROWH)), times(var("SCROLL"), ROWH))),
        IF(AND(lt(var("yy"), 113), gt(var("yy"), -170)),
           addL("s", var("li"), plus(CX, times(var("depth"), 12)), var("yy"), var("op"), item(var("li"), "S_ARG")),
           setv("dd", 0),
           repeat(var("depth"),
               addl(plus(CX, times(var("dd"), 12)), "B_X"), addl(var("yy"), "B_Y"), chg("dd", 1))),
        IF(OR(eq(var("op"), "repeat"), eq(var("op"), "forever")), chg("depth", 1)),
        chg("li", 1)),
])
# editing an input slot
stage.script(recv("edit"), [
    IFELSE(eq(var("EDITROLE"), "p"), [setv("op", item(var("EDITIDX"), "P_OP"))],
                                     [setv("op", item(var("EDITIDX"), "S_OP"))]),
    setv("kk", itemnum(var("op"), "D_OP")),
    IF(gt(var("kk"), 0),
        IFELSE(eq(item(var("kk"), "D_KIND"), "t"),
               [ask("What should Groovy say?"), setv("maxc", 9)],
               [ask("Type a number:"), setv("maxc", 5)]),
        setv("ans", answer()),
        IF(AND(eq(item(var("kk"), "D_KIND"), "n"), NOT(eq(plus(var("ans"), 0), var("ans")))), setv("ans", "")),
        IF(NOT(eq(var("ans"), "")),
            call("truncate"),
            IFELSE(eq(var("EDITROLE"), "p"), [repl(var("EDITIDX"), "P_ARG", var("ans"))],
                                              [repl(var("EDITIDX"), "S_ARG", var("ans"))])),
        bcast("relayout")),
])
stage.proc("truncate", [
    IF(gt(slen(var("ans")), var("maxc")),
        setv("tmp", ""), setv("li", 1),
        repeat(var("maxc"), setv("tmp", join(var("tmp"), letter(var("li"), var("ans")))), chg("li", 1)),
        setv("ans", var("tmp"))),
])
# party mode: stage colour cycling + music
stage.script(recv("party"), [
    IF(eq(var("PARTY"), 1), until(eq(var("PARTY"), 0), chgeff("COLOR", 3), wait(0.04)), cleareff()),
])
stage.script(recv("party"), [
    IF(eq(var("PARTY"), 1), until(eq(var("PARTY"), 0), playuntil("disco loop"))),
])
# secret word D-I-S-C-O
for ch in "disco":
    stage.script(keyhat(ch), [setv("KEYCH", ch), call("secret word")])
stage.proc("secret word", [
    IFELSE(eq(letter(plus(var("KEYPOS"), 1), "disco"), var("KEYCH")), [chg("KEYPOS", 1)],
           [IFELSE(eq(var("KEYCH"), "d"), [setv("KEYPOS", 1)], [setv("KEYPOS", 0)])]),
    IF(eq(var("KEYPOS"), 5), setv("KEYPOS", 0),
       IF(eq(var("UNLOCKED"), 0), setv("UNLOCKED", 1), bcast("unlock"))),
])
stage.script(recv("unlock"), [
    setv("CAT", "disco"), bcast("setup"), bcast("palette"),
    IF(eq(var("PARTY"), 0), setv("PARTY", 1), bcast("party")),
])
stage.script(keyhat("t"), [setv("TURBO", minus(1, var("TURBO"))), bcast("turbo")])
stage.script(keyhat("space"), [bcast("go")])

# ============================================================ sprites
sprites = []
def sprite(name, layer, x=0, y=0, visible=False, **props):
    global CUR
    t = Target(name, layer=layer)
    t.props = dict(visible=visible, x=x, y=y, size=100, direction=90, draggable=False, rotationStyle="all around")
    t.props.update(props)
    sprites.append(t); CUR = t
    return t

def render_pair(t, draw_proc):
    t.script(recv("unrender"), [IF(eq(var("isClone"), 1), delclone())])
    t.script(recv("render"), [IF(eq(var("isClone"), 0), call(draw_proc))])
    t.script(flag(), [setv("isClone", 0), hide()])

def make_clone():
    return [setv("isClone", 1), clone(), setv("isClone", 0)]

# ---- Lights (party beams)
lights = sprite("Lights", 1, x=12, y=166)
lights.local("isClone", "myBase", "myPhase", "li")
lights.costumes = [("beam", A.beam_costume())]
lights.script(flag(), [setv("isClone", 0), hide()])
lights.script(recv("party"), [
    IF(AND(eq(var("PARTY"), 1), eq(var("isClone"), 0)),
        setv("li", 0), gotoxy(12, 160),
        repeat(7,
            setv("myBase", plus(120, times(var("li"), 20))), setv("myPhase", times(var("li"), 50)),
            point(var("myBase")), seteff("COLOR", times(var("li"), 28)), *make_clone(), chg("li", 1))),
])
lights.script(asclone(), [
    back(), seteff("GHOST", 45), show(),
    until(eq(var("PARTY"), 0),
        point(plus(var("myBase"), times(30, mathop("sin", plus(times(timer(), 80), var("myPhase")))))),
        chgeff("COLOR", 4)),
    delclone(),
])

# ---- Block (palette + script blocks)
blk = sprite("Block", 2)
blk.local("isClone", "myRole", "myIdx", "k")
blk.costumes = [(n, (s, c)) for n, s, c in BLOCK_COSTUMES + [HAT, END, BAR]]
render_pair(blk, "draw blocks")
blk.proc("draw blocks", [
    hide(), setv("k", 1),
    repeat(llen("L_ROLE"),
        gotoxy(item(var("k"), "L_X"), item(var("k"), "L_Y")),
        costume(item(var("k"), "L_OP"), "move"),
        setv("myRole", item(var("k"), "L_ROLE")), setv("myIdx", item(var("k"), "L_IDX")),
        *make_clone(), chg("k", 1)),
    setv("k", 1), costume("bar", "bar"), setv("myRole", "b"),
    repeat(llen("B_X"), gotoxy(item(var("k"), "B_X"), item(var("k"), "B_Y")), *make_clone(), chg("k", 1)),
])
blk.script(asclone(), [
    show(),
    forever(
        IFELSE(eq(var("PARTY"), 1),
            [seteff("COLOR", plus(times(timer(), 70), times(ypos(), 1.5)))],
            [IFELSE(AND(eq(var("myRole"), "h"), eq(var("RUNNING"), 1)),
                [seteff("BRIGHTNESS", plus(25, times(15, mathop("sin", times(timer(), 720)))))],
                [cleareff()])])),
])
blk.script(clicked(), [
    IF(eq(var("isClone"), 1),
        IFELSE(eq(var("myRole"), "h"), [bcast("go")], [
            IF(OR(eq(var("myRole"), "p"), eq(var("myRole"), "s")),
                setv("DRAGOP", cosname()),
                IFELSE(eq(var("myRole"), "p"),
                       [setv("DRAGARG", item(var("myIdx"), "P_ARG")), setv("DRAGFROM", 0)],
                       [setv("DRAGARG", item(var("myIdx"), "S_ARG")), setv("DRAGFROM", var("myIdx"))]),
                setv("DRAGDX", minus(xpos(), mx())), setv("DRAGDY", minus(ypos(), my())),
                setv("DRAGSX", mx()), setv("DRAGSY", my()),
                bcast("drag"))])),
])

# ---- Slot (input ovals)
slot = sprite("Slot", 3)
slot.local("isClone", "myRole", "myIdx", "k", "di")
slot.costumes = [("slotN", A.slot_costume("n")), ("slotT", A.slot_costume("t"))]
render_pair(slot, "draw slots")
slot.proc("draw slots", [
    hide(), setv("k", 1),
    repeat(llen("L_ROLE"),
        setv("di", itemnum(item(var("k"), "L_OP"), "D_OP")),
        IF(gt(var("di"), 0), IF(gt(item(var("di"), "D_SLOT"), -1),
            gotoxy(plus(item(var("k"), "L_X"), item(var("di"), "D_SLOT")), item(var("k"), "L_Y")),
            IFELSE(eq(item(var("di"), "D_KIND"), "t"), [costume("slotT", "")], [costume("slotN", "")]),
            setv("myRole", item(var("k"), "L_ROLE")), setv("myIdx", item(var("k"), "L_IDX")),
            *make_clone())),
        chg("k", 1)),
])
EDIT_CLICK = [IF(eq(var("isClone"), 1), setv("EDITROLE", var("myRole")), setv("EDITIDX", var("myIdx")), bcast("edit"))]
slot.script(asclone(), [show()])
slot.script(clicked(), EDIT_CLICK)

# ---- Char (input text, one clone per character)
CHARS = [chr(c) for c in range(33, 127)]
chs = sprite("Char", 4)
chs.local("isClone", "myRole", "myIdx", "k", "di", "s", "n", "c", "sx", "w", "ch")
chs.costumes = [("c_" + ch, A.char_costume(ch)) for ch in CHARS]
render_pair(chs, "draw chars")
chs.proc("draw chars", [
    hide(), setv("k", 1),
    repeat(llen("L_ROLE"),
        setv("di", itemnum(item(var("k"), "L_OP"), "D_OP")),
        IF(gt(var("di"), 0), IF(gt(item(var("di"), "D_SLOT"), -1),
            setv("s", item(var("k"), "L_ARG")), setv("n", slen(var("s"))),
            IFELSE(eq(item(var("di"), "D_KIND"), "t"), [setv("w", A.SLOT_W["t"]), IF(gt(var("n"), 9), setv("n", 9))],
                                                      [setv("w", A.SLOT_W["n"]), IF(gt(var("n"), 4), setv("n", 4))]),
            setv("sx", plus(plus(item(var("k"), "L_X"), item(var("di"), "D_SLOT")),
                            plus(div(minus(var("w"), times(var("n"), 6)), 2), 5))),
            setv("myRole", item(var("k"), "L_ROLE")), setv("myIdx", item(var("k"), "L_IDX")),
            setv("c", 1),
            repeat(var("n"),
                setv("ch", letter(var("c"), var("s"))),
                IF(NOT(eq(var("ch"), " ")),
                    gotoxy(plus(var("sx"), times(minus(var("c"), 1), 6)), item(var("k"), "L_Y")),
                    costume(join("c_", var("ch")), "c_0"), *make_clone()),
                chg("c", 1)))),
        chg("k", 1)),
])
chs.script(asclone(), [show()])
chs.script(clicked(), EDIT_CLICK)

# ---- Category buttons
cat = sprite("Category", 5)
cat.local("isClone", "myCat", "ci")
cat.costumes = [("cat_" + c, A.cat_costume(c, A.CAT_COLORS[c])) for c in CATS]
cat.script(flag(), [setv("isClone", 0), hide()])
cat.script(recv("setup"), [
    IFELSE(eq(var("isClone"), 1), [delclone()], [
        hide(), setv("ci", 1),
        repeat(plus(5, var("UNLOCKED")),
            gotoxy(-220, minus(122, times(minus(var("ci"), 1), 38))),
            costume(join("cat_", item(var("ci"), "CATS")), "cat_motion"),
            setv("myCat", item(var("ci"), "CATS")), *make_clone(), chg("ci", 1))]),
])
cat.script(asclone(), [
    show(),
    forever(IFELSE(eq(var("CAT"), var("myCat")), [setsize(112), seteff("BRIGHTNESS", 0)],
                                                  [setsize(92), seteff("BRIGHTNESS", -20)])),
])
cat.script(clicked(), [IF(eq(var("isClone"), 1), setv("CAT", var("myCat")), bcast("palette"))])

# ---- Tool buttons (scroll, clear, reset)
tool = sprite("Tools", 6)
tool.local("isClone", "myTool")
tool.costumes = [(n, A.tool_costume(n)) for n in ["up", "down", "clear", "reset"]]
tool.script(flag(), [setv("isClone", 0), hide()])
tool.script(recv("setup"), [
    IFELSE(eq(var("isClone"), 1), [delclone()], [
        *[x for name, px, py in [("up", 48, -116), ("down", 48, -140), ("clear", 48, -164), ("reset", 151, -150)]
          for x in [gotoxy(px, py), costume(name, ""), setv("myTool", name), *make_clone()]]]),
])
tool.script(asclone(), [show()])
tool.script(clicked(), [
    IF(eq(var("isClone"), 1),
        seteff("BRIGHTNESS", 40),
        IF(eq(var("myTool"), "up"), IF(gt(var("SCROLL"), 0), chg("SCROLL", -2),
                                       IF(lt(var("SCROLL"), 0), setv("SCROLL", 0)), bcast("relayout"))),
        IF(eq(var("myTool"), "down"), IF(lt(var("SCROLL"), minus(llen("S_OP"), 3)), chg("SCROLL", 2), bcast("relayout"))),
        IF(eq(var("myTool"), "clear"), bcast("halt"), delall("S_OP"), delall("S_ARG"), setv("SCROLL", 0), bcast("relayout")),
        IF(eq(var("myTool"), "reset"), bcast("resetactor")),
        wait(0.15), cleareff()),
])

# ---- Groovy (the actor + the interpreter)
act = sprite("Groovy", 7, x=STX, y=STY, visible=True, size=round(100 * SC, 2))
act.local("ox", "oy", "ax", "ay", "dragged", "n", "t", "dd", "found", "j")
act.costumes = [("groovy1", A.groovy(1)), ("groovy2", A.groovy(2))]
act.sounds = ["drum1", "drum2", "drum3", "drum4", "synth"]

def apply_pos():
    return gotoxy(plus(var("STX"), times(var("VX"), var("SC"))), plus(var("STY"), times(var("VY"), var("SC"))))

act.proc("apply", [apply_pos()])
act.proc("fence", [
    IF(gt(var("VX"), 225), setv("VX", 225)), IF(lt(var("VX"), -225), setv("VX", -225)),
    IF(gt(var("VY"), 165), setv("VY", 165)), IF(lt(var("VY"), -165), setv("VY", -165)),
])
act.proc("reset groovy", [
    penup(), setv("VX", 0), setv("VY", 0), setv("VSIZE", 100), point(90), rotstyle("all around"),
    setsize(times(var("VSIZE"), var("SC"))), cleareff(), say(""), costume("groovy1", ""), show(),
    pencolor("#ff4fd8"), pensize(1.5), call("apply"),
])
act.script(flag(), [setv("SC", SC), setv("STX", STX), setv("STY", STY), front(), call("reset groovy")])
act.script(recv("resetactor"), [stop("other scripts in sprite"), setv("RUNNING", 0), call("reset groovy"), penclear()])
act.script(recv("halt"), [stop("other scripts in sprite"), setv("RUNNING", 0), stopsounds()])

def op_is(name): return eq(var("OP"), name)
def loop_yield():
    return IFELSE(eq(var("TURBO"), 1), [chg("TC", 1), IF(gt(var("TC"), 400), setv("YIELD", "frame"))],
                  [setv("YIELD", "frame")])

EXEC = [
    IF(op_is("move"),
       chg("VX", times(var("A"), mathop("sin", dirn()))), chg("VY", times(var("A"), mathop("cos", dirn()))),
       call("fence"), call("apply")),
    IF(op_is("turnR"), turnr(var("A"))),
    IF(op_is("turnL"), turnl(var("A"))),
    IF(op_is("point"), point(var("A"))),
    IF(op_is("changex"), chg("VX", var("A")), call("fence"), call("apply")),
    IF(op_is("changey"), chg("VY", var("A")), call("fence"), call("apply")),
    IF(op_is("home"), setv("VX", 0), setv("VY", 0), call("apply")),
    IF(op_is("bounce"),
       IF(OR(gt(var("VX"), 224), lt(var("VX"), -224)), point(minus(0, dirn()))),
       IF(OR(gt(var("VY"), 164), lt(var("VY"), -164)), point(minus(180, dirn()))),
       call("fence"), call("apply")),
    IF(op_is("say"), say(var("A"))),
    IF(op_is("nextcos"), nextcos()),
    IF(op_is("color"), chgeff("COLOR", var("A"))),
    IF(op_is("grow"), chg("VSIZE", var("A")),
       IF(lt(var("VSIZE"), 5), setv("VSIZE", 5)), IF(gt(var("VSIZE"), 400), setv("VSIZE", 400)),
       setsize(times(var("VSIZE"), var("SC")))),
    IF(op_is("show"), show()),
    IF(op_is("hide"), hide()),
    IF(op_is("drum"), playsnd(join("drum", plus(mod(minus(rnd(var("A")), 1), 4), 1)), "drum1"), setv("YIELD", "beat")),
    IF(op_is("note"), sndeff("PITCH", times(minus(var("A"), 60), 10)), playsnd("synth"), setv("YIELD", "beat")),
    IF(op_is("stopsnd"), stopsounds()),
    IF(op_is("wait"), setv("WAITT", var("A")), setv("YIELD", "w")),
    IF(op_is("repeat"),
       IFELSE(lt(rnd(var("A")), 1), [call("skip loop")],
              [addl(var("PC"), "LS"), addl(rnd(var("A")), "LC")])),
    IF(op_is("forever"), addl(var("PC"), "LS"), addl(-1, "LC")),
    IF(op_is("end"),
       IF(gt(llen("LS"), 0),
          setv("n", item(llen("LC"), "LC")),
          IFELSE(OR(eq(var("n"), -1), gt(var("n"), 1)),
                 [IF(gt(var("n"), 1), repl(llen("LC"), "LC", minus(var("n"), 1))),
                  setv("PC", item(llen("LS"), "LS"))],
                 [dell(llen("LS"), "LS"), dell(llen("LC"), "LC")]),
          loop_yield())),
    IF(op_is("stopall"), setv("PC", plus(llen("S_OP"), 1))),
    IF(op_is("pendown"), pendown()),
    IF(op_is("penup"), penup()),
    IF(op_is("erase"), penclear()),
    IF(op_is("pencolor"), penhue(var("A"))),
    IF(op_is("pensize"), pensize(plus(times(var("A"), var("SC")), 0.5))),
    IF(ORS(op_is("boogie"), op_is("spin"), op_is("moonwalk"), op_is("rainbow")), setv("YIELD", var("OP"))),
]
act.proc("exec", EXEC)
act.proc("skip loop", [
    setv("dd", 0), setv("found", 0),
    until(OR(eq(var("found"), 1), gt(var("PC"), llen("S_OP"))),
        setv("t", item(var("PC"), "S_OP")),
        IFELSE(OR(eq(var("t"), "repeat"), eq(var("t"), "forever")), [chg("dd", 1)],
               [IF(eq(var("t"), "end"), IFELSE(eq(var("dd"), 0), [setv("found", 1)], [chg("dd", -1)]))]),
        chg("PC", 1)),
])
act.proc("step", [
    setv("YIELD", ""), setv("TC", 0),
    until(ORS(NOT(eq(var("YIELD"), "")), gt(var("PC"), llen("S_OP")), eq(var("RUNNING"), 0)),
        setv("OP", item(var("PC"), "S_OP")), setv("A", item(var("PC"), "S_ARG")), chg("PC", 1),
        call("exec")),
])
act.proc("do yield", [
    IF(eq(var("YIELD"), "w"), wait(var("WAITT"))),
    IF(eq(var("YIELD"), "beat"), wait(0.25)),
    IF(eq(var("YIELD"), "boogie"),
       repeat(rnd(var("A")), turnr(20), costume("groovy2", ""), wait(0.12), turnl(40), costume("groovy1", ""),
              wait(0.12), turnr(20), chgeff("COLOR", 25))),
    IF(eq(var("YIELD"), "spin"), repeat(rnd(times(var("A"), 24)), turnr(15))),
    IF(eq(var("YIELD"), "rainbow"), repeat(36, chgeff("COLOR", 10))),
    IF(eq(var("YIELD"), "moonwalk"),
       repeat(12,
           chg("VX", times(div(var("A"), -12), mathop("sin", dirn()))),
           chg("VY", times(div(var("A"), -12), mathop("cos", dirn()))),
           call("fence"), call("apply"), nextcos(), wait(0.05)),
       costume("groovy1", "")),
], warp=False)
act.script(recv("go"), [
    setv("RUNNING", 1), setv("PC", 1), delall("LS"), delall("LC"),
    until(OR(eq(var("RUNNING"), 0), gt(var("PC"), llen("S_OP"))),
        call("step"), call("do yield", warp=False)),
    setv("RUNNING", 0),
])
act.script(recv("runone"), [
    IF(eq(var("RUNNING"), 0),
       IF(NOT(OR(eq(var("DRAGOP"), "repeat"), eq(var("DRAGOP"), "forever"))),
          delall("LS"), delall("LC"), setv("YIELD", ""),
          setv("OP", var("DRAGOP")), setv("A", var("DRAGARG")), call("exec"), call("do yield", warp=False))),
])
# hidden: click Groovy for a quip + spin; drag Groovy around the stage
act.script(clicked(), [
    setv("ox", mx()), setv("oy", my()), setv("ax", var("VX")), setv("ay", var("VY")), setv("dragged", 0),
    until(NOT(mdown()),
        IF(gt(plus(mathop("abs", minus(mx(), var("ox"))), mathop("abs", minus(my(), var("oy")))), 3), setv("dragged", 1)),
        IF(eq(var("dragged"), 1),
           setv("VX", plus(var("ax"), div(minus(mx(), var("ox")), var("SC")))),
           setv("VY", plus(var("ay"), div(minus(my(), var("oy")), var("SC")))),
           call("fence"), call("apply"))),
    IF(AND(eq(var("dragged"), 0), eq(var("RUNNING"), 0)),
       say(item(rand(1, llen("QUIPS")), "QUIPS")),
       repeat(24, turnr(15)),
       costume("groovy2", ""), wait(0.4), costume("groovy1", ""), wait(0.8), say("")),
])

# ---- header buttons
flg = sprite("Go", 8, x=76, y=147, visible=True)
flg.costumes = [("flag", A.flag_btn())]
flg.script(clicked(), [bcast("go")])
flg.script(flag(), [show(), forever(IFELSE(eq(var("RUNNING"), 1), [seteff("BRIGHTNESS", 35), setsize(112)],
                                                                   [cleareff(), setsize(100)]))])
stp = sprite("Stop", 9, x=97, y=147, visible=True)
stp.costumes = [("stop", A.stop_btn())]
stp.script(clicked(), [bcast("halt")])

ball = sprite("Disco Ball", 10, x=12, y=167, visible=True)
ball.costumes = [("ball1", A.ball_costume(1)), ("ball2", A.ball_costume(2)), ("ball3", A.ball_costume(3))]
ball.script(flag(), [show(), forever(nextcos(), IFELSE(eq(var("PARTY"), 1), [chgeff("COLOR", 25), wait(0.12)],
                                                                          [cleareff(), wait(0.6)]))])
ball.script(clicked(), [setv("PARTY", minus(1, var("PARTY"))), IF(eq(var("PARTY"), 0), stopsounds()), bcast("party")])

trb = sprite("Turbo", 11, x=140, y=147)
trb.costumes = [("turbo", A.turbo_label())]
trb.script(flag(), [hide()])
trb.script(recv("turbo"), [IFELSE(eq(var("TURBO"), 1), [show()], [hide()])])

# ---- Dragger (the block under your mouse while dragging)
drg = sprite("Dragger", 12)
drg.local("moved", "k", "j", "t", "dd", "found", "p", "by")
drg.costumes = [(n, (s, c)) for n, s, c in BLOCK_COSTUMES + [END]]
drg.sounds = ["pop"]
drg.script(flag(), [hide()])
def is_opener(x): return OR(eq(x, "repeat"), eq(x, "forever"))
drg.proc("pick up", [
    setv("k", var("DRAGFROM")),
    IF(eq(item(var("k"), "S_OP"), "end"),
       setv("dd", 0), setv("found", 0), setv("j", minus(var("k"), 1)),
       until(OR(eq(var("found"), 1), lt(var("j"), 1)),
           setv("t", item(var("j"), "S_OP")),
           IFELSE(eq(var("t"), "end"), [chg("dd", 1)],
                  [IF(is_opener(var("t")), IFELSE(eq(var("dd"), 0), [setv("found", 1)], [chg("dd", -1)]))]),
           IF(eq(var("found"), 0), chg("j", -1))),
       IF(eq(var("found"), 1), setv("k", var("j")))),
    setv("DRAGOP", item(var("k"), "S_OP")), setv("DRAGARG", item(var("k"), "S_ARG")),
    IF(is_opener(var("DRAGOP")),
       setv("dd", 0), setv("found", 0), setv("j", plus(var("k"), 1)),
       until(OR(eq(var("found"), 1), gt(var("j"), llen("S_OP"))),
           setv("t", item(var("j"), "S_OP")),
           IFELSE(is_opener(var("t")), [chg("dd", 1)],
                  [IF(eq(var("t"), "end"), IFELSE(eq(var("dd"), 0), [setv("found", 1)], [chg("dd", -1)]))]),
           IF(eq(var("found"), 0), chg("j", 1))),
       IF(eq(var("found"), 1), dell(var("j"), "S_OP"), dell(var("j"), "S_ARG"))),
    dell(var("k"), "S_OP"), dell(var("k"), "S_ARG"),
])
drg.proc("drop", [
    setv("by", plus(my(), var("DRAGDY"))),
    setv("p", plus(rnd(div(minus(plus(ROW0, times(var("SCROLL"), ROWH)), var("by")), ROWH)), 1)),
    IF(lt(var("p"), 1), setv("p", 1)),
    IF(gt(var("p"), plus(llen("S_OP"), 1)), setv("p", plus(llen("S_OP"), 1))),
    insl(var("DRAGARG"), var("p"), "S_ARG"), insl(var("DRAGOP"), var("p"), "S_OP"),
    IF(is_opener(var("DRAGOP")), insl("", plus(var("p"), 1), "S_ARG"), insl("end", plus(var("p"), 1), "S_OP")),
])
drg.script(recv("drag"), [
    setv("moved", 0),
    until(OR(NOT(mdown()), eq(var("moved"), 1)),
        IF(gt(plus(mathop("abs", minus(mx(), var("DRAGSX"))), mathop("abs", minus(my(), var("DRAGSY")))), 4),
           setv("moved", 1))),
    IFELSE(eq(var("moved"), 0),
        [IFELSE(eq(var("DRAGFROM"), 0), [bcast("runone")], [bcast("go")])],
        [IF(gt(var("DRAGFROM"), 0), call("pick up"), bcast("relayout")),
         costume(var("DRAGOP"), "move"), front(), seteff("GHOST", 10), show(),
         until(NOT(mdown()), gotoxy(plus(mx(), var("DRAGDX")), plus(my(), var("DRAGDY")))),
         hide(),
         IF(ANDS(gt(mx(), -90), lt(mx(), 62), lt(my(), 140), gt(my(), -180)), call("drop"), playsnd("pop")),
         bcast("relayout")]),
])

# ============================================================ serialise
assets_out = {}
def add_asset(data, ext):
    if isinstance(data, str): data = data.encode()
    h = hashlib.md5(data).hexdigest()
    assets_out[f"{h}.{ext}"] = data
    return h

def costume_json(name, svg_and_center):
    s, (cx, cy) = svg_and_center
    h = add_asset(s, "svg")
    return {"name": name, "bitmapResolution": 1, "dataFormat": "svg", "assetId": h, "md5ext": h + ".svg",
            "rotationCenterX": cx, "rotationCenterY": cy}

SOUND_SRC = {"drum1": A.kick(), "drum2": A.snare(), "drum3": A.hat(.15), "drum4": A.clap(),
             "synth": A.synth(), "pop": A.pop(), "disco loop": A.disco_loop()}
def sound_json(name):
    data, n = A.to_wav(SOUND_SRC[name])
    h = add_asset(data, "wav")
    return {"name": name, "assetId": h, "dataFormat": "wav", "format": "", "rate": A.RATE, "sampleCount": n,
            "md5ext": h + ".wav"}

stage.costumes = [("Disco Floor", A.backdrop())]
stage.sounds = ["disco loop"]

def target_json(t):
    d = {"isStage": t.stage, "name": t.name,
         "variables": {vid: [n, v] for n, (vid, v) in (GVARS.items() if t.stage else t.lvars.items())},
         "lists": {lid: [n, v] for n, (lid, v) in GLISTS.items()} if t.stage else {},
         "broadcasts": {bid: n for n, bid in BCASTS.items()} if t.stage else {},
         "blocks": t.blocks, "comments": {}, "currentCostume": 0,
         "costumes": [costume_json(n, sc) for n, sc in t.costumes],
         "sounds": [sound_json(n) for n in t.sounds], "volume": 100, "layerOrder": t.layer}
    if t.stage:
        d.update(tempo=60, videoTransparency=50, videoState="on", textToSpeechLanguage=None)
    else:
        d.update(t.props)
    return d

project = {"targets": [target_json(stage)] + [target_json(t) for t in sprites],
           "monitors": [], "extensions": ["pen"],
           "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "disco-code-builder"}}

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disco-code.sb3")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("project.json", json.dumps(project))
    for name, data in assets_out.items():
        z.writestr(name, data)
nblocks = sum(len(t.blocks) for t in [stage] + sprites)
print(f"wrote {out}: {len(sprites)} sprites, {nblocks} blocks, {len(assets_out)} assets, "
      f"{os.path.getsize(out)//1024} KB")
