# TODO

> **Status: vibe-coded DRAFT.** This project was put together quickly, with an
> AI assistant, as a way to understand the Miller–Rabin primality test. It is
> a learning aid, not a polished or reviewed explainer: the math, the narration
> and the code have not been carefully checked. Don't cite it as a reference.

## Correctness

- [ ] Fix the deterministic-bases bound in `make_video.py`. It says the first 12
      primes (2…37) as bases are exact for n < 3.3 × 10²⁴. That bound is for the
      first **13** primes (up to 41). For the first 12 primes, the bound is
      n < 318,665,857,834,031,151,167,461 ≈ 3.18 × 10²³. Both still cover every
      64-bit integer. (Already fixed in `miller_rabin_manim.py`.)
- [ ] Port the other Codex review fixes from `miller_rabin_manim.py` back to
      `make_video.py` (coprime-base wording, "nontrivial square root", `for…else`),
      or retire `make_video.py` in favor of the Manim version.
- [ ] Manim version runs about 6:24; trim toward 5 minutes. Its final caption is long
      enough to be scaled down to fit and reads small.
- [ ] Double-check every other numeric claim in `SCENES` against a source
      (the ≥ 3/4 witnesses bound, the 10¹³³ years estimate, the AKS complexity).
- [ ] Add a small test that recomputes the worked examples (the chains for
      n = 13 and n = 561, 2¹⁴ mod 15) so the slides can't drift from the math.

## Video

- [ ] Watch the full render end to end and check that audio and visuals stay in sync.
- [ ] The "²" labels on the chain arrows are too small to read; enlarge them.
- [ ] Trim the runtime to about 5:00 (currently about 5:27).
- [ ] Consider a nicer TTS voice than macOS `say`.

## Portability and packaging

- [ ] Support narration on non-macOS systems (e.g. `espeak-ng` or a TTS API).
- [ ] Make the font paths configurable; they're hard-coded to macOS system fonts.
- [ ] Add a `requirements.txt` and a LICENSE.
- [ ] Publish a rendered MP4 as a GitHub release, not in the repo.
