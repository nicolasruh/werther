# Die Leiden des jungen Werther

Statische Webseite mit dem Volltext von Goethes Briefroman (1774) – mit
Zeitstrahl-Navigation, Stimmungsanzeige und abonnierbaren Briefen.

**Live:** https://nicolasruh.github.io/werther/

## Aufbau

| Datei | Zweck |
|---|---|
| `index.html` | Generierte Seite (nicht von Hand editieren) |
| `build.py` | Generator: baut `index.html` aus Quelltext + Stimmungen |
| `generate_feeds.py` | Erzeugt die Atom-Feeds `feed-a.xml` / `feed-b.xml` |
| `moods.json` | Stimmungs-Klassifikation der 84 Briefe (editierbar) |
| `sources/` | Rohtexte von [Projekt Gutenberg #2407](https://www.gutenberg.org/ebooks/2407) & [#2408](https://www.gutenberg.org/ebooks/2408) (gemeinfrei) |

## Bauen

```sh
python3 build.py           # index.html neu generieren
python3 generate_feeds.py  # Feeds neu generieren
```

## Brief-Abo („Werther schreibt“)

Die Briefe erscheinen per Atom-Feed am jeweils „richtigen“ Datum.
Zweijahreszyklus: Zyklus A bildet 1771 auf ungerade Jahre ab, Zyklus B auf
gerade. Eine GitHub Action (`.github/workflows/feeds.yml`) aktualisiert die
Feeds täglich; GitHub Pages liefert sie aus.
