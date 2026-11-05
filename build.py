#!/usr/bin/env python3
"""Generiert index.html aus den Projekt-Gutenberg-Texten (Band 1 & 2).

Quelle: https://www.gutenberg.org/ebooks/2407 und /2408
Die Rohtexte werden erwartet unter sources/band1.txt und sources/band2.txt
"""
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
SRC1 = ROOT / "sources" / "band1.txt"
SRC2 = ROOT / "sources" / "band2.txt"
MOODS = ROOT / "moods.json"
OUT = ROOT / "index.html"

SECTION_HEADINGS = {"Erstes Buch", "Zweites Buch", "Der Herausgeber an den Leser"}
DATE_RE = re.compile(r"^(Am|Den) \d+\. [A-ZÄÖÜ][a-zäöü]+( 17\d\d)?$")
EXTRA_HEADINGS = {"Nach Eilfe"}

# Absätze, mit denen die Herausgeber-Erzählung einen Brief/Zettel beendet
CLOSE_LETTER_STARTS = ("Ein Nachbar sah den Blick vom Pulver",)
DROP_PARA_STARTS = ("Ende dieses Projekt Gutenberg",)

MONTHS = {"Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5,
          "Juni": 6, "Junius": 6, "Juli": 7, "Julius": 7, "August": 8,
          "September": 9, "Oktober": 10, "November": 11, "Dezember": 12}

# Stimmungsskala −5 … +5: sonniges Gelb → entsättigt → dunkles Blau → fast Schwarz
# Positive Stufen bewusst hell/gesättigt, damit (hypo)manische Hochs deutlich leuchten
SCORE_COLORS = {
    5: "#ffd93b", 4: "#fbcb38", 3: "#f4ba3c", 2: "#eaa83f", 1: "#d49a48",
    0: "#a3906b",
    -1: "#6f7a82", -2: "#5d6a7e", -3: "#475573", -4: "#2e3a55", -5: "#15171d",
}


def score_text(s: int) -> str:
    return f"+{s}" if s > 0 else ("±0" if s == 0 else f"\u2212{abs(s)}")

VORREDE = (
    "Was ich von der Geschichte des armen Werther nur habe auffinden können, "
    "habe ich mit Fleiß gesammelt und lege es euch hier vor, und weiß, daß ihr "
    "mir's danken werdet. Ihr könnt seinem Geist und seinem Charakter eure "
    "Bewunderung und Liebe, seinem Schicksale eure Tränen nicht versagen.\n"
    "Und du gute Seele, die du eben den Drang fühlst wie er, schöpfe Trost aus "
    "seinem Leiden, und laß das Büchlein deinen Freund sein, wenn du aus "
    "Geschick oder eigener Schuld keinen näheren finden kannst."
)


def strip_gutenberg(raw: str) -> str:
    start = raw.index("***", raw.index("*** START OF")) + 3
    start = raw.index("***", start) + 3
    end = raw.index("*** END OF")
    return raw[start:end]


def clean_body(text: str) -> str:
    # Titelzeilen der Hamburger Ausgabe am Anfang entfernen
    lines = text.splitlines()
    out = []
    skipping_head = True
    for line in lines:
        s = line.strip()
        if skipping_head:
            if s in SECTION_HEADINGS:
                skipping_head = False
            else:
                continue
        out.append(line.rstrip())
    return "\n".join(out)


def parse_blocks(text: str):
    """Liefert Liste von (kind, content)-Tupeln.
    kind: 'book' | 'date' | 'para'
    """
    blocks = []
    para: list[str] = []

    def flush():
        nonlocal para
        if para:
            blocks.append(("para", " ".join(para)))
            para = []

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
            continue
        if s in SECTION_HEADINGS:
            flush()
            blocks.append(("book", s))
        elif DATE_RE.match(s) or s in EXTRA_HEADINGS:
            flush()
            blocks.append(("date", s))
        else:
            para.append(re.sub(r"\s+", " ", s))
    flush()
    return blocks


def typographize(s: str) -> str:
    s = html.escape(s, quote=False)
    s = s.replace("--", "\u2014")  # Geviertstrich
    # Anführungszeichen: gerade " paarweise in „ … “ umwandeln
    result = []
    open_q = False
    for ch in s:
        if ch == '"':
            result.append("\u201e" if not open_q else "\u201c")
            open_q = not open_q
        else:
            result.append(ch)
    return "".join(result)


def render(blocks, moods):
    """Liefert (html, letters); letters = (anchor_id, date, tooltip, mood-dict)."""
    out = []
    letters = []
    letter_open = False
    letter_count = 0
    current_year = 1771
    prev_month = None

    def close_letter():
        nonlocal letter_open
        if letter_open:
            out.append("    </article>")
            letter_open = False

    for kind, content in blocks:
        if kind == "book":
            close_letter()
            slug = {
                "Erstes Buch": "erstes-buch",
                "Zweites Buch": "zweites-buch",
                "Der Herausgeber an den Leser": "herausgeber",
            }[content]
            out.append(f'    <h2 class="book-heading" id="{slug}"><span>{content}</span></h2>')
        elif kind == "date":
            close_letter()
            letter_count += 1
            anchor = f"brief-{letter_count}"
            mood = moods[letter_count - 1]
            m = re.match(r"^(?:Am|Den) (\d+)\. ([A-ZÄÖÜ][a-zäöü]+)(?: (17\d\d))?$", content)
            if m:
                day, monthname, year = int(m.group(1)), m.group(2), m.group(3)
                month = MONTHS[monthname]
                if year:
                    current_year = int(year)
                elif prev_month is not None and month < prev_month:
                    current_year += 1
                prev_month = month
                letters.append((anchor, date(current_year, month, day),
                                f"{day}. {monthname} {current_year}", mood))
            elif content == "Nach Eilfe":
                # Werthers letzter Zettel, Nacht des 22. Dezember 1772
                letters.append((anchor, date(1772, 12, 22),
                                "Nach Eilfe (22. Dezember 1772)", mood))
            assert mood["date"] == letters[-1][2], \
                f"moods.json passt nicht: Brief {letter_count} ist {letters[-1][2]!r}, erwartet {mood['date']!r}"
            color = SCORE_COLORS[mood["score"]]
            out.append(f'    <article class="letter" id="{anchor}">')
            out.append(f'      <h3 class="letter-date">{typographize(content)}</h3>')
            out.append(f'      <span class="mood-badge" style="--mood:{color}">'
                       f'{mood["word"]}&nbsp;&middot;&nbsp;{score_text(mood["score"])}</span>')
            letter_open = True
        else:  # para
            if content.startswith(DROP_PARA_STARTS):
                continue
            if content.startswith(CLOSE_LETTER_STARTS):
                close_letter()
            indent = "      " if letter_open else "    "
            cls = "" if letter_open else ' class="narration"'
            out.append(f"{indent}<p{cls}>{typographize(content)}</p>")
    close_letter()
    return "\n".join(out), letters


MONTH_ABBR = {1: "Jan", 2: "Feb", 3: "Mär", 4: "Apr", 5: "Mai", 6: "Jun",
              7: "Jul", 8: "Aug", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dez"}


def render_timeline(letters) -> str:
    """Vertikaler Zeitstrahl: Monatsraster + ein Marker pro Brief."""
    first = min(d for _, d, _, _ in letters)
    last = max(d for _, d, _, _ in letters)
    span = (last - first).days

    def pct(d: date) -> float:
        return (d - first).days / span * 100

    out = []
    # Monatsraster: Tick je Monat, Beschriftung jeden 2. Monat, Jahr am Jahresanfang
    y, m = first.year, first.month
    idx = 0
    while (y, m) <= (last.year, last.month):
        d = max(date(y, m, 1), first)
        p = pct(d)
        out.append(f'      <span class="tl-tick" style="top:{p:.2f}%"></span>')
        if m == 1 or idx == 0:
            label = MONTH_ABBR[m] if idx == 0 else ""
            out.append(f'      <span class="tl-year" style="top:{p:.2f}%">{y}</span>')
            if label:
                out.append(f'      <span class="tl-month" style="top:{p:.2f}%">{label}</span>')
        elif idx % 2 == 0:
            out.append(f'      <span class="tl-month" style="top:{p:.2f}%">{MONTH_ABBR[m]}</span>')
        idx += 1
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    # Briefmarker, bei dichten Clustern minimal nach unten ausweichen
    last_p = -10.0
    for anchor, d, tooltip, mood in letters:
        p = max(pct(d), last_p + 0.55)
        last_p = p
        color = SCORE_COLORS[mood["score"]]
        out.append(
            f'      <a class="tl-mark" href="#{anchor}" style="top:{p:.2f}%;--mood:{color}" '
            f'aria-label="Brief vom {tooltip}"><span class="tl-tip">{tooltip}'
            f'<em class="tip-mood"> &middot; {mood["word"]}</em></span></a>'
        )
    return "\n".join(out)


def main():
    parts = []
    for src in (SRC1, SRC2):
        body = clean_body(strip_gutenberg(src.read_text(encoding="utf-8")))
        parts.append(body)
    blocks = parse_blocks("\n\n".join(parts))
    moods = json.loads(MOODS.read_text(encoding="utf-8"))
    n_dates = sum(1 for k, _ in blocks if k == "date")
    assert len(moods) == n_dates, f"moods.json hat {len(moods)} Einträge, Text hat {n_dates} Briefe"
    body_html, letters = render(blocks, moods)
    timeline_html = render_timeline(letters)

    vorrede_html = "\n".join(
        f"        <p>{typographize(p)}</p>" for p in VORREDE.split("\n")
    )

    page = (TEMPLATE
            .replace("{{VORREDE}}", vorrede_html)
            .replace("{{TIMELINE}}", timeline_html)
            .replace("{{BODY}}", body_html))
    OUT.write_text(page, encoding="utf-8")
    n_letters = sum(1 for k, _ in blocks if k == "date")
    print(f"index.html geschrieben: {len(page)//1024} KB, {n_letters} Briefe/Einträge, "
          f"{len(letters)} Zeitstrahl-Marker ({letters[0][1]} bis {letters[-1][1]})")


TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Die Leiden des jungen Werther · J. W. Goethe</title>
<meta name="description" content="Johann Wolfgang von Goethe: Die Leiden des jungen Werther – Volltext des Briefromans von 1774.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Grenze+Gotisch:wght@400;600&family=Dancing+Script:wght@500;600&display=swap" rel="stylesheet">
<link rel="alternate" type="application/atom+xml" title="Werther schreibt – Zyklus A" href="feed-a.xml">
<link rel="alternate" type="application/atom+xml" title="Werther schreibt – Zyklus B" href="feed-b.xml">
<style>
  :root {
    --paper: #f7f2e7;
    --paper-deep: #efe7d3;
    --ink: #3a3328;
    --ink-soft: #6b6152;
    --werther-blau: #39567c;
    --werther-blau-hell: #c9d6e6;
    --werther-gelb: #d9a62e;
    --werther-gelb-hell: #f3e3b8;
    --line: #d8cdb4;
  }

  * { box-sizing: border-box; }

  html { scroll-behavior: smooth; }

  [id] { scroll-margin-top: 5rem; }

  body {
    margin: 0;
    background: var(--paper);
    background-image:
      radial-gradient(ellipse at top, rgba(255,255,255,.55), transparent 60%),
      repeating-linear-gradient(0deg, transparent 0 2px, rgba(120,100,60,.016) 2px 4px);
    color: var(--ink);
    font-family: "EB Garamond", Garamond, Georgia, serif;
    font-size: 1.22rem;
    line-height: 1.68;
  }

  /* ---------- Navigation ---------- */
  nav.topbar {
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    padding: .55rem 1.4rem;
    background: rgba(57, 86, 124, .96);
    color: var(--paper);
    box-shadow: 0 2px 10px rgba(50, 42, 24, .25);
    border-bottom: 3px solid var(--werther-gelb);
    backdrop-filter: blur(4px);
  }
  nav.topbar .brand {
    font-family: "Grenze Gotisch", "EB Garamond", serif;
    font-size: 1.35rem;
    letter-spacing: .02em;
    color: var(--werther-gelb-hell);
    text-decoration: none;
    white-space: nowrap;
  }
  nav.topbar .brand .seal {
    display: inline-block;
    margin-right: .5rem;
    transform: translateY(2px);
  }
  nav.topbar ul {
    display: flex;
    gap: 1.2rem;
    margin: 0 0 0 auto;
    padding: 0;
    list-style: none;
    align-items: center;
  }
  nav.topbar a.navlink,
  nav.topbar button.navlink {
    color: var(--paper);
    background: none;
    border: none;
    cursor: pointer;
    font-family: inherit;
    text-decoration: none;
    font-variant: small-caps;
    letter-spacing: .08em;
    font-size: 1.05rem;
    padding: .2rem .55rem;
    border-radius: 3px;
    border-bottom: 2px solid transparent;
    transition: border-color .2s, background .2s;
  }
  nav.topbar a.navlink:hover,
  nav.topbar button.navlink:hover,
  nav.topbar a.navlink.active {
    border-bottom-color: var(--werther-gelb);
    background: rgba(255,255,255,.08);
  }
  nav.topbar button.navlink::before {
    content: "";
    display: inline-block;
    width: .62em;
    height: .62em;
    margin-right: .45em;
    border-radius: 50%;
    border: 1.5px solid var(--werther-gelb-hell);
    background: transparent;
    transform: translateY(.02em);
    transition: background .2s;
  }
  nav.topbar button.navlink[aria-pressed="true"] {
    border-bottom-color: var(--werther-gelb);
  }
  nav.topbar button.navlink[aria-pressed="true"]::before {
    background: linear-gradient(135deg, var(--werther-gelb) 50%, #2e3a55 50%);
    border-color: var(--werther-gelb);
  }

  /* ---------- Kopf ---------- */
  header.hero {
    max-width: 44rem;
    margin: 0 auto;
    padding: 4.5rem 1.5rem 2.5rem;
    text-align: center;
  }
  header.hero .ornament {
    color: var(--werther-gelb);
    font-size: 1.4rem;
    letter-spacing: .6em;
    margin-bottom: 1rem;
  }
  header.hero h1 {
    font-family: "Grenze Gotisch", serif;
    font-weight: 600;
    font-size: clamp(2.4rem, 6vw, 3.8rem);
    margin: 0 0 .4rem;
    color: var(--werther-blau);
    line-height: 1.15;
  }
  header.hero .author {
    font-variant: small-caps;
    letter-spacing: .22em;
    font-size: 1.15rem;
    color: var(--ink-soft);
  }
  header.hero .year {
    margin-top: .3rem;
    font-style: italic;
    color: var(--ink-soft);
  }

  /* ---------- Vorrede ---------- */
  .vorrede {
    max-width: 36rem;
    margin: 0 auto 3rem;
    padding: 1.6rem 2rem;
    font-style: italic;
    color: var(--ink-soft);
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    position: relative;
  }
  .vorrede::before {
    content: "\\2766";
    position: absolute;
    top: -0.9rem;
    left: 50%;
    transform: translateX(-50%);
    background: var(--paper);
    padding: 0 .7rem;
    color: var(--werther-gelb);
    font-size: 1.2rem;
    font-style: normal;
  }
  .vorrede p { margin: .6em 0; }

  /* ---------- Inhalt ---------- */
  main {
    max-width: 44rem;
    margin: 0 auto;
    padding: 0 1.2rem 5rem;
  }

  h2.book-heading {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 4.5rem 0 2.5rem;
    font-family: "Grenze Gotisch", serif;
    font-weight: 600;
    font-size: 2.1rem;
    color: var(--werther-blau);
    text-align: center;
  }
  h2.book-heading::before,
  h2.book-heading::after {
    content: "";
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--werther-gelb), transparent);
  }
  h2.book-heading span { white-space: nowrap; padding: 0 .4rem; }

  /* Briefe als Briefbögen */
  article.letter {
    background: #fffdf6;
    border: 1px solid var(--line);
    border-radius: 2px;
    margin: 2.8rem 0;
    padding: 1.6rem 2.1rem 1.8rem;
    box-shadow:
      0 1px 3px rgba(70, 58, 32, .10),
      0 8px 22px -14px rgba(70, 58, 32, .28);
    position: relative;
  }
  /* "Umschlagklappe" oben */
  article.letter::before {
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 5px;
    background: linear-gradient(90deg, var(--werther-blau-hell), var(--werther-gelb-hell), var(--werther-blau-hell));
    border-radius: 2px 2px 0 0;
  }
  /* Siegel */
  article.letter::after {
    content: "\\2709";
    position: absolute;
    top: -0.85rem;
    right: 1.4rem;
    width: 1.9rem;
    height: 1.9rem;
    display: grid;
    place-items: center;
    font-size: .95rem;
    color: #fffdf6;
    background: radial-gradient(circle at 35% 30%, #5577a5, var(--werther-blau) 65%);
    border-radius: 50%;
    box-shadow: 0 2px 5px rgba(50,42,24,.3);
  }

  h3.letter-date {
    font-family: "Dancing Script", cursive;
    font-weight: 600;
    font-size: 1.85rem;
    margin: 0 0 .9rem;
    color: var(--werther-blau);
  }
  h3.letter-date::after {
    content: "";
    display: block;
    width: 5.5rem;
    height: 2px;
    margin-top: .35rem;
    background: var(--werther-gelb);
    opacity: .75;
  }

  /* ---------- Stimmungsanzeige ---------- */
  .mood-badge {
    display: none;
    position: absolute;
    top: 1.75rem;
    right: 2.1rem;
    max-width: 45%;
    align-items: center;
    gap: .45em;
    font-variant: small-caps;
    letter-spacing: .06em;
    font-size: 1.02rem;
    color: var(--ink-soft);
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: .12rem .75rem .12rem .5rem;
    background: var(--paper);
  }
  .mood-badge::before {
    content: "";
    flex: none;
    width: .78em;
    height: .78em;
    border-radius: 50%;
    background: var(--mood);
    box-shadow: inset 0 0 1px rgba(0,0,0,.35);
  }
  body.mood-on .mood-badge { display: inline-flex; }

  body.mood-on a.tl-mark::before { background: var(--mood); }
  body.mood-on a.tl-mark:hover::before,
  body.mood-on a.tl-mark:focus-visible::before { background: var(--mood); filter: brightness(1.15) saturate(1.3); }

  .tip-mood { display: none; font-style: normal; color: var(--ink-soft); }
  body.mood-on .tl-tip .tip-mood { display: inline; }

  article.letter p { margin: 0 0 1em; text-align: justify; hyphens: auto; }
  article.letter p:last-child { margin-bottom: 0; }

  /* Initiale im ersten Absatz jedes Briefes */
  article.letter p:first-of-type::first-letter {
    font-family: "Grenze Gotisch", serif;
    font-size: 2.6em;
    line-height: .8;
    float: left;
    padding: .08em .12em 0 0;
    color: var(--werther-gelb);
    text-shadow: 0 1px 0 rgba(70,58,32,.18);
  }

  /* Herausgeber-Erzähltext ausserhalb der Briefe */
  p.narration {
    margin: 1.1em auto;
    text-align: justify;
    hyphens: auto;
    color: var(--ink);
  }

  /* ---------- Zeitstrahl ---------- */
  aside.timeline {
    position: fixed;
    left: 0;
    top: 4.6rem;
    bottom: 0;
    width: 10.5rem;
    z-index: 50;
    pointer-events: none;
  }
  .tl-inner {
    position: absolute;
    top: 2.2rem;
    bottom: 2.2rem;
    left: 6.6rem;
    width: 2px;
    background: linear-gradient(180deg, var(--werther-blau-hell), var(--line) 50%, var(--werther-blau-hell));
  }
  .tl-inner::before, .tl-inner::after {
    content: "";
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--werther-blau);
  }
  .tl-inner::before { top: -10px; }
  .tl-inner::after  { bottom: -10px; }

  .tl-tick {
    position: absolute;
    right: calc(100% + 2px);
    width: 7px;
    height: 1px;
    background: var(--line);
    transform: translateY(-50%);
  }
  .tl-month, .tl-year {
    position: absolute;
    right: calc(100% + 13px);
    transform: translateY(-50%);
    font-size: .78rem;
    letter-spacing: .05em;
    color: var(--ink-soft);
    font-variant: small-caps;
    line-height: 1;
  }
  .tl-year {
    font-size: .92rem;
    font-weight: 600;
    color: var(--werther-blau);
    right: calc(100% + 38px);
  }

  a.tl-mark {
    position: absolute;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 22px;
    height: 7px;
    display: block;
    pointer-events: auto;
  }
  a.tl-mark::before {
    content: "";
    position: absolute;
    left: 50%; top: 50%;
    transform: translate(-50%, -50%);
    width: 14px;
    height: 2px;
    background: var(--werther-gelb);
    transition: width .15s, height .15s, background .15s;
  }
  a.tl-mark:hover::before,
  a.tl-mark:focus-visible::before {
    width: 20px;
    height: 3px;
    background: var(--werther-blau);
  }
  .tl-tip {
    position: absolute;
    left: calc(100% + 10px);
    top: 50%;
    transform: translateY(-50%);
    white-space: nowrap;
    background: #fffdf6;
    border: 1px solid var(--line);
    border-left: 3px solid var(--werther-gelb);
    color: var(--ink);
    font-size: .95rem;
    font-style: italic;
    padding: .15rem .6rem;
    border-radius: 2px;
    box-shadow: 0 2px 8px rgba(70,58,32,.18);
    opacity: 0;
    visibility: hidden;
    transition: opacity .12s;
    pointer-events: none;
    z-index: 60;
  }
  a.tl-mark:hover .tl-tip,
  a.tl-mark:focus-visible .tl-tip {
    opacity: 1;
    visibility: visible;
  }

  @media (max-width: 1120px) {
    aside.timeline { display: none; }
  }

  /* ---------- Abonnieren ---------- */
  section.subscribe {
    max-width: 44rem;
    margin: 0 auto;
    padding: 0 1.2rem 4rem;
  }
  .sub-intro { text-align: justify; hyphens: auto; }
  .feed-cards {
    display: flex;
    gap: 1.4rem;
    margin: 1.8rem 0;
    flex-wrap: wrap;
  }
  .feed-card {
    flex: 1 1 14rem;
    background: #fffdf6;
    border: 1px solid var(--line);
    border-top: 4px solid var(--werther-blau-hell);
    border-radius: 2px;
    padding: 1.1rem 1.4rem 1.2rem;
    box-shadow: 0 1px 3px rgba(70,58,32,.10);
    text-align: center;
  }
  .feed-card.fresh { border-top-color: var(--werther-gelb); }
  .feed-card h3 {
    font-family: "Grenze Gotisch", serif;
    font-weight: 600;
    font-size: 1.45rem;
    margin: 0 0 .3rem;
    color: var(--werther-blau);
  }
  .feed-years { margin: 0 0 .5rem; color: var(--ink-soft); font-size: .98rem; }
  .feed-status { margin: 0 0 .8rem; font-style: italic; font-size: .98rem; min-height: 1.3em; }
  .feed-card.fresh .feed-status { color: var(--werther-blau); font-weight: 500; }
  a.feed-link {
    display: inline-block;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: .92rem;
    color: var(--werther-blau);
    background: var(--paper);
    border: 1px solid var(--line);
    border-radius: 3px;
    padding: .3rem .8rem;
    text-decoration: none;
  }
  a.feed-link:hover { border-color: var(--werther-gelb); }
  .howto h3 {
    font-family: "Grenze Gotisch", serif;
    font-weight: 600;
    font-size: 1.45rem;
    color: var(--werther-blau);
    margin: 1.6rem 0 .6rem;
  }
  .howto ol { padding-left: 1.3rem; }
  .howto li { margin-bottom: .7em; }
  .howto a { color: var(--werther-blau); }

  /* ---------- Fusszeile ---------- */
  footer {
    border-top: 1px solid var(--line);
    background: var(--paper-deep);
    color: var(--ink-soft);
    text-align: center;
    padding: 2rem 1.5rem 2.5rem;
    font-size: .95rem;
  }
  footer a { color: var(--werther-blau); }
  footer .fleuron { color: var(--werther-gelb); font-size: 1.2rem; margin-bottom: .6rem; }

  /* Nach-oben-Knopf */
  a.to-top {
    position: fixed;
    right: 1.2rem;
    bottom: 1.2rem;
    width: 2.6rem;
    height: 2.6rem;
    display: grid;
    place-items: center;
    background: var(--werther-blau);
    color: var(--werther-gelb-hell);
    border-radius: 50%;
    text-decoration: none;
    font-size: 1.2rem;
    box-shadow: 0 2px 8px rgba(50,42,24,.3);
    opacity: .85;
  }
  a.to-top:hover { opacity: 1; }

  @media (max-width: 600px) {
    body { font-size: 1.12rem; }
    article.letter { padding: 1.2rem 1.1rem 1.4rem; margin: 2.2rem 0; }
    nav.topbar { gap: .8rem; padding: .5rem .9rem; }
    nav.topbar .brand { font-size: 1.1rem; }
    .mood-badge {
      position: static;
      max-width: none;
      margin-bottom: .8rem;
    }
  }
</style>
</head>
<body>

<nav class="topbar">
  <a class="brand" href="#top"><span class="seal">&#9993;</span>Werther</a>
  <ul>
    <li><a class="navlink active" href="#volltext">Volltext</a></li>
    <li><a class="navlink" href="#abonnieren">Abonnieren</a></li>
    <li><button class="navlink" id="moodToggle" aria-pressed="false"
        title="Werthers Stimmung in Briefen und Zeitstrahl anzeigen">Stimmung</button></li>
  </ul>
</nav>

<aside class="timeline" aria-label="Zeitstrahl der Briefe">
  <div class="tl-inner">
{{TIMELINE}}
  </div>
</aside>

<header class="hero" id="top">
  <div class="ornament">&#10087; &#10087; &#10087;</div>
  <h1>Die Leiden des jungen&nbsp;Werther</h1>
  <div class="author">Johann Wolfgang von Goethe</div>
  <div class="year">Ein Briefroman &middot; 1774</div>
</header>

<section class="vorrede" aria-label="Vorrede des Herausgebers">
{{VORREDE}}
</section>

<main id="volltext">
{{BODY}}
</main>

<section class="subscribe" id="abonnieren" aria-label="Werthers Briefe abonnieren">
  <h2 class="book-heading"><span>Werther schreibt &ndash; das Brief-Abo</span></h2>
  <p class="sub-intro">Werthers Briefe lassen sich <em>in Echtzeit</em> miterleben:
     Jeder Brief erscheint an seinem richtigen Datum &ndash; vom ersten Brief am
     4.&nbsp;Mai bis zur letzten Nachricht in der Dezembernacht. Da die Handlung
     zwei Jahre umspannt, laufen zwei zeitversetzte Durchl&auml;ufe parallel;
     beim Einstieg zeigt das Abo automatisch alle bisherigen Briefe des
     laufenden Durchlaufs.</p>

  <div class="feed-cards">
    <div class="feed-card" data-parity="1">
      <h3>Zyklus A</h3>
      <p class="feed-years">1771 = ungerade Jahre<br>(2025, 2027, &hellip;)</p>
      <p class="feed-status" data-status></p>
      <a class="feed-link" href="feed-a.xml">feed-a.xml</a>
    </div>
    <div class="feed-card" data-parity="0">
      <h3>Zyklus B</h3>
      <p class="feed-years">1771 = gerade Jahre<br>(2026, 2028, &hellip;)</p>
      <p class="feed-status" data-status></p>
      <a class="feed-link" href="feed-b.xml">feed-b.xml</a>
    </div>
  </div>

  <div class="howto">
    <h3>So abonnierst du</h3>
    <ol>
      <li><strong>Als E-Mail:</strong> Feed-Adresse kopieren (Rechtsklick auf den
          Link &rarr; &bdquo;Linkadresse kopieren&ldquo;) und bei einem
          RSS-zu-Mail-Dienst wie <a href="https://blogtrottr.com">Blogtrottr</a>
          oder <a href="https://follow.it">Follow.it</a> zusammen mit deiner
          E-Mail-Adresse eintragen &ndash; fertig. Neue Briefe kommen als Mail.</li>
      <li><strong>Mit Feedreader:</strong> In Apps wie
          <a href="https://netnewswire.com">NetNewsWire</a> (Mac/iOS, gratis),
          <a href="https://feedly.com">Feedly</a> oder
          <a href="https://www.inoreader.com">Inoreader</a> die Feed-Adresse
          hinzuf&uuml;gen.</li>
      <li><strong>In Microsoft Teams</strong> (f&uuml;r Klassen): In
          <a href="https://make.powerautomate.com">Power Automate</a> einen Flow
          mit dem Ausl&ouml;ser &bdquo;Wenn ein Feedelement ver&ouml;ffentlicht
          wird&ldquo; (RSS) anlegen, die Feed-Adresse eintragen und als Aktion
          &bdquo;In einem Kanal posten&ldquo; (Teams) w&auml;hlen &ndash; dann
          erscheint jeder Brief automatisch im Klassenkanal.</li>
    </ol>
  </div>
</section>

<footer>
  <div class="fleuron">&#10087;</div>
  <p>Textgrundlage: Hamburger Ausgabe, Band&nbsp;6 &mdash;
     <a href="https://www.gutenberg.org/ebooks/2407">Projekt Gutenberg #2407</a> &amp;
     <a href="https://www.gutenberg.org/ebooks/2408">#2408</a> (gemeinfrei).</p>
</footer>

<a class="to-top" href="#top" aria-label="Nach oben">&#8593;</a>

<script>
(function () {
  var btn = document.getElementById('moodToggle');
  var KEY = 'werther-mood';
  function set(on) {
    document.body.classList.toggle('mood-on', on);
    btn.setAttribute('aria-pressed', String(on));
    try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) {}
  }
  btn.addEventListener('click', function () {
    set(!document.body.classList.contains('mood-on'));
  });
  try { if (localStorage.getItem(KEY) === '1') set(true); } catch (e) {}

  // Zyklus-Status der Brief-Abos anzeigen
  var MONATE = ['Januar','Februar','März','April','Mai','Juni','Juli',
                'August','September','Oktober','November','Dezember'];
  var heute = new Date();
  var frischstes = -1;
  var karten = document.querySelectorAll('.feed-card');
  karten.forEach(function (card) {
    var parity = +card.dataset.parity;
    var y = heute.getFullYear();
    while (y % 2 !== parity || heute < new Date(y, 4, 4)) y--;
    card.dataset.start = y;
    if (y > frischstes) frischstes = y;
    var fiktiv = 1771 + (heute.getFullYear() - y);
    var status;
    if (fiktiv > 1772 || (fiktiv === 1772 && heute >= new Date(y + 1, 11, 24))) {
      status = 'Durchlauf ' + y + '\u2013' + (y + 1) + ' beendet \u2013 Neustart am 4. Mai ' + (y + 2);
    } else {
      status = 'Läuft \u2013 Werther schreibt gerade im ' +
               MONATE[heute.getMonth()] + ' ' + Math.min(fiktiv, 1772);
    }
    card.querySelector('[data-status]').textContent = status;
  });
  karten.forEach(function (card) {
    if (+card.dataset.start === frischstes) card.classList.add('fresh');
  });
})();
</script>

</body>
</html>
"""


if __name__ == "__main__":
    main()
