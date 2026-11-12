# Miller–Rabin explainer

A single Python script that renders a ~5½ minute narrated, captioned explainer
video of the Miller–Rabin primality test:

- why trial division is too slow
- Fermat's little theorem, and how Carmichael numbers (561) fool it
- square roots of 1 modulo a prime
- the squaring chain `a^d → a^2d → … → a^(n−1)` and the two shapes a prime allows
- worked examples (n = 13, n = 561), a line-by-line code walkthrough
- why a few bases suffice, and why PRIMES ∈ P (AKS)

## Requirements

- macOS (narration uses the built-in `say` command, voice "Samantha")
- `ffmpeg` with `libx264` (`brew install ffmpeg`)
- Python 3 with Pillow (`pip install pillow`)

## Usage

```bash
python3 make_video.py
```

Writes `miller_rabin_explained.mp4` (1280×720, 24 fps) in about a minute.

To change the content, edit the `SCENES` list: each scene is a title plus a
list of `(narration sentence, [visual elements])` pairs. Each sentence is
voiced separately, and its visuals fade in exactly when it starts.

## Manim version (`miller_rabin_manim.py`)

A richer, animated version built with [Manim Community](https://www.manim.community/)
(about 6½ minutes at 1080p). It animates the squaring chain step by step, compares
x² mod 13 with x² mod 15, shows every base for 561 colored by witness or strong
liar, and highlights the code block by block. It was reviewed by a second model
(Codex) for code quality and mathematical accuracy. Every number the narration
states is recomputed by `assert`s before rendering.

```bash
python3 -m venv .venv
# pycairo builds from source on macOS: needs `brew install cairo pkg-config`
SDKROOT="$(xcrun --show-sdk-path)" .venv/bin/pip install manim pillow
.venv/bin/manim -r 1920,1080 --frame_rate 30 miller_rabin_manim.py MillerRabin
```

Output lands in `media/videos/miller_rabin_manim/1080p30/MillerRabin.mp4`. Narration
clips are cached in `media/voice/`, so re-renders only regenerate changed sentences.
