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
