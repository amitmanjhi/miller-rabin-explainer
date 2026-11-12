"""Render a ~5 minute narrated explainer of the Miller-Rabin primality test.

Requires: macOS `say`, ffmpeg (libx264), Pillow.
Usage:    python3 make_video.py            -> miller_rabin_explained.mp4
"""
import os, re, subprocess, sys, tempfile, wave

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 24
VOICE, RATE = "Samantha", 196
GAP, SCENE_GAP, LEAD = 0.35, 0.9, 0.6
OUT = "miller_rabin_explained.mp4"

BG = (15, 18, 32)
FG = (232, 232, 240)
DIM = (140, 145, 170)
YEL = (255, 209, 102)
GRN = (6, 214, 160)
RED = (239, 71, 111)
BLU = (76, 201, 240)
BOX = (34, 40, 66)
HL = (52, 60, 98)

FONTS = {
    "sans": ("/System/Library/Fonts/HelveticaNeue.ttc", 0),
    "bold": ("/System/Library/Fonts/HelveticaNeue.ttc", 1),
    "math": ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
    "mono": ("/System/Library/Fonts/Menlo.ttc", 0),
}
_fc = {}


def font(kind, size):
    k = (kind, size)
    if k not in _fc:
        path, idx = FONTS[kind]
        _fc[k] = ImageFont.truetype(path, size, index=idx)
    return _fc[k]


def mix(c, a):
    return tuple(int(BG[i] + (c[i] - BG[i]) * a) for i in range(3))


# ---------------------------------------------------------------- rich text
# "a^{n-1}" renders the braced part as a raised superscript.
def _parts(s):
    out, i = [], 0
    for m in re.finditer(r"\^\{([^}]*)\}", s):
        if m.start() > i:
            out.append((s[i:m.start()], False))
        out.append((m.group(1), True))
        i = m.end()
    if i < len(s):
        out.append((s[i:], False))
    return out


def rich_width(s, kind, size):
    w = 0
    for txt, sup in _parts(s):
        w += font(kind, int(size * 0.62) if sup else size).getlength(txt)
    return w


def rich(d, x, y, s, size, color, kind="math", anchor="l"):
    w = rich_width(s, kind, size)
    if anchor == "m":
        x -= w / 2
    elif anchor == "r":
        x -= w
    for txt, sup in _parts(s):
        f = font(kind, int(size * 0.62) if sup else size)
        yy = y - size * 0.38 if sup else y
        d.text((x, yy), txt, font=f, fill=color, anchor="ls")
        x += f.getlength(txt)


# ---------------------------------------------------------------- elements
class El:
    def __init__(self, fn, z=0, hide=None):
        self.fn, self.z, self.hide = fn, z, hide  # hide = sentences until fade-out


def T(s, x, y, size=34, color=FG, kind="sans", anchor="l", **kw):
    return El(lambda d, a: rich(d, x, y, s, size, mix(color, a), kind, anchor), **kw)


def M(s, x, y, size=44, color=FG, anchor="m", **kw):
    return T(s, x, y, size, color, "math", anchor, **kw)


def rect(x0, y0, x1, y1, color, r=12, outline=None, **kw):
    def fn(d, a):
        d.rounded_rectangle((x0, y0, x1, y1), r, fill=mix(color, a),
                            outline=mix(outline, a) if outline else None, width=3)
    return El(fn, **kw)


def arrow(x0, y, x1, color=DIM, label=None):
    def fn(d, a):
        c = mix(color, a)
        d.line((x0, y, x1 - 4, y), fill=c, width=3)
        d.polygon([(x1, y), (x1 - 12, y - 7), (x1 - 12, y + 7)], fill=c)
        if label:
            rich(d, (x0 + x1) / 2, y - 12, label, 26, c, "math", "m")
    return El(fn)


def chain(values, y, colors=None, notes=None, bw=150, gap=60, size=30):
    """A row of boxes joined by 'square' arrows. Returns list of El (one per box)."""
    n = len(values)
    total = n * bw + (n - 1) * gap
    x = (W - total) / 2
    els = []
    for i, v in enumerate(values):
        col = (colors or [FG] * n)[i]
        bx = x + i * (bw + gap)
        parts = [rect(bx, y - 40, bx + bw, y + 40, BOX, outline=col),
                 M(v, bx + bw / 2, y + 12, size, col)]
        if i:
            parts.append(arrow(bx - gap + 6, y, bx - 6, DIM, "²"))
        if notes and notes[i]:
            parts.append(T(notes[i], bx + bw / 2, y + 78, 22, col, "sans", "m"))
        els.append(group(parts))
    return els


def group(els, **kw):
    def fn(d, a):
        for e in els:
            e.fn(d, a)
    return El(fn, **kw)


# ---------------------------------------------------------------- script
CODE = """def is_prime(n):
    if n < 2: return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n % p == 0: return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2; s += 1
    for a in small:
        x = pow(a, d, n)
        if x in (1, n - 1): continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1: break
        else:
            return False
    return True""".split("\n")
CX, CY, LH, CS = 170, 112, 27, 20


def code_block():
    def fn(d, a):
        for i, line in enumerate(CODE):
            d.text((CX - 50, CY + i * LH), f"{i+1:>2}", font=font("mono", CS), fill=mix(DIM, a * 0.6))
            d.text((CX, CY + i * LH), line, font=font("mono", CS), fill=mix(FG, a))
    return El(fn)


def hl(l0, l1, color=HL):
    return rect(CX - 14, CY + (l0 - 1) * LH - 4, CX + 900, CY + l1 * LH - 2, color, r=6, z=-1, hide=1)


cx = W / 2
SCENES = [
    ("", [
        ("How can a computer tell, in a few milliseconds, whether a number with hundreds of digits is prime?",
         [T("Is this number prime?", cx, 300, 64, FG, "bold", "m")]),
        ("In the next five minutes, we'll build the answer: the Miller-Rabin test.",
         [T("The Miller–Rabin test", cx, 380, 40, YEL, "sans", "m")]),
        ("It rests on two simple facts about primes, and one clever way of combining them.",
         [T("Fact 1: Fermat's little theorem", cx, 470, 28, BLU, "sans", "m"),
          T("Fact 2: square roots of 1", cx, 515, 28, BLU, "sans", "m")]),
    ]),
    ("The obvious way is too slow", [
        ("The obvious method is trial division: try dividing n by every number up to its square root.",
         [M("Trial division: try every divisor up to √n", cx, 200, 38)]),
        ("For a seven digit number, that's about a thousand divisions. Easy.",
         [M("n ≈ 1,000,000   →   ~1,000 divisions", cx, 290, 34, GRN)]),
        ("But for a number with three hundred digits, the square root has a hundred and fifty digits.",
         [M("n has 300 digits   →   √n has 150 digits", cx, 360, 34, RED)]),
        ("Even at a billion divisions per second, that takes far longer than the age of the universe.",
         [M("≈ 10^{133} years at 10^{9} per second", cx, 430, 34, RED)]),
        ("So instead of searching for a factor, we'll look for evidence that n is composite, without ever finding the factor.",
         [T("New goal: prove “composite” without finding a factor", cx, 530, 32, YEL, "sans", "m")]),
    ]),
    ("Fact 1: Fermat's little theorem", [
        ("Here is the first fact. If p is prime, and a is not a multiple of p, then a to the power p minus one leaves remainder one when divided by p.",
         [M("p prime   ⇒   a^{p−1} ≡ 1  (mod p)", cx, 210, 50, YEL)]),
        ("Try p equals seven, and a equals two. Two to the sixth is sixty four, which is nine sevens plus one. Remainder one, as promised.",
         [M("2^{6} = 64 = 9·7 + 1   ✓", cx, 310, 40, GRN)]),
        ("Now try fifteen. Two to the fourteenth, modulo fifteen, is four. Not one.",
         [M("2^{14} mod 15 = 4   ✗", cx, 390, 40, RED)]),
        ("So fifteen cannot be prime. We proved it composite without ever finding three or five.",
         [T("15 is composite — and we never found 3 or 5", cx, 470, 30, FG, "sans", "m")]),
        ("And these powers are cheap: by repeated squaring, even a thousand digit exponent needs only a few thousand multiplications.",
         [T("Fast: repeated squaring  →  ~ (number of digits) multiplications", cx, 550, 24, DIM, "math", "m")]),
    ]),
    ("The loophole: Carmichael numbers", [
        ("Unfortunately, some composite numbers pass this test for every base.",
         [T("Some composites fool Fermat for every base a", cx, 200, 34, FG, "sans", "m")]),
        ("The smallest is five hundred sixty one, which is three times eleven times seventeen.",
         [M("561 = 3 · 11 · 17", cx, 300, 52, YEL)]),
        ("Yet for every a that shares no factor with it, a to the five hundred sixty, modulo five hundred sixty one, is one.",
         [M("a^{560} ≡ 1  (mod 561)   for every such a", cx, 390, 38, RED)]),
        ("These are called Carmichael numbers, and there are infinitely many of them. We need a sharper test.",
         [T("Carmichael numbers — infinitely many. Need a sharper test.", cx, 490, 30, DIM, "sans", "m")]),
    ]),
    ("Fact 2: square roots of 1", [
        ("The second fact is about square roots of one.", []),
        ("If x squared leaves remainder one modulo a prime p, then p divides x squared minus one, which is x minus one, times x plus one.",
         [M("x² ≡ 1 (mod p)   ⇒   p divides (x − 1)(x + 1)", cx, 210, 38)]),
        ("A prime that divides a product must divide one of the factors. So x is either one, or minus one.",
         [M("⇒   x ≡ 1   or   x ≡ −1  (that is, p − 1)", cx, 290, 38, GRN)]),
        ("Modulo a composite, that's no longer true. Modulo fifteen, four squared is sixteen, which is one more than fifteen.",
         [M("mod 15:   4² = 16 ≡ 1,   but 4 ≠ ±1", cx, 390, 38, RED)]),
        ("So four is a fake square root of one. And finding a fake square root of one proves the number is composite.",
         [T("A “fake” square root of 1  ⇒  composite", cx, 490, 34, YEL, "sans", "m")]),
    ]),
    ("Combining the two facts", [
        ("Now the clever part. Write n minus one as a power of two, times an odd number d.",
         [M("n − 1 = 2^{s} · d,     d odd", cx, 170, 44, YEL)]),
        ("Start with a to the d, and keep squaring. After s squarings, you reach a to the n minus one.",
         chain(["a^{d}", "a^{2d}", "a^{4d}", "…", "a^{n−1}"], 300, size=28)),
        ("If n is prime, the chain must end in one. That's Fermat.",
         [T("↑ must be 1 (Fermat)", 1060, 375, 22, GRN, "math", "m")]),
        ("And the value just before the first one is a square root of one, so it has to be minus one.",
         [T("and the value just before the first 1 must be −1", cx, 410, 24, BLU, "math", "m")]),
        ("So a prime can only make two shapes of chain: all ones from the start, or something that reaches minus one, followed by ones.",
         [M("prime shapes:    1, 1, 1, …, 1      or      …, −1, 1, …, 1", cx, 470, 32, GRN)]),
        ("Any other shape proves n is composite.",
         [T("Any other shape  ⇒  composite", cx, 550, 34, RED, "sans", "m")]),
    ]),
    ("Example: a prime, n = 13, a = 2", [
        ("Let's try n equals thirteen, with base two. Twelve is four times three, so s is two and d is three.",
         [M("13 − 1 = 12 = 2² · 3      s = 2,  d = 3", cx, 180, 40, YEL)]),
        ("Two cubed is eight. Eight squared is sixty four, which is twelve modulo thirteen: that's minus one. One more squaring gives one.",
         chain(["8", "12", "1"], 320, [FG, BLU, GRN], [None, "= −1", None], bw=170, gap=90, size=36)),
        ("Minus one, then one. Exactly the shape a prime is allowed to make.",
         [T("−1 then 1  ✓  consistent with a prime", cx, 500, 34, GRN, "sans", "m")]),
    ]),
    ("Example: catching 561, a = 2", [
        ("Now the Carmichael number five hundred sixty one, which fooled Fermat.", []),
        ("Five hundred sixty is sixteen times thirty five, so we start with two to the thirty fifth, modulo five hundred sixty one.",
         [M("560 = 2⁴ · 35       start with 2^{35} mod 561", cx, 180, 38, YEL)]),
        ("The chain is two sixty three, one sixty six, sixty seven, one, and one.",
         chain(["263", "166", "67", "1", "1"], 320, [FG, FG, RED, GRN, GRN], bw=140, gap=55, size=34)),
        ("It ends in one, so Fermat is satisfied. But the value before the first one is sixty seven, not minus one.",
         [T("67 ≠ −1  (−1 would be 560)", 652, 405, 22, RED, "math", "m")]),
        ("Sixty seven squared is one, so it's a fake square root of one. Five hundred sixty one is composite. Caught.",
         [T("Fake square root of 1  ⇒  561 is composite. Caught!", cx, 510, 34, RED, "sans", "m")]),
    ]),
    ("The code, line by line", [
        ("Here is the code again.", [code_block()]),
        ("First, it divides by a few small primes. That handles tiny n, and removes easy factors quickly.", [hl(2, 5)]),
        ("Next, it pulls the factors of two out of n minus one, to get s and d.", [hl(6, 8)]),
        ("For each base, it computes a to the d, the first link of the chain. If that's already one or minus one, the chain is fine, so it moves on.", [hl(9, 11)]),
        ("Otherwise it keeps squaring, looking for minus one. Finding it means this chain has a legal shape.", [hl(12, 14)]),
        ("If minus one never shows up, the chain has an illegal shape, and the function returns false: composite.", [hl(15, 16, (90, 40, 60))]),
        ("If every base passes, it returns true: prime.", [hl(17, 17, (30, 80, 70))]),
    ]),
    ("Why a few bases are enough", [
        ("A base that exposes a composite is called a witness.",
         [T("witness = a base whose chain has an illegal shape", cx, 190, 32, FG, "sans", "m")]),
        ("A theorem by Rabin and Monier says that for any odd composite, at least three quarters of all bases are witnesses. Nothing can hide the way Carmichael numbers hide from Fermat.",
         [M("Any odd composite:  ≥ 3/4 of bases are witnesses", cx, 280, 38, YEL)]),
        ("So each random base misses with probability at most one quarter, and forty bases miss with probability below two to the minus eighty.",
         [M("P(miss with k bases) ≤ (1/4)^{k}       k = 40  ⇒  < 2^{−80}", cx, 370, 34, GRN)]),
        ("For fixed bases, people have searched exhaustively. Using the first twelve primes is exactly right for every number below three point three times ten to the twenty four. That covers every sixty four bit integer.",
         [M("first 12 primes as bases: exact for n < 3.3 × 10^{24}", cx, 460, 34, BLU),
          T("(covers every 64-bit integer)", cx, 510, 24, DIM, "sans", "m")]),
    ]),
    ("Is primality testing in P?", [
        ("So, is primality testing in P? Yes.",
         [T("PRIMES ∈ P", cx, 220, 60, GRN, "math", "m")]),
        ("In two thousand two, Agrawal, Kayal and Saxena found the A K S algorithm: deterministic, unconditional, and polynomial in the number of digits.",
         [T("AKS (2002): deterministic, polynomial in the number of digits", cx, 310, 30, FG, "sans", "m")]),
        ("In practice, though, Miller-Rabin is far faster, and it's what real software uses.",
         [T("In practice: Miller–Rabin is much faster", cx, 380, 30, YEL, "sans", "m")]),
        ("And notice the twist: we can prove a number composite without finding its factors. Factoring itself is not known to be easy, and that gap is what keeps RSA secure.",
         [M("testing: easy        factoring: no known fast method  →  RSA", cx, 480, 30, BLU)]),
    ]),
    ("Recap", [
        ("To recap. Fermat says a to the n minus one must be one.",
         [M("1.  a^{n−1} ≡ 1  (mod n)", 260, 220, 40, YEL, "l")]),
        ("Modulo a prime, the only square roots of one are one and minus one.",
         [M("2.  x² ≡ 1  ⇒  x ≡ ±1", 260, 310, 40, BLU, "l")]),
        ("Miller-Rabin walks the squaring chain and checks both facts at once. Try a few bases, and you know.",
         [M("3.  walk aᵈ → a²ᵈ → … and check the shape", 260, 400, 40, GRN, "l"),
          T("Thanks for watching!", cx, 540, 30, DIM, "sans", "m")]),
    ]),
]


# ---------------------------------------------------------------- audio
def build_audio(tmp):
    rate, frames_all, timeline = None, [], []
    t = LEAD
    sent_id = 0
    for si, (_, lines) in enumerate(SCENES):
        for li, (text, _) in enumerate(lines):
            path = os.path.join(tmp, f"s{sent_id}.wav")
            subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "--data-format=LEI16@22050",
                            "-o", path, text], check=True)
            with wave.open(path) as w:
                rate = w.getframerate()
                data = w.readframes(w.getnframes())
            dur = len(data) / 2 / rate
            timeline.append((si, li, t, t + dur, text))
            frames_all.append((t, data))
            t += dur + (SCENE_GAP if li == len(lines) - 1 else GAP)
            sent_id += 1
            print(f"\raudio {sent_id}", end="", flush=True)
    total = t + 1.0
    buf = bytearray(int(total * rate) * 2)
    for start, data in frames_all:
        o = int(start * rate) * 2
        buf[o:o + len(data)] = data
    out = os.path.join(tmp, "narration.wav")
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(bytes(buf))
    print(f"\naudio length {total:.1f}s")
    return out, timeline, total


# ---------------------------------------------------------------- video
def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if f.getlength(test) > maxw and cur:
            lines.append(cur); cur = wd
        else:
            cur = test
    lines.append(cur)
    return lines


def render(timeline, total, audio):
    # Per-scene element schedule: (El, appear_time, hide_time or None)
    sched = {}
    sent_starts = {}
    for si, li, t0, t1, _ in timeline:
        sent_starts[(si, li)] = t0
    scene_start = {si: sent_starts[(si, 0)] for si in range(len(SCENES))}
    for si, (_, lines) in enumerate(SCENES):
        items = []
        for li, (_, els) in enumerate(lines):
            for e in els:
                hide = sent_starts.get((si, li + e.hide)) if e.hide else None
                items.append((e, sent_starts[(si, li)], hide))
        items.sort(key=lambda it: it[0].z)
        sched[si] = items

    cap_font = font("sans", 22)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)

    cache_key, cache_val = None, None
    nframes = int(total * FPS)
    for fi in range(nframes):
        t = fi / FPS
        si = max([s for s, st in scene_start.items() if st <= t] or [0])
        cur = None
        for row in timeline:
            if row[2] <= t:
                cur = row
        alphas = []
        for e, ta, th in sched[si]:
            a = min(max((t - ta) / 0.45, 0), 1)
            if th is not None:
                a *= 1 - min(max((t - th) / 0.25, 0), 1)
            alphas.append(round(a * 12) / 12)
        title_a = round(min(max((t - scene_start[si] + 0.3) / 0.45, 0), 1) * 12) / 12
        key = (si, cur[:2] if cur else None, tuple(alphas), title_a)
        if key != cache_key:
            img = Image.new("RGB", (W, H), BG)
            d = ImageDraw.Draw(img)
            title = SCENES[si][0]
            if title:
                d.text((60, 62), title, font=font("bold", 36), fill=mix(YEL, title_a), anchor="ls")
                d.line((60, 80, 60 + 80, 80), fill=mix(YEL, title_a), width=3)
            for (e, _, _), a in zip(sched[si], alphas):
                if a > 0:
                    e.fn(d, a)
            if cur:
                d.rectangle((0, 615, W, H), fill=(10, 12, 22))
                for k, line in enumerate(wrap(cur[4], cap_font, W - 160)[:3]):
                    d.text((W / 2, 648 + k * 28), line, font=cap_font, fill=DIM, anchor="ms")
            cache_key, cache_val = key, img.tobytes()
        ff.stdin.write(cache_val)
        if fi % (FPS * 10) == 0:
            print(f"\rvideo {t:6.1f}/{total:.1f}s", end="", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        audio, timeline, total = build_audio(tmp)
        render(timeline, total, audio)
