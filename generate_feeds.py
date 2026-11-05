#!/usr/bin/env python3
"""Erzeugt die Atom-Feeds "Werther schreibt" (Zyklus A und B).

Zweijahreszyklus: Die Briefdaten 1771/1772 werden auf reale Jahre abgebildet.
  Zyklus A: 1771 = ungerade Jahre (2025, 2027, ...), 1772 = das Folgejahr
  Zyklus B: 1771 = gerade Jahre  (2026, 2028, ...), 1772 = das Folgejahr
Jeder Feed enthält alle Briefe des aktuell laufenden (bzw. zuletzt beendeten)
Durchlaufs bis zum heutigen Tag – neue Abonnenten sehen so automatisch den
bisherigen Verlauf. Gedacht für den täglichen Lauf per GitHub Action.
"""
import html
import json
import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from build import (MOODS, MONTHS, SRC1, SRC2, CLOSE_LETTER_STARTS,
                   DROP_PARA_STARTS, SECTION_HEADINGS, clean_body,
                   parse_blocks, strip_gutenberg, typographize)

TZ = ZoneInfo("Europe/Zurich")
BASE = "https://nicolasruh.github.io/werther/"
AUTHOR = "Werther (J. W. Goethe)"
PUBLISH_TIME = time(6, 0)  # Briefe erscheinen morgens um 6 Uhr


def extract_letters():
    """Alle Briefe mit fiktivem Datum, Überschrift, Stimmung und Absätzen."""
    parts = [clean_body(strip_gutenberg(s.read_text(encoding="utf-8")))
             for s in (SRC1, SRC2)]
    blocks = parse_blocks("\n\n".join(parts))
    moods = json.loads(MOODS.read_text(encoding="utf-8"))

    letters = []
    current = None
    n = 0
    current_year = 1771
    prev_month = None

    def close():
        nonlocal current
        if current:
            letters.append(current)
            current = None

    for kind, content in blocks:
        if kind == "book":
            close()
        elif kind == "date":
            close()
            n += 1
            m = re.match(r"^(?:Am|Den) (\d+)\. ([A-ZÄÖÜ][a-zäöü]+)(?: (17\d\d))?$", content)
            if m:
                day, monthname, year = int(m.group(1)), m.group(2), m.group(3)
                month = MONTHS[monthname]
                if year:
                    current_year = int(year)
                elif prev_month is not None and month < prev_month:
                    current_year += 1
                prev_month = month
                d = date(current_year, month, day)
                title = content if year else f"{content} {current_year}"
            else:  # "Nach Eilfe"
                d = date(1772, 12, 22)
                title = content
            current = {"n": n, "date": d, "title": title,
                       "mood": moods[n - 1], "paras": []}
        else:  # para
            if content.startswith(DROP_PARA_STARTS):
                continue
            if content.startswith(CLOSE_LETTER_STARTS):
                close()
            if current:
                current["paras"].append(content)
    close()

    # Schlusseintrag: der Bericht des Herausgebers über Werthers Tod (23.12.)
    last_paras = [c for k, c in blocks if k == "para"
                  and not c.startswith(DROP_PARA_STARTS)][-3:]
    letters.append({"n": 0, "date": date(1772, 12, 23),
                    "title": "Der Herausgeber an den Leser", "mood": None,
                    "paras": ["Werther hat sich in der Nacht erschossen. "
                              "Aus dem Bericht des Herausgebers:"] + last_paras,
                    "anchor": "herausgeber"})
    return letters


def cycle_start_year(today: date, parity: int) -> int:
    """Jahr, in dem der aktuell laufende/zuletzt beendete Durchlauf begann."""
    y = today.year
    while y % 2 != parity or date(y, 5, 4) > today:
        y -= 1
    return y


def entry_xml(letter, real_date: date, cycle: str) -> str:
    anchor = letter.get("anchor") or f"brief-{letter['n']}"
    url = f"{BASE}#{anchor}"
    updated = datetime.combine(real_date, PUBLISH_TIME, tzinfo=TZ).isoformat()
    body = "\n".join(f"<p>{typographize(p)}</p>" for p in letter["paras"])
    body += (f'\n<p><a href="{url}">Im Volltext lesen &rarr;</a></p>')
    eid = f"tag:nicolasruh.github.io,2025:werther:{cycle}:{real_date.isoformat()}:{anchor}"
    mood = letter.get("mood")
    category = (f'\n    <category term="{html.escape(mood["word"], quote=True)}"/>'
                if mood else "")
    return f"""  <entry>
    <title>{html.escape(letter['title'])}</title>
    <id>{eid}</id>
    <link href="{url}"/>
    <updated>{updated}</updated>
    <published>{updated}</published>{category}
    <content type="html">{html.escape(body)}</content>
  </entry>"""


def build_feed(letters, today: date, parity: int, cycle: str, label: str) -> str:
    y0 = cycle_start_year(today, parity)

    def real(d: date) -> date:
        return date(y0 + (d.year - 1771), d.month, d.day)

    published = [(l, real(l["date"])) for l in letters if real(l["date"]) <= today]
    published.sort(key=lambda t: (t[1], t[0]["n"]))
    last_update = (datetime.combine(published[-1][1], PUBLISH_TIME, tzinfo=TZ)
                   if published else datetime.combine(today, PUBLISH_TIME, tzinfo=TZ))

    entries = "\n".join(entry_xml(l, rd, cycle) for l, rd in published)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="de">
  <title>Werther schreibt – Zyklus {cycle}</title>
  <subtitle>Die Briefe aus Goethes "Die Leiden des jungen Werther",
  zugestellt am jeweils richtigen Tag ({label}). Laufender Durchlauf: {y0}–{y0 + 1}.</subtitle>
  <id>tag:nicolasruh.github.io,2025:werther:feed-{cycle.lower()}</id>
  <link href="{BASE}feed-{cycle.lower()}.xml" rel="self" type="application/atom+xml"/>
  <link href="{BASE}"/>
  <updated>{last_update.isoformat()}</updated>
  <author><name>{AUTHOR}</name></author>
{entries}
</feed>
"""


def main():
    today = datetime.now(TZ).date()
    letters = extract_letters()
    from pathlib import Path
    root = Path(__file__).parent
    for parity, cycle, label in ((1, "A", "Beginn in ungeraden Jahren"),
                                 (0, "B", "Beginn in geraden Jahren")):
        xml = build_feed(letters, today, parity, cycle, label)
        out = root / f"feed-{cycle.lower()}.xml"
        out.write_text(xml, encoding="utf-8")
        n = xml.count("<entry>")
        print(f"{out.name}: {n} Einträge (Durchlauf ab {cycle_start_year(today, parity)})")


if __name__ == "__main__":
    main()
