# -*- coding: utf-8 -*-
"""
Generate the terminal-style profile card (dark.svg + light.svg) from a photo.

Usage (from repo root):
    py scripts/build_profile.py

Edit the DATA dict (identity/contacts) and the CROP/COLS knobs below, then re-run.
Requires: Pillow  ->  py -m pip install pillow
"""
from PIL import Image, ImageOps, ImageEnhance
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets", "portrait.png")   # source photo
OUT_DIR = ROOT                                        # dark.svg / light.svg land here

# ---- ascii font metrics (must match the .ascii CSS emitted below) ----
FS_ASCII = 6.2
LH_ASCII = 6.2
ADV = FS_ASCII * 0.60          # monospace advance per char
COLS = 116                     # portrait width in characters (bigger = more detail)
CROP = (0.15, 0.12, 0.85, 0.67)  # cx0, cy0, cx1, cy1 as fractions of the photo
RAMP = " ..'':-~=++**cvxzsoaekw%8B#@@"   # dark -> light density ramp
BLACK_FLOOR = 42               # pixels darker than this render as empty background

# ---- identity data -----------------------------------------------------
DATA = {
    "user":  "franklyn@dev",
    "Subject":  "Franklyn Roberto",
    "Role":     "Mobile Developer · Flutter/Dart",
    "Origin":   "Arapiraca - AL, Brazil",
    "Status":   "Building • Learning • Shipping",
    "Currently":"Flutter apps · Studying iOS/Kotlin",
    "ToolChain":"VS Code, Git, Docker, Postman, Figma",
    "OpenTo":   "Freelance · Full-time · Collabs",
    "Lang":     "Dart, Java, Python, C#, TypeScript",
    "Mobile":   "Flutter, Android, React Native",
    "Frontend": "React, TypeScript, Tailwind, Astro",
    "Backend":  "Node.js, Spring, Electron",
    "Database": "PostgreSQL, MySQL, Oracle",
    "Mail":     "franklyn.dev.mobile@gmail.com",
    "Portfolio":"devfrs.com",
    "LinkedIn": "franklyn-r-silva",
    "Instagram":"@franklynrsilva",
    "WhatsApp": "+55 82 99991-5558",
    "Github":   "Franklyn-R-Silva",
}

# ---- dynamic data (recomputed on every build / daily via GitHub Actions) ----
import datetime
CODING_SINCE = datetime.date(2021, 1, 1)   # ajuste: quando você começou a codar
_today = datetime.date.today()
_days = (_today - CODING_SINCE).days
DATA["UptimeShort"] = f"up {_days}d"
SYNC = _today.strftime("%Y-%m-%d")

# ---- live streak stats, scraped from github-readme-streak-stats at build time ----
# The daily `refresh-card` CI job re-runs this, keeping the numbers fresh.
# Returns None on any network/parse failure so the build never breaks (offline/CI hiccup).
def fetch_streak(user):
    import urllib.request, re
    url = f"https://github-readme-streak-stats.herokuapp.com/?user={user}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "profile-card-build"})
        with urllib.request.urlopen(req, timeout=20) as r:
            svg = r.read().decode("utf-8", "ignore")
    except Exception:
        return None
    vals = [m.strip() for m in re.findall(r"<text[^>]*>([^<]+)</text>", svg)]
    nums = [v for v in vals if re.fullmatch(r"[\d,]+", v)]
    if len(nums) < 3:
        return None

    def num_before(label):
        if label not in vals:
            return None
        for j in range(vals.index(label) - 1, -1, -1):
            if re.fullmatch(r"[\d,]+", vals[j]):
                return vals[j]
        return None

    # current streak = the number carrying the 'currstreak' animation
    current = None
    for m in re.finditer(r"<text[^>]*>([\d,]+)</text>", svg):
        if "currstreak" in svg[max(0, m.start() - 180): m.start() + len(m.group(0))]:
            current = m.group(1)
            break
    total = num_before("Total Contributions") or nums[0]
    longest = num_before("Longest Streak") or nums[-1]
    if current is None:
        current = next((n for n in nums if n not in (total, longest)), nums[1])
    years = re.findall(r"(20\d\d)", " ".join(vals))
    since = min(years) if years else ""
    return {"total": total, "current": current, "longest": longest, "since": since}

# ---- GitHub API metrics (stars, forks, PRs, issues, followers, top languages) ----
# GH_PAT (classic, scope repo) -> includes PRIVATE repos. Else GITHUB_TOKEN (public,
# higher rate limit) or unauthenticated. Languages by code bytes when authenticated.
def fetch_github(user):
    import urllib.request, json, collections
    pat = os.environ.get("GH_PAT")
    tok = pat or os.environ.get("GITHUB_TOKEN")
    def api(path):
        h = {"User-Agent": "profile-card", "Accept": "application/vnd.github+json"}
        if tok:
            h["Authorization"] = "Bearer " + tok
        with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=h), timeout=30) as r:
            return json.load(r)
    try:
        prof = api(f"/users/{user}")
        repos = []
        for pg in (1, 2, 3, 4):
            if pat:   # authenticated as the user -> owned public + private repos
                r = api(f"/user/repos?per_page=100&page={pg}&affiliation=owner&visibility=all")
            else:
                r = api(f"/users/{user}/repos?per_page=100&page={pg}&type=owner")
            repos += r
            if len(r) < 100:
                break
        own = [x for x in repos if not x.get("fork")]
        stars = sum(x.get("stargazers_count", 0) for x in own)
        forks = sum(x.get("forks_count", 0) for x in own)
        # languages: by code bytes when authenticated (accurate, incl. private),
        # else by primary-language repo count (1 request, no per-repo calls)
        by = collections.Counter()
        if tok:
            for x in own:
                try:
                    for l, b in api(f"/repos/{x['full_name']}/languages").items():
                        by[l] += b
                except Exception:
                    if x.get("language"):
                        by[x["language"]] += 1
        else:
            for x in own:
                if x.get("language"):
                    by[x["language"]] += 1
        tot = sum(by.values()) or 1
        langs = [(l, round(b / tot * 100)) for l, b in by.most_common(5)]
        repos_count = len(own) if pat else prof.get("public_repos")
        try:
            prs = api(f"/search/issues?q=author:{user}+type:pr&per_page=1").get("total_count")
            iss = api(f"/search/issues?q=author:{user}+type:issue&per_page=1").get("total_count")
        except Exception:
            prs = iss = None
        return dict(followers=prof.get("followers"), following=prof.get("following"),
                    repos=repos_count, stars=stars, forks=forks, prs=prs, issues=iss,
                    langs=langs, private=bool(pat))
    except Exception:
        return None

# ---- WakaTime coding hours per language (optional; needs WAKATIME_API_KEY secret) ----
# Tries all-time first (sums every year) and falls back to shorter ranges if the
# account plan doesn't expose it. Returns hours per language.
def fetch_wakatime():
    import urllib.request, json, base64
    key = os.environ.get("WAKATIME_API_KEY")
    if not key:
        return None
    auth = base64.b64encode(key.encode()).decode()
    for rng, label in [("all_time", "ALL TIME"), ("last_year", "LAST YEAR"),
                       ("last_30_days", "LAST 30 DAYS"), ("last_7_days", "LAST 7 DAYS")]:
        try:
            url = f"https://wakatime.com/api/v1/users/current/stats/{rng}"
            req = urllib.request.Request(url, headers={"Authorization": "Basic " + auth})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.load(r)["data"]
        except Exception:
            continue
        langs = []
        for l in data.get("languages", []):
            if l["name"].lower() == "other":
                continue
            h, m = int(l.get("hours", 0)), int(l.get("minutes", 0))
            short = f"{h}h{m:02d}m" if h else f"{m}m"
            langs.append((l["name"], short, round(l.get("percent", 0))))
            if len(langs) >= 5:
                break
        if langs:
            return dict(total=data.get("human_readable_total", ""), langs=langs, range=label)
    return None

STREAK = fetch_streak(DATA["Github"])
GH = fetch_github(DATA["Github"])
WAKA = fetch_wakatime()

# ------------------------------------------------------------------ ascii
def gen_ascii():
    base = Image.open(SRC).convert("L")
    W, H = base.size
    cx0, cy0, cx1, cy1 = CROP
    crop = base.crop((int(cx0*W), int(cy0*H), int(cx1*W), int(cy1*H)))
    crop = ImageOps.autocontrast(crop, cutoff=1)
    crop = ImageEnhance.Contrast(crop).enhance(1.35)
    crop = ImageEnhance.Brightness(crop).enhance(1.12)
    crop = crop.point(lambda v: 0 if v < BLACK_FLOOR else v)
    aspect = crop.size[0] / crop.size[1]
    rows = round(COLS * ADV / (LH_ASCII * aspect))
    small = crop.resize((COLS, rows), Image.LANCZOS)
    px = small.load()
    n = len(RAMP)
    return ["".join(RAMP[min(n-1, int(px[x, y]/256*n))] for x in range(COLS))
            for y in range(rows)]

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ------------------------------------------------------------------ layout
L_X, L_Y, L_W, L_H = 14, 26, 488, 479      # top-left panel (VISUAL.MAP)
R_X, R_Y, R_W, R_H = 508, 10, 655, 495     # top-right panel (SYSTEM.INFO)
M_X, M_Y, M_W, M_H = 14, 532, 1149, 184    # 3rd card (SYSTEM.METRICS), full width
CANVAS_H = 38 + M_Y + M_H + 14             # dynamic overall canvas height

LINES = [
    ("head", DATA["user"]),
    ("kv",  "Subject",  DATA["Subject"]),
    ("kv",  "Role",     DATA["Role"]),
    ("kv",  "Origin",   DATA["Origin"]),
    ("kv",  "Status",   DATA["Status"]),
    ("kv",  "Currently",DATA["Currently"]),
    ("kv",  "ToolChain",DATA["ToolChain"]),
    ("blank",),
    ("kv2", "Core", "Lang",     DATA["Lang"]),
    ("kv2", "Core", "Mobile",   DATA["Mobile"]),
    ("kv2", "Core", "Frontend", DATA["Frontend"]),
    ("kv2", "Core", "Backend",  DATA["Backend"]),
    ("kv2", "Core", "Database", DATA["Database"]),
    ("blank",),
    ("kv2", "Open", "To",       DATA["OpenTo"]),
    ("blank",),
    ("sec", "Contact"),
    ("kv2", "Grid", "Mail",      DATA["Mail"]),
    ("kv2", "Grid", "Portfolio", DATA["Portfolio"]),
    ("kv2", "Grid", "LinkedIn",  DATA["LinkedIn"]),
    ("kv2", "Grid", "Instagram", DATA["Instagram"]),
    ("kv2", "Grid", "WhatsApp",  DATA["WhatsApp"]),
    ("kv2", "Grid", "Github",    DATA["Github"]),
]

VALUE_COL = 33
TX, TY0, TSTEP = 520, 40, 19

def build_line_tspans(kind, parts, y):
    if kind == "head":
        dash = " -" + "—"*30 + "-—-"
        return (f'<tspan x="{TX}" y="{y}" class="head">{esc(parts[0])}</tspan>'
                f'<tspan class="cc">  ·  </tspan>'
                f'<tspan class="accent">{esc(DATA["UptimeShort"])}</tspan>'
                f'<tspan class="cc">{dash}</tspan>')
    if kind == "sec":
        dash = " -" + "—"*44 + "-—-"
        return (f'<tspan x="{TX}" y="{y}" class="accent">- {esc(parts[0])}</tspan>'
                f'<tspan class="cc">{dash}</tspan>')
    if kind == "sec2":
        dash = " -" + "—"*28 + "-—-"
        return (f'<tspan x="{TX}" y="{y}" class="accent">- {esc(parts[0])}</tspan>'
                f'<tspan class="cc">  ·  </tspan>'
                f'<tspan class="value">{esc(parts[1])}</tspan>'
                f'<tspan class="cc">{dash}</tspan>')
    if kind == "blank":
        return f'<tspan x="{TX}" y="{y}" class="cc">. </tspan>'
    if kind == "txt":
        return (f'<tspan x="{TX}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="value">{esc(parts[0])}</tspan>')
    if kind == "kv":
        label, value = parts
        dots = "." * max(3, VALUE_COL - (2 + len(label) + 2) - 1)
        return (f'<tspan x="{TX}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="key">{esc(label)}</tspan>'
                f'<tspan class="cc">: {dots} </tspan>'
                f'<tspan class="value">{esc(value)}</tspan>')
    if kind == "kv2":
        a, b, value = parts
        dots = "." * max(3, VALUE_COL - (2 + len(a) + 1 + len(b) + 2) - 1)
        return (f'<tspan x="{TX}" y="{y}" class="cc">. </tspan>'
                f'<tspan class="key">{esc(a)}</tspan><tspan class="cc">.</tspan>'
                f'<tspan class="key">{esc(b)}</tspan>'
                f'<tspan class="cc">: {dots} </tspan>'
                f'<tspan class="value">{esc(value)}</tspan>')
    return ""

# ------------------------------------------------------------------ palette
PALETTES = {
    "dark": dict(
        bg0="#0B1120", bg1="#050816",
        g1="#22D3EE", g2="#7C3AED", g3="#38BDF8",
        b1="#7C3AED", b2="#22D3EE", b3="#10B981",
        key="#22D3EE", value="#E5E7EB", cc="#475569", head="#7C3AED",
        accent="#10B981", term="#64748B", scan="#F87171",
        ptitle="#38BDF8", scanfill="#22D3EE", scanhi="#A5F3FC",
        scanlo="#7C3AED", scanline="#7DD3FC", titlebar="#0B1120",
        scanblend="screen", scanop="0.75", glow="1.5", asciiglow="1.1",
        ghost1="#FF2E63", ghost2="#22D3EE", ghostblend="screen"),
    "light": dict(   # monochrome: black on light (no purple/lilac/blue)
        bg0="#F1F5F9", bg1="#E2E8F0",
        g1="#0F172A", g2="#475569", g3="#000000",
        b1="#0F172A", b2="#000000", b3="#334155",
        key="#000000", value="#111827", cc="#94A3B8", head="#000000",
        accent="#000000", term="#475569", scan="#DC2626",
        ptitle="#334155", scanfill="#334155", scanhi="#0F172A",
        scanlo="#334155", scanline="#CBD5E1", titlebar="#F8FAFC",
        scanblend="multiply", scanop="0.55", glow="0.7", asciiglow="0.5",
        ghost1="#334155", ghost2="#475569", ghostblend="multiply"),
}

def render_metrics(p, begin):
    """3rd full-width card: SYSTEM.METRICS dashboard (auto-fetched numbers)."""
    if not (STREAK or GH):
        return ""
    RS = 20
    hy = M_Y + 56        # column header baseline
    ry0 = M_Y + 80       # first data row baseline

    def column(x, header, rows, field=11):
        out = [f'<text x="{x}" y="{hy}" class="mhead">{esc(header)}</text>']
        for k, (lab, val) in enumerate(rows):
            dots = "." * max(2, field - len(lab))
            out.append(
                f'<text x="{x}" y="{ry0 + k*RS}"><tspan class="mkey">{esc(lab)}</tspan>'
                f'<tspan class="mcc"> {dots} </tspan><tspan class="mval">{esc(str(val))}</tspan></text>')
        return "".join(out)

    cols = []
    if STREAK:
        cols.append(column(40, "CONTRIBUTIONS", [
            ("total", STREAK["total"]), ("current", f'{STREAK["current"]}d'),
            ("longest", f'{STREAK["longest"]}d'), ("since", STREAK["since"])]))
    if GH:
        cols.append(column(340, "IMPACT", [
            ("stars", GH["stars"]), ("forks", GH["forks"]),
            ("pull reqs", "—" if GH["prs"] is None else GH["prs"]),
            ("issues", "—" if GH["issues"] is None else GH["issues"])]))
        cols.append(column(630, "NETWORK", [
            ("followers", GH["followers"]), ("following", GH["following"]),
            ("repos", GH["repos"])]))
    # LANGUAGES column: prefer WakaTime hours (real coding time, incl. private repos);
    # fall back to GitHub repo languages (%) when WakaTime isn't configured.
    lang = ""
    if WAKA and WAKA.get("langs"):
        hdr = f'LANGUAGES · {WAKA.get("range", "")}'.strip(" ·")
        lang = f'<text x="880" y="{hy}" class="mhead">{esc(hdr)}</text>'
        for k, (name, short, pct) in enumerate(WAKA["langs"][:5]):
            bar = "█" * min(14, max(1, round(pct / 3.5)))
            lab = name[:11].ljust(12)
            lang += (f'<text x="880" y="{ry0 + k*RS}"><tspan class="mkey">{esc(lab)}</tspan>'
                     f'<tspan class="mbar">{bar}</tspan><tspan class="mval"> {esc(short)}</tspan></text>')
    elif GH and GH["langs"]:
        lang = f'<text x="880" y="{hy}" class="mhead">LANGUAGES</text>'
        for k, (name, pct) in enumerate(GH["langs"]):
            bar = "█" * min(16, max(1, round(pct / 3.5)))
            lab = name[:11].ljust(12)
            lang += (f'<text x="880" y="{ry0 + k*RS}"><tspan class="mkey">{esc(lab)}</tspan>'
                     f'<tspan class="mbar">{bar}</tspan><tspan class="mval"> {pct}%</tspan></text>')
    waka = ""
    # optional grand-total coding time line at the bottom of the panel
    if WAKA and WAKA.get("total"):
        waka = (f'<text x="40" y="{M_Y + M_H - 16}"><tspan class="mhead">CODE TIME · {esc(WAKA.get("range",""))}  </tspan>'
                f'<tspan class="mval">{esc(WAKA["total"])} total tracked</tspan></text>')

    return (
        f'<g opacity="0">'
        f'<rect x="{M_X}" y="{M_Y}" width="{M_W}" height="{M_H}" rx="14" fill="{p["bg0"]}" '
        f'fill-opacity="0.35" stroke="url(#borderGrad)" stroke-width="1" opacity="0.35"/>'
        f'<text x="{M_X + 20}" y="{M_Y + 26}" class="panel-title">SYSTEM.METRICS</text>'
        f'<text x="{M_X + M_W - 20}" y="{M_Y + 26}" text-anchor="end" class="mcc">synced {SYNC}</text>'
        f'{"".join(cols)}{lang}{waka}'
        f'<animate attributeName="opacity" values="0;1" dur="0.7s" begin="{begin:.2f}s" fill="freeze"/>'
        f'</g>')

def build_svg(theme, ascii_lines):
    p = PALETTES[theme]
    rows = len(ascii_lines)
    block_h = rows * LH_ASCII
    block_w = COLS * ADV
    ax = L_X + (L_W - block_w) / 2 + 4
    ay0 = L_Y + (L_H - block_h) / 2 + FS_ASCII
    reveal_to = block_h + 30

    at = [f'<tspan x="{ax:.1f}" y="{ay0 + i*LH_ASCII:.2f}" xml:space="preserve">{esc(line)}</tspan>'
          for i, line in enumerate(ascii_lines)]
    ascii_block = "\n".join(at)

    # --- boot intro sequence (types first, then fades; info reveals after) ---
    BOOT_END = 2.55
    reveal_begin = BOOT_END - 0.25
    boot_lines = [
        ("> booting devOS v4.8", "value"),
        ("> mounting /home/franklyn/identity", "value"),
        ("> decrypting profile ........ ", "value", "OK", "accent"),
        ("> access granted", "accent"),
    ]
    boot_items = []
    for j, bl in enumerate(boot_lines):
        by = 70 + j * 26
        b_open = 0.25 + j * 0.5
        seg = f'<tspan class="{bl[1]}" style="font-size:14px">{esc(bl[0])}</tspan>'
        if len(bl) > 2:
            seg += f'<tspan class="{bl[3]}" style="font-size:14px">{esc(bl[2])}</tspan>'
        boot_items.append(
            f'<text x="528" y="{by}" opacity="0">{seg}'
            f'<animate attributeName="opacity" values="0;1" dur="0.18s" begin="{b_open:.2f}s" fill="freeze"/></text>')
    boot_svg = (f'<g id="boot" filter="url(#softGlow)">'
                + "".join(boot_items)
                + f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;0.85;1" '
                  f'dur="{BOOT_END:.2f}s" fill="freeze"/></g>')

    clips, texts = [], []
    for i, spec in enumerate(LINES):
        y = TY0 + i * TSTEP
        begin = BOOT_END + i * 0.10
        clips.append(
            f'<clipPath id="lc{i}"><rect x="500" y="{y-16}" width="0" height="24">'
            f'<animate attributeName="width" from="0" to="690" dur="0.34s" '
            f'begin="{begin:.2f}s" fill="freeze"/></rect></clipPath>')
        inner = build_line_tspans(spec[0], spec[1:], y)
        flt = ' filter="url(#softGlow)"' if spec[0] in ("head", "sec", "sec2") else ""
        texts.append(f'<g clip-path="url(#lc{i})"><text x="{TX}" y="0" fill="{p["value"]}"{flt}>{inner}</text></g>')
    clips_s = "".join(clips)
    texts_s = "\n".join(texts)

    # --- RGB chromatic-aberration ghosts on the name (flash during glitch) ---
    gy = TY0
    ghost_op = 'values="0;0;0.65;0;0.5;0;0" keyTimes="0;0.71;0.735;0.76;0.8;0.84;1" dur="7s" repeatCount="indefinite"'
    ghost_style = "font-family:'Courier New',Consolas,monospace;font-size:17px;font-weight:bold"
    ghosts = (
        f'<g style="mix-blend-mode:{p["ghostblend"]}">'
        f'<text x="{TX-4}" y="{gy}" style="{ghost_style};fill:{p["ghost1"]}" opacity="0">{esc(DATA["user"])}'
        f'<animate attributeName="opacity" {ghost_op}/></text>'
        f'<text x="{TX+4}" y="{gy}" style="{ghost_style};fill:{p["ghost2"]}" opacity="0">{esc(DATA["user"])}'
        f'<animate attributeName="opacity" {ghost_op}/></text></g>')

    cursor_y = TY0 + (len(LINES)-2) * TSTEP - 15
    cursor_begin = BOOT_END + len(LINES) * 0.10
    metrics_svg = render_metrics(p, BOOT_END + len(LINES) * 0.10 + 0.2)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="{CANVAS_H}" viewBox="0 0 1180 {CANVAS_H}">
<defs>
  <linearGradient id="asciiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="{p['g1']}"><animate attributeName="stop-color" values="{p['g1']};{p['g2']};{p['g3']};{p['g1']}" dur="9s" repeatCount="indefinite"/></stop>
    <stop offset="100%" stop-color="{p['g2']}"><animate attributeName="stop-color" values="{p['g2']};{p['g3']};{p['g1']};{p['g2']}" dur="9s" repeatCount="indefinite"/></stop>
  </linearGradient>
  <linearGradient id="borderGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="{p['b1']}"/><stop offset="50%" stop-color="{p['b2']}"/><stop offset="100%" stop-color="{p['b3']}"/>
  </linearGradient>
  <radialGradient id="bgGlow" cx="30%" cy="20%" r="80%">
    <stop offset="0%" stop-color="{p['bg0']}"/><stop offset="100%" stop-color="{p['bg1']}"/>
  </radialGradient>
  <linearGradient id="scanGrad" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="{p['scanfill']}" stop-opacity="0"/>
    <stop offset="45%" stop-color="{p['scanfill']}" stop-opacity="0.05"/>
    <stop offset="50%" stop-color="{p['scanhi']}" stop-opacity="0.65"/>
    <stop offset="55%" stop-color="{p['scanfill']}" stop-opacity="0.05"/>
    <stop offset="100%" stop-color="{p['scanlo']}" stop-opacity="0"/>
  </linearGradient>
  <pattern id="scanlines" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="{p['scanline']}" opacity="0.05"/>
  </pattern>
  <filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="{p['glow']}" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="asciiGlow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="{p['asciiglow']}" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="glitch" x="-6%" y="-3%" width="112%" height="106%">
    <feTurbulence type="fractalNoise" baseFrequency="0.00001 0.4" numOctaves="1" seed="4" result="noise">
      <animate attributeName="seed" values="4;19;7;23;11;4" keyTimes="0;0.71;0.75;0.8;0.86;1" dur="7s" calcMode="discrete" repeatCount="indefinite"/>
    </feTurbulence>
    <feDisplacementMap in="SourceGraphic" in2="noise" xChannelSelector="R" yChannelSelector="G" scale="0" result="disp">
      <animate attributeName="scale" values="0;0;22;3;14;0;0" keyTimes="0;0.71;0.735;0.76;0.8;0.84;1" dur="7s" repeatCount="indefinite"/>
    </feDisplacementMap>
  </filter>
  <mask id="revealMask" maskUnits="userSpaceOnUse" x="0" y="0" width="1180" height="{CANVAS_H + 10}">
    <rect x="0" y="0" width="1180" height="0" fill="#fff">
      <animate attributeName="height" from="0" to="{reveal_to:.0f}" dur="2.4s" begin="{reveal_begin:.2f}s" fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>
    </rect>
  </mask>
  {clips_s}
  <style>
    .ascii  {{ font-family: 'Courier New', Consolas, monospace; font-size: {FS_ASCII}px; fill: url(#asciiGrad); letter-spacing: 0px; }}
    .key    {{ font-family: 'Courier New', Consolas, monospace; font-size: 15px; fill: {p['key']}; font-weight: bold; }}
    .value  {{ font-family: 'Courier New', Consolas, monospace; font-size: 15px; fill: {p['value']}; }}
    .cc     {{ font-family: 'Courier New', Consolas, monospace; font-size: 15px; fill: {p['cc']}; }}
    .head   {{ font-family: 'Courier New', Consolas, monospace; font-size: 17px; fill: {p['head']}; font-weight: bold; }}
    .accent {{ font-family: 'Courier New', Consolas, monospace; font-size: 15px; fill: {p['accent']}; font-weight: bold; }}
    text, tspan {{ white-space: pre; }}
    .term-label {{ font-family: 'Courier New', Consolas, monospace; font-size: 12px; fill: {p['term']}; letter-spacing: 0.5px; }}
    .scan-label {{ font-family: 'Courier New', Consolas, monospace; font-size: 10px; fill: {p['scan']}; letter-spacing: 1px; }}
    .panel-title {{ font-family: 'Courier New', Consolas, monospace; font-size: 11px; fill: {p['ptitle']}; letter-spacing: 2px; opacity: 0.7; }}
    .cursor-blink {{ fill: {p['scanfill']}; }}
    .mhead {{ font-family: 'Courier New', Consolas, monospace; font-size: 11px; fill: {p['accent']}; font-weight: bold; letter-spacing: 1.5px; }}
    .mkey  {{ font-family: 'Courier New', Consolas, monospace; font-size: 13px; fill: {p['key']}; font-weight: bold; }}
    .mcc   {{ font-family: 'Courier New', Consolas, monospace; font-size: 13px; fill: {p['cc']}; }}
    .mval  {{ font-family: 'Courier New', Consolas, monospace; font-size: 13px; fill: {p['value']}; }}
    .mbar  {{ font-family: 'Courier New', Consolas, monospace; font-size: 13px; fill: url(#asciiGrad); }}
  </style>
</defs>

<rect width="1180" height="{CANVAS_H}" rx="18" fill="url(#bgGlow)"/>
<rect width="1180" height="{CANVAS_H}" rx="18" fill="url(#scanlines)"/>

<g filter="url(#glitch)">
<g id="titlebar">
  <rect x="3" y="3" width="1174" height="34" rx="16" fill="{p['titlebar']}" fill-opacity="0.85"/>
  <circle cx="24" cy="20" r="5" fill="#EF4444"><animate attributeName="opacity" values="1;0.55;1" dur="4s" repeatCount="indefinite"/></circle>
  <circle cx="42" cy="20" r="5" fill="#F59E0B"><animate attributeName="opacity" values="1;0.55;1" dur="4s" begin="0.3s" repeatCount="indefinite"/></circle>
  <circle cx="60" cy="20" r="5" fill="#10B981"><animate attributeName="opacity" values="1;0.55;1" dur="4s" begin="0.6s" repeatCount="indefinite"/></circle>
  <text x="590" y="25" text-anchor="middle" class="term-label">{esc(DATA["user"])} ~ % ./profile.sh --live</text>
  <circle cx="1082" cy="20" r="4" fill="{p['scan']}"><animate attributeName="opacity" values="1;0.15;1" dur="1.1s" repeatCount="indefinite"/></circle>
  <text x="1092" y="24" class="scan-label">SCANNING</text>
</g>

<g transform="translate(0,38)">
  <rect x="{L_X}" y="{L_Y}" width="{L_W}" height="{L_H}" rx="14" fill="{p['bg0']}" fill-opacity="0.35" stroke="url(#borderGrad)" stroke-width="1" opacity="0.35"/>
  <rect x="{R_X}" y="{R_Y}" width="{R_W}" height="{R_H}" rx="14" fill="{p['bg0']}" fill-opacity="0.35" stroke="url(#borderGrad)" stroke-width="1" opacity="0.35"/>
  <text x="30" y="24" class="panel-title">VISUAL.MAP</text>
  <text x="524" y="24" class="panel-title">SYSTEM.INFO</text>

  <g mask="url(#revealMask)">
  <text class="ascii" filter="url(#asciiGlow)">
{ascii_block}
  <animate attributeName="opacity" values="0.88;1;0.93;1;0.9" dur="3.8s" begin="2.4s" repeatCount="indefinite"/>
  </text>
  </g>

  {texts_s}

  {ghosts}

  {boot_svg}

  <rect x="522" y="{cursor_y}" width="9" height="16" class="cursor-blink" opacity="0">
    <animate attributeName="opacity" values="0;0;1;0;1;0;1;0" keyTimes="0;0.01;0.02;0.3;0.5;0.7;0.85;1" dur="1.4s" begin="{cursor_begin:.2f}s" repeatCount="indefinite"/>
  </rect>

  {metrics_svg}
</g>
</g>

<!-- glitch tear band: flashes and jumps during the glitch burst -->
<rect x="0" width="1180" height="7" y="200" fill="{p['scanhi']}" opacity="0" style="mix-blend-mode:{p['scanblend']}">
  <animate attributeName="opacity" values="0;0;0.55;0.1;0.4;0" keyTimes="0;0.71;0.735;0.76;0.8;0.85" dur="7s" repeatCount="indefinite"/>
  <animate attributeName="y" values="210;210;150;330;110;110" keyTimes="0;0.71;0.735;0.76;0.8;1" dur="7s" calcMode="discrete" repeatCount="indefinite"/>
  <animate attributeName="height" values="7;7;5;14;3;7" keyTimes="0;0.71;0.735;0.76;0.8;1" dur="7s" calcMode="discrete" repeatCount="indefinite"/>
</rect>

<rect x="0" y="-90" width="1180" height="90" fill="url(#scanGrad)" opacity="{p['scanop']}" style="mix-blend-mode:{p['scanblend']}">
  <animateTransform attributeName="transform" type="translate" from="0 -90" to="0 {CANVAS_H + 90}" dur="4.6s" repeatCount="indefinite"/>
</rect>

<rect x="3" y="3" width="1174" height="{CANVAS_H - 6}" rx="16" fill="none" stroke="url(#borderGrad)" stroke-width="2" opacity="0.8">
  <animate attributeName="opacity" values="0.5;0.95;0.5" dur="3.2s" repeatCount="indefinite"/>
</rect>
</svg>
'''

def main():
    ascii_lines = gen_ascii()
    for theme in ("dark", "light"):
        svg = build_svg(theme, ascii_lines)
        with open(os.path.join(OUT_DIR, f"{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {theme}.svg  (ascii rows={len(ascii_lines)})")

if __name__ == "__main__":
    main()
