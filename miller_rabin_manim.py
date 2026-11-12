"""Narrated Manim explainer of the Miller-Rabin primality test.

Requires: manim (Community Edition), ffmpeg, Pillow, and macOS `say` for narration.
Render:
    manim -r 1920,1080 --frame_rate 30 miller_rabin_manim.py MillerRabin
"""
import hashlib
import re
import subprocess
import wave
from pathlib import Path

from PIL import ImageFont
from manim import (
    DOWN, LEFT, RIGHT, UP, ORIGIN, Arrow, Code, Create, FadeIn, FadeOut, GrowArrow,
    Indicate, LaggedStart, MarkupText, RoundedRectangle, Scene, SurroundingRectangle,
    Text, Transform, VGroup, Group, Write, config, Square,
)

config.background_color = "#0f1220"

VOICE, RATE = "Samantha", 205
GAP = 0.25  # silence after each sentence
VOICE_DIR = Path("media/voice")
FONT = "Helvetica Neue"
FONT_FILE = "/System/Library/Fonts/HelveticaNeue.ttc"  # only used to measure caption widths

FG, DIM = "#e8e8f0", "#8c91aa"
YEL, GRN, RED, BLU = "#ffd166", "#06d6a0", "#ef476f", "#4cc9f0"
BOX = "#222842"

# Layout limits (frame is ~14.2 x 8 units). Captions live below CAPTION_TOP.
CAPTION_TOP = -2.85
CAPTION_MAX_W = 12.5

# Smallest composite that passes the strong test for all of the first 12 prime bases
# (Sorenson & Webster, 2015). Below it, those 12 bases give an exact answer.
PSI_12 = 318665857834031151167461

CODE = '''def is_prime(n):  # exact for n < 3.18e23 (all 64-bit ints)
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
    return True'''


# ------------------------------------------------------------------ math helpers
def split_n_minus_1(n):
    """n - 1 = 2**s * d with d odd. n must be an odd integer >= 3."""
    if n < 3 or n % 2 == 0:
        raise ValueError("n must be odd and >= 3")
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    return s, d


def squaring_chain(a, n):
    """[a^d, a^2d, ..., a^(n-1)], every entry reduced mod n."""
    s, d = split_n_minus_1(n)
    x = pow(a, d, n)
    chain = [x]
    for _ in range(s):
        x = x * x % n
        chain.append(x)
    return chain


def passes_strong_test(a, n):
    """True if base a does NOT expose n (for composite n: a is a 'strong liar')."""
    chain = squaring_chain(a, n)
    return chain[0] == 1 or (n - 1) in chain[:-1]


def is_prime(n):
    """The function shown on screen, kept in sync with CODE."""
    ns = {}
    exec(CODE, ns)
    return ns["is_prime"](n)


# Sanity checks for every number the narration states.
assert pow(2, 6) % 7 == 1 and pow(2, 14, 15) == 4
assert pow(3, 560, 561) != 1                     # Fermat needs a coprime base
assert all(pow(a, 560, 561) == 1 for a in range(2, 561) if a % 3 and a % 11 and a % 17)
assert squaring_chain(2, 13) == [8, 12, 1]
assert squaring_chain(2, 561) == [263, 166, 67, 1, 1] and 67 * 67 == 8 * 561 + 1
LIARS_561 = [a for a in range(2, 560) if passes_strong_test(a, 561)]
assert len(LIARS_561) == 8
assert [is_prime(k) for k in range(30)] == [k in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29) for k in range(30)]
assert not is_prime(561) and is_prime(2**61 - 1)
assert is_prime(PSI_12)  # the documented limit of the fixed-base version


# ------------------------------------------------------------------ text helpers
SAFE_W = 13.0  # widest any single line of text may be (frame is ~14.2 wide)


def _fit(m):
    if m.width > SAFE_W:
        m.scale_to_fit_width(SAFE_W)
    return m


def T(s, size=36, color=FG, **kw):
    return _fit(Text(s, font=FONT, font_size=size, color=color, **kw))


_SUP = str.maketrans("0123456789−-+adnpsk", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁻⁺ᵃᵈⁿᵖˢᵏ")


def M(s, size=44, color=FG):
    """Pango markup; <sup>…</sup> becomes Unicode superscripts (Pango's own <sup> renders too small)."""
    s = re.sub(r"<sup>(.*?)</sup>", lambda m: m.group(1).translate(_SUP), s)
    return _fit(MarkupText(s, font=FONT, font_size=size, color=color))


def box(label, color=FG, w=1.9, h=1.0, size=34):
    rect = RoundedRectangle(corner_radius=0.15, width=w, height=h, stroke_color=color,
                            stroke_width=3, fill_color=BOX, fill_opacity=1)
    return VGroup(rect, M(label, size, color).move_to(rect))


def chain_row(labels, colors=None, w=1.9, buff=0.9, size=34):
    """Boxes joined by 'square' arrows, as one VGroup(boxes, arrows)."""
    colors = colors or [FG] * len(labels)
    boxes = VGroup(*[box(l, c, w=w, size=size) for l, c in zip(labels, colors)]).arrange(RIGHT, buff=buff)
    arrows = VGroup()
    for b1, b2 in zip(boxes[:-1], boxes[1:]):
        arr = Arrow(b1.get_right(), b2.get_left(), buff=0.08, stroke_width=4, color=DIM,
                    max_tip_length_to_length_ratio=0.3)
        arr.add(M("²", 26, DIM).next_to(arr, UP, buff=0.05))
        arrows.add(arr)
    return VGroup(boxes, arrows)


_measure = ImageFont.truetype(FONT_FILE, 100)


def split_caption(text):
    """Best two-line split by rendered width (minimises the wider line)."""
    words = text.split()
    best, best_w = None, float("inf")
    for i in range(1, len(words)):
        w = max(_measure.getlength(" ".join(words[:i])), _measure.getlength(" ".join(words[i:])))
        if w < best_w:
            best, best_w = i, w
    return " ".join(words[:best]), " ".join(words[best:])


# ------------------------------------------------------------------ scene
class MillerRabin(Scene):
    def setup(self):
        VOICE_DIR.mkdir(parents=True, exist_ok=True)
        self.caption = None

    # -- narration ---------------------------------------------------------
    def voice(self, text):
        key = hashlib.sha1(f"{VOICE}|{RATE}|{text}".encode()).hexdigest()[:16]
        path = VOICE_DIR / f"{key}.wav"
        if not path.exists():
            # `say` occasionally hangs forever; synthesize to a temp file with a timeout and retry.
            tmp = path.with_suffix(".tmp.wav")
            for attempt in range(3):
                try:
                    subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "--data-format=LEI16@22050",
                                    "-o", str(tmp), text], check=True, timeout=30)
                    tmp.rename(path)
                    break
                except subprocess.TimeoutExpired:
                    tmp.unlink(missing_ok=True)
            else:
                raise RuntimeError(f"`say` kept timing out on: {text!r}")
        with wave.open(str(path)) as w:
            return str(path), w.getnframes() / w.getframerate()

    def set_caption(self, text):
        if self.caption is not None:
            self.remove(self.caption)
        cap = T(text, 22, DIM)
        if cap.width > CAPTION_MAX_W:
            cap = VGroup(*[T(line, 22, DIM) for line in split_caption(text)]).arrange(DOWN, buff=0.12)
        if cap.width > CAPTION_MAX_W:
            cap.scale_to_fit_width(CAPTION_MAX_W)
        cap.to_edge(DOWN, buff=0.35)
        assert cap.get_top()[1] < CAPTION_TOP + 0.05, text
        self.caption = cap
        self.add(cap)

    def say(self, text, *steps, step_time=1.0):
        """Speak `text`, playing each step (an Animation or a tuple of them) during it.

        Waits on real elapsed scene time, so a sentence never ends before its audio does.
        """
        path, dur = self.voice(text)
        self.set_caption(text)
        started = self.renderer.time
        self.add_sound(path)
        if steps:
            rt = min(step_time, max(0.3, dur * 0.85 / len(steps)))
            for st in steps:
                anims = st if isinstance(st, (tuple, list)) else (st,)
                self.play(*anims, run_time=rt)
        self.wait(max(0.0, dur - (self.renderer.time - started)) + GAP)

    def chapter(self, title):
        old = [m for m in self.mobjects if m is not self.caption]
        if old:
            self.play(*[FadeOut(m) for m in old], run_time=0.5)
        t = T(title, 40, YEL, weight="BOLD").to_corner(UP + LEFT, buff=0.5)
        self.play(FadeIn(t, shift=0.2 * RIGHT), run_time=0.5)

    # -- story -------------------------------------------------------------
    def construct(self):
        self.intro()
        self.trial_division()
        self.fermat()
        self.carmichael()
        self.square_roots()
        self.combine()
        self.example_13()
        self.example_561()
        self.witnesses()
        self.code_walkthrough()
        self.complexity()
        self.recap()

    def intro(self):
        q = T("Is this number prime?", 64, FG, weight="BOLD").shift(UP * 0.8)
        sub = T("The Miller–Rabin test", 40, YEL).next_to(q, DOWN, buff=0.4)
        facts = VGroup(T("Fact 1: Fermat's little theorem", 28, BLU),
                       T("Fact 2: square roots of 1", 28, BLU)).arrange(DOWN, buff=0.2).next_to(sub, DOWN, buff=0.7)
        self.say("How can a computer tell, in a few milliseconds, whether a number with hundreds of digits is prime?",
                 Write(q))
        self.say("In the next five minutes, we'll build the answer: the Miller-Rabin test.", FadeIn(sub, shift=UP * 0.2))
        self.say("It rests on two simple facts about primes, and one clever way of combining them.",
                 LaggedStart(*[FadeIn(f) for f in facts], lag_ratio=0.5))

    def trial_division(self):
        self.chapter("The obvious way is too slow")
        rows = VGroup(
            M("Trial division: try every divisor up to √n", 40),
            M("n ≈ 1,000,000   →   about 1,000 divisions", 34, GRN),
            M("n has 300 digits   →   √n has 150 digits", 34, RED),
            M("≈ 10<sup>133</sup> years, even at 10<sup>9</sup> divisions per second", 34, RED),
            M("New goal: prove “composite” <i>without</i> finding a factor", 36, YEL),
        ).arrange(DOWN, buff=0.45).shift(UP * 0.3)
        self.say("The obvious method is trial division: try dividing n by every number up to its square root.",
                 FadeIn(rows[0]))
        self.say("For a seven digit number, that's about a thousand divisions. Easy.", FadeIn(rows[1]))
        self.say("But for a number with three hundred digits, the square root has a hundred and fifty digits.",
                 FadeIn(rows[2]))
        self.say("Even at a billion divisions per second, that takes far longer than the age of the universe.",
                 FadeIn(rows[3]))
        self.say("So instead of searching for a factor, we'll look for evidence that n is composite, "
                 "without ever finding the factor.", Write(rows[4]))

    def fermat(self):
        self.chapter("Fact 1: Fermat's little theorem")
        thm = M("p prime,  a not a multiple of p   ⇒   a<sup>p−1</sup> ≡ 1  (mod p)", 44, YEL).shift(UP * 1.8)
        ex1 = M("2<sup>6</sup> = 64 = 9 · 7 + 1   ✓", 42, GRN).next_to(thm, DOWN, buff=0.6)
        ex2 = M("2<sup>14</sup> mod 15 = 4   ✗", 42, RED).next_to(ex1, DOWN, buff=0.4)
        concl = T("15 is composite — and we never found 3 or 5", 32).next_to(ex2, DOWN, buff=0.5)
        fast = M("Fast: repeated squaring needs only about (number of digits) multiplications", 26, DIM)
        fast.next_to(concl, DOWN, buff=0.5)
        self.say("Here is the first fact. If p is prime, and a is not a multiple of p, "
                 "then a to the power p minus one leaves remainder one when divided by p.", Write(thm))
        self.say("Try p equals seven, and a equals two. Two to the sixth is sixty four, which is nine sevens plus one. "
                 "Remainder one, as promised.", FadeIn(ex1))
        self.say("Now try fifteen. Two to the fourteenth, modulo fifteen, is four. Not one.", FadeIn(ex2))
        self.say("So fifteen cannot be prime. We proved it composite without ever finding three or five.",
                 FadeIn(concl), Indicate(concl, color=YEL))
        self.say("And these powers are cheap: by repeated squaring, even a thousand digit exponent "
                 "needs only a few thousand multiplications.", FadeIn(fast))

    def carmichael(self):
        self.chapter("The loophole: Carmichael numbers")
        a = T("Some composites pass Fermat's test for every coprime base", 34).shift(UP * 1.8)
        b = M("561 = 3 · 11 · 17", 60, YEL).next_to(a, DOWN, buff=0.6)
        c = M("a<sup>560</sup> ≡ 1  (mod 561)   for every a coprime to 561", 38, RED).next_to(b, DOWN, buff=0.5)
        d = T("Carmichael numbers: infinitely many. We need a sharper test.", 30, DIM).next_to(c, DOWN, buff=0.6)
        self.say("Unfortunately, some composite numbers pass this test for every base that shares no factor with them.",
                 FadeIn(a))
        self.say("The smallest is five hundred sixty one, which is three times eleven times seventeen.", Write(b))
        self.say("For every a coprime to it, a to the five hundred sixty, modulo five hundred sixty one, is one. "
                 "Only bases that happen to share a factor give it away, and for big numbers those are rare.",
                 FadeIn(c))
        self.say("These are called Carmichael numbers, and there are infinitely many of them. We need a sharper test.",
                 FadeIn(d))

    def _sq_table(self, n, y):
        cells = VGroup()
        for x in range(1, n):
            v = x * x % n
            cells.add(VGroup(M(str(x), 26, DIM), M(str(v), 26, GRN if v == 1 else FG)).arrange(DOWN, buff=0.18))
        cells.arrange(RIGHT, buff=0.32)
        head = VGroup(M("x", 26, DIM), M(f"x² mod {n}", 26, DIM)).arrange(DOWN, buff=0.18, aligned_edge=RIGHT)
        head.next_to(cells, LEFT, buff=0.45)
        table = VGroup(head, cells).move_to(ORIGIN).set_y(y)
        # Build highlights only after the table is in its final position.
        hits = VGroup(*[
            SurroundingRectangle(cell, color=GRN if x in (1, n - 1) else RED, buff=0.08, corner_radius=0.08)
            for x, cell in zip(range(1, n), cells) if x * x % n == 1
        ])
        return table, hits

    def square_roots(self):
        self.chapter("Fact 2: square roots of 1")
        a = M("x² ≡ 1 (mod p)   ⇒   p divides (x − 1)(x + 1)", 38).shift(UP * 2.3)
        b = M("⇒   x ≡ 1   or   x ≡ −1  (that is, p − 1)", 38, GRN).next_to(a, DOWN, buff=0.35)
        t13, h13 = self._sq_table(13, 0.05)
        t15, h15 = self._sq_table(15, -1.5)
        nontriv = T("4 and 11 are nontrivial square roots of 1  ⇒  15 is composite", 28, YEL)
        nontriv.next_to(t15, DOWN, buff=0.35)
        self.say("The second fact is about square roots of one.")
        self.say("If x squared leaves remainder one modulo a prime p, then p divides x squared minus one, "
                 "which is x minus one, times x plus one.", Write(a))
        self.say("A prime that divides a product must divide one of the factors. So x is either one, or minus one.",
                 FadeIn(b))
        self.say("Here are all the squares modulo thirteen, a prime. Only one and twelve square to one, "
                 "and twelve is minus one.", FadeIn(t13), Create(h13))
        self.say("Modulo fifteen, a composite, four and eleven also square to one. Four squared is sixteen, "
                 "which leaves remainder one.", FadeIn(t15), Create(h15))
        self.say("These are called nontrivial square roots of one. A prime has none, so finding even one "
                 "proves the number is composite.", FadeIn(nontriv))

    def combine(self):
        self.chapter("Combining the two facts")
        top = M("n − 1 = 2<sup>s</sup> · d,     d odd", 46, YEL).shift(UP * 2.3)
        modn = T("(n odd, base a from 2 to n − 2, every value reduced mod n)", 24, DIM).next_to(top, DOWN, buff=0.2)
        row = chain_row(["a<sup>d</sup>", "a<sup>2d</sup>", "a<sup>4d</sup>", "…", "a<sup>n−1</sup>"])
        row.shift(UP * 0.75)
        boxes, arrows = row
        fermat = T("↑ must be 1 (Fermat)", 24, GRN).next_to(boxes[-1], DOWN, buff=0.2)
        before = T("…and the first 1 must come right after −1", 26, BLU).next_to(fermat, DOWN, buff=0.25).set_x(0)
        shapes = M("A prime allows only:    1, 1, …, 1     or     …, −1, 1, …, 1", 32, GRN)
        shapes.next_to(before, DOWN, buff=0.4)
        other = T("Never reaching 1, or a 1 right after anything but −1  ⇒  composite", 28, RED)
        other.next_to(shapes, DOWN, buff=0.25)
        self.say("Now the clever part. Take an odd n, and remove every factor of two from n minus one. "
                 "What's left is an odd number d.", Write(top), FadeIn(modn))
        self.say("Start with a to the d, and square it s times. That walks all the way up to a to the n minus one, "
                 "one square root at a time.",
                 FadeIn(boxes[0]),
                 *[(GrowArrow(arr), FadeIn(b)) for arr, b in zip(arrows, boxes[1:])], step_time=0.7)
        self.say("If n is prime, the chain must end in one. That's Fermat.", FadeIn(fermat))
        self.say("And if the chain doesn't start at one, the value just before the first one is a square root of one. "
                 "For a prime, it has to be minus one.", FadeIn(before))
        self.say("So a prime can only make two shapes of chain: all ones from the start, "
                 "or something that reaches minus one, followed by ones.", FadeIn(shapes))
        self.say("A chain that never reaches one fails Fermat. A first one that follows anything other than "
                 "minus one is a nontrivial square root. Either way, n is composite.",
                 FadeIn(other), Indicate(other, color=RED))

    def _example(self, header, labels, colors, w=1.6, buff=0.8):
        top = M(header, 40, YEL).shift(UP * 2.2)
        row = chain_row(labels, colors, w=w, buff=buff, size=38).shift(UP * 0.2)
        return top, row[0], row[1]

    def example_13(self):
        self.chapter("Example: a prime, n = 13, a = 2")
        top, boxes, arrows = self._example("13 − 1 = 12 = 2² · 3        s = 2,  d = 3", ["8", "12", "1"],
                                           [FG, BLU, GRN])
        neg = M("= −1", 24, BLU).next_to(boxes[1], DOWN, buff=0.25)
        ok = T("−1, then 1  ✓  the shape a prime is allowed to make", 32, GRN).shift(DOWN * 1.8)
        self.say("Let's try n equals thirteen, with base two. Twelve is four times three, so s is two and d is three.",
                 Write(top))
        self.say("Two cubed is eight.", FadeIn(boxes[0]))
        self.say("Eight squared is sixty four, which is twelve modulo thirteen. That's minus one.",
                 (GrowArrow(arrows[0]), FadeIn(boxes[1])), FadeIn(neg))
        self.say("One more squaring gives one.", (GrowArrow(arrows[1]), FadeIn(boxes[2])))
        self.say("Minus one, then one. Exactly the shape a prime is allowed to make. "
                 "Base two finds no evidence against thirteen.", FadeIn(ok))

    def example_561(self):
        self.chapter("Example: catching 561, a = 2")
        top, boxes, arrows = self._example("560 = 2⁴ · 35        start with 2<sup>35</sup> mod 561",
                                           ["263", "166", "67", "1", "1"], [FG, FG, RED, GRN, GRN], w=1.5, buff=0.7)
        note = M("67 ≠ −1  (−1 would be 560)", 26, RED).next_to(boxes[2], DOWN, buff=0.3)
        caught = T("Nontrivial square root of 1  ⇒  561 is composite. Caught!", 34, RED).shift(DOWN * 1.9)
        self.say("Now the Carmichael number five hundred sixty one, which fooled Fermat.")
        self.say("Five hundred sixty is sixteen times thirty five, so s is four, and we start with two to the "
                 "thirty fifth, modulo five hundred sixty one.", Write(top))
        self.say("That's two hundred sixty three.", FadeIn(boxes[0]))
        self.say("Square it: one hundred sixty six.", (GrowArrow(arrows[0]), FadeIn(boxes[1])))
        self.say("Square again: sixty seven.", (GrowArrow(arrows[1]), FadeIn(boxes[2])))
        self.say("Then one, and one again.", (GrowArrow(arrows[2]), FadeIn(boxes[3])),
                 (GrowArrow(arrows[3]), FadeIn(boxes[4])))
        self.say("It ends in one, so Fermat is satisfied. But the value right before the first one is sixty seven, "
                 "not minus one.", Indicate(boxes[2], color=RED, scale_factor=1.15), FadeIn(note))
        self.say("Sixty seven squared leaves remainder one modulo five hundred sixty one, yet sixty seven is neither "
                 "one nor minus one. A prime can't have such a root, so five hundred sixty one is composite. Caught.",
                 FadeIn(caught))

    def witnesses(self):
        self.chapter("Why a few bases are enough")
        cells = VGroup(*[Square(0.16, stroke_width=0, fill_opacity=1,
                                fill_color=GRN if a in LIARS_561 else RED) for a in range(2, 560)])
        cells.arrange_in_grid(rows=18, buff=0.04).shift(DOWN * 0.15)
        legend = VGroup(
            M("every base a from 2 to 559, for n = 561", 26, DIM),
            M(f"<span foreground='{RED}'>■ witness (exposes 561)</span>     "
              f"<span foreground='{GRN}'>■ strong liar ({len(LIARS_561)} of 558)</span>", 26),
        ).arrange(DOWN, buff=0.15).next_to(cells, UP, buff=0.3)
        bound = M("Any odd composite:  at most 1/4 of bases are strong liars", 30, YEL).next_to(cells, DOWN, buff=0.3)
        self.say("A base that exposes a composite is called a witness. A base that doesn't is called a strong liar.",
                 FadeIn(legend[0]))
        self.say(f"Here is every possible base for five hundred sixty one. Red ones are witnesses. "
                 f"Only {len(LIARS_561)} out of five hundred fifty eight are strong liars.",
                 LaggedStart(*[FadeIn(c) for c in cells], lag_ratio=0.004, run_time=2.0), FadeIn(legend[1]),
                 step_time=2.0)
        self.say("A theorem by Rabin and Monier says that for any odd composite, at most one quarter of the bases "
                 "are strong liars. Nothing can hide the way Carmichael numbers hide from Fermat.", FadeIn(bound))
        self.play(*[FadeOut(m) for m in (cells, legend, bound)], run_time=0.4)
        p = M("k independent random bases, all strong liars:   probability ≤ (1/4)<sup>k</sup>", 32, GRN)
        p.shift(UP * 1.3)
        p2 = M("k = 40   ⇒   ≤ 2<sup>−80</sup>", 32, GRN).next_to(p, DOWN, buff=0.3)
        q = M("Fixed bases 2, 3, 5, …, 37 (first 12 primes): exact for n &lt; 3.18 × 10<sup>23</sup>", 32, BLU)
        q.next_to(p2, DOWN, buff=0.6)
        r = T("(that covers every 64-bit integer)", 26, DIM).next_to(q, DOWN, buff=0.25)
        self.say("So if you pick bases independently at random, each one is a strong liar with probability at most "
                 "one quarter. Forty random bases are all fooled with probability at most two to the minus eighty.",
                 FadeIn(p), FadeIn(p2))
        self.say("For fixed bases, people have searched exhaustively instead. The first twelve primes give an exact "
                 "answer for every number below three point one eight times ten to the twenty three. "
                 "That covers every sixty four bit integer.", FadeIn(q), FadeIn(r))

    def code_walkthrough(self):
        self.chapter("The code, line by line")
        code = Code(code_string=CODE, language="python", formatter_style="monokai",
                    background="rectangle",
                    background_config={"fill_color": "#161a2e", "stroke_color": "#2a3050"},
                    paragraph_config={"font": "Menlo"})
        code.scale(min(1, 12.8 / code.width, 5.0 / code.height))
        code.move_to(ORIGIN).set_y(-0.05)
        lines = code.code_lines

        def hl(a, b, color=YEL):
            return SurroundingRectangle(Group(*lines[a - 1:b]), color=color, buff=0.06, corner_radius=0.06)

        steps = [
            ("First, it divides by a few small primes. That handles tiny n, even n, and easy factors.", hl(2, 5)),
            ("Next, it pulls the factors of two out of n minus one, to get s and d.", hl(6, 8)),
            ("For each base, it computes a to the d, the first link of the chain. If that's one or minus one, "
             "the chain already has a legal shape, so it moves on to the next base.", hl(9, 11)),
            ("Otherwise it squares, looking for minus one. It only needs s minus one squarings: "
             "once it finds minus one, the next square is guaranteed to be one.", hl(12, 14)),
            ("In Python, a loop's else block runs only if the loop finished without break. "
             "Here that means minus one never appeared, so this base is a witness, and n is composite.",
             hl(15, 16, RED)),
            ("If no base is a witness, it returns true. With these twelve bases, that's exact below "
             "three point one eight times ten to the twenty three.", hl(17, 17, GRN)),
        ]
        self.say("Here is the code. It does exactly what we just described.", FadeIn(code))
        frame = None
        for text, rect in steps:
            self.say(text, Create(rect) if frame is None else Transform(frame, rect))
            frame = frame or rect

    def complexity(self):
        self.chapter("Is primality testing in P?")
        a = M("PRIMES ∈ P", 64, GRN).shift(UP * 1.6)
        b = T("AKS (2002): deterministic, polynomial in the number of digits", 30).next_to(a, DOWN, buff=0.5)
        c = T("In practice: Miller–Rabin is much faster", 30, YEL).next_to(b, DOWN, buff=0.35)
        d = M("testing: easy        factoring: no known fast method  →  RSA", 30, BLU).next_to(c, DOWN, buff=0.6)
        self.say("So, is primality testing in P? Yes.", Write(a))
        self.say("In two thousand two, Agrawal, Kayal and Saxena found the A K S algorithm: deterministic, "
                 "unconditional, and polynomial in the number of digits.", FadeIn(b))
        self.say("In practice, though, Miller-Rabin is far faster, and it's what real software uses.", FadeIn(c))
        self.say("And notice the twist: we can prove a number composite without finding its factors. "
                 "Factoring itself is not known to be easy, and that gap is what keeps RSA secure.", FadeIn(d))

    def recap(self):
        self.chapter("Recap")
        head = T("If n is prime, then:", 32, DIM)
        items = VGroup(
            head,
            M("1.  a<sup>n−1</sup> ≡ 1  (mod n)", 40, YEL),
            M("2.  x² ≡ 1  ⇒  x ≡ ±1", 40, BLU),
            M("3.  so the chain a<sup>d</sup> → a<sup>2d</sup> → … has a legal shape", 40, GRN),
        ).arrange(DOWN, buff=0.45, aligned_edge=LEFT).shift(UP * 0.4)
        self.add(head)
        self.say("To recap. If n is prime, Fermat says a to the n minus one must be one.", FadeIn(items[1]))
        self.say("And the only square roots of one are one and minus one.", FadeIn(items[2]))
        self.say("Miller-Rabin walks the squaring chain and checks both facts at once. An illegal shape proves n "
                 "composite. Twelve fixed bases settle every sixty four bit number, and a few dozen random bases "
                 "make an error astronomically unlikely for any size.", FadeIn(items[3]))
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=1.0)
