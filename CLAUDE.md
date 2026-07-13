# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

This is a **GitHub special profile repository** (`Franklyn-R-Silva/Franklyn-R-Silva`). Because the repo name matches the account name, `README.md` renders on the owner's GitHub profile page. There is no application to build or test — the "product" is the rendered README and the animated SVG it embeds.

## The terminal profile card (main artifact)

The centerpiece is a **terminal-style SVG card** (inspired by `Sushmitadasari/Sushmitadasari`): a fake terminal window running `./profile.sh --live` with a left **VISUAL.MAP** panel (the owner's photo rendered as animated ASCII art) and a right **SYSTEM.INFO** panel (identity/skills/contact fields typed out line-by-line). Animations use SMIL (`<animate>` / clip-path reveals / a moving scanline) — these play on GitHub when the SVG is served from `raw.githubusercontent.com`, so the README references the raw URLs, not relative paths.

Two theme variants are generated:
- `dark.svg` / `light.svg` — selected via `<picture>` `prefers-color-scheme` in `README.md`.

### Regenerating the card

Both SVGs are **generated, not hand-edited**. Source of truth:
- `scripts/build_profile.py` — the generator (needs Pillow: `py -m pip install pillow`).
- `assets/portrait.png` — the source photo the ASCII portrait is derived from.

To change identity text, skills, contacts, or colors, edit the `DATA` dict / `PALETTES` in `scripts/build_profile.py`, then from the repo root run:

```
py scripts/build_profile.py
```

This overwrites `dark.svg` and `light.svg`. **Do not edit the `.svg` files by hand** — changes will be lost on the next regen.

### Generator internals worth knowing

- **ASCII portrait**: `gen_ascii()` crops the photo (`CROP` fractions), boosts contrast, clips dim background below `BLACK_FLOOR` to empty space, then maps brightness to the `RAMP` characters. `COLS` controls detail/size; rows are derived to preserve aspect using the font cell ratio `ADV`×`LH_ASCII`.
- **Font-metric coupling**: the layout math assumes monospace advance `ADV = FS_ASCII * 0.60`. If you change `FS_ASCII`, keep `LH_ASCII` and this ratio consistent or the portrait distorts vertically.
- **SYSTEM.INFO alignment** relies on monospace + `white-space: pre`; values align because each line's `key + dots` prefix is padded to `VALUE_COL` characters. The typing effect is per-line clip-paths (`lc0..lcN`) with staggered `begin` times.
- **Dynamic data**: computed at build time from `datetime.today()` — `DATA["UptimeShort"]` (days since `CODING_SINCE`, shown in the header) and `SYNC` (date, shown in the footer line). **`CODING_SINCE` is a placeholder — set it to when Franklyn actually started coding.** These change daily, which is what the `refresh-card` CI job commits.
- **Animation sequence & timing**: a boot intro (`> booting devOS...`, id `boot`) types first and fades at `BOOT_END`; only then does the ascii reveal mask open (`reveal_begin`) and the info lines type (`begin = BOOT_END + i*0.10`). If you add/remove lines, these derive automatically, but watch the panel-height fit.
- **Glitch**: `#glitch` filter (feTurbulence → feDisplacementMap → per-channel feOffset + `feBlend mode=screen`) tears the whole card and adds RGB chromatic aberration in short bursts (~every 7s, keyed at 0.71–0.84 of the cycle). Extra RGB "ghost" copies of the name (`ghost1`/`ghost2` per theme) flash in sync. `scanblend`/`scanop` are per-theme so the scanline is `screen` on dark but **`multiply` on light** (screen is invisible on a light background — this was the "light animation not showing" bug).
- **Previewing**: GitHub plays the SMIL animation, but an offline still renderer shows the card blank at t=0 (reveal mask height 0, clip widths 0, boot lines opacity 0). To eyeball a given moment, strip `<animate>`/`<animateTransform>`, then force the state you want (open the mask/clip rects; for a glitch frame bake `scale="22"` on the displacement and raise the ghost opacities; for the boot frame force the `x="528"` boot texts to opacity 1), then rasterize with `@resvg/resvg-js`.

## The snake animation workflow

`.github/workflows/main.yml` uses `Platane/snk` to render the contribution graph into two SVGs, then `crazy-max/ghaction-github-pages` force-pushes `dist/` to the **`output`** branch. `README.md` references those SVGs via `raw.githubusercontent.com/.../output/...`, so the animation lives on a separate generated branch — do not commit those SVGs to the working branch.

Triggers: every 24h (cron `0 0 * * *`), manual (`workflow_dispatch`), and push to `main`.

The same workflow has a second job, **`refresh-card`**, which reinstalls Pillow, re-runs `scripts/build_profile.py`, and commits `dark.svg`/`light.svg` if they changed — keeping the card's uptime/sync-date fresh. It is gated `if: github.event_name != 'push'` so the bot's own commit doesn't re-trigger the workflow into a loop.

## README notes

- The README relies on external image services (`shields.io`, `github-readme-stats`, `github-readme-streak-stats`, `capsule-render`). Changes are visual — verify by previewing rendered Markdown.
- Any `user=`/`username=` param in the stat/snake URLs must stay as `Franklyn-R-Silva`.
