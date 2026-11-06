# Projektkontext: Werther

## Zweck

Statische Webseite zu Goethes Briefroman **„Die Leiden des jungen Werther“**
(1774), primär für den Schulunterricht (Kantonsschule). Volltext mit
literarischen Zusatzfunktionen: Zeitstrahl, Stimmungsanalyse, Brief-Abo in
Echtzeit.

- **Live:** <https://nicolasruh.github.io/werther/>
- **Repo:** <https://github.com/nicolasruh/werther>

## Technischer Rahmen

- **Rein statisch**, gehostet auf GitHub Pages (Branch `main`, Root). Keine
  Datenbank, kein Server, keine Nutzerdaten, keine Kosten.
- **Build-Pipeline in Python 3** (nur Standardbibliothek): Generatoren bauen
  die Artefakte aus den Quelltexten; die generierten Dateien werden mit
  committet.
- **Textgrundlage:** Projekt Gutenberg #2407/#2408 (Hamburger Ausgabe, Bd. 6,
  gemeinfrei) in `sources/band1.txt` und `band2.txt` – diese Dateien nie
  editieren. Die Vorrede („Was ich von der Geschichte des armen Werther…“)
  fehlt dort und ist in `build.py` ergänzt.
- **GitHub Action** (`.github/workflows/feeds.yml`): täglicher Cron
  (~5:30 Uhr Europe/Zurich), regeneriert die Feeds und committet bei
  Änderung; Keepalive-Leer-Commit alle 50 stillen Tage gegen die
  60-Tage-Cron-Deaktivierung.

## Dateien

| Datei | Rolle |
|---|---|
| `build.py` | Generiert `index.html` (Parsing, Typografie, komplettes HTML/CSS/JS-Template als String) |
| `generate_feeds.py` | Generiert `feed-a.xml` / `feed-b.xml`; importiert Parsing-Funktionen aus `build.py` |
| `moods.json` | Stimmungs-Klassifikation aller 84 Briefe: `n`, `date`, `word`, `score` (−5…+5); von Hand editierbar |
| `index.html`, `feed-*.xml` | **Generiert – nie von Hand editieren** |

## Umgesetzte Features

1. **Volltext als Onepage** – 84 Briefe als „Briefbögen“ (Karten mit Siegel,
   Initiale, handschriftlichem Datum), Abschnitte Erstes/Zweites Buch und
   „Der Herausgeber an den Leser“. Anker: `#brief-1`…`#brief-84`,
   `#erstes-buch`, `#zweites-buch`, `#herausgeber`.
   Design: Pastell/Papier, Werther-Farben Blau + Gelb, Fonts EB Garamond /
   Grenze Gotisch / Dancing Script (Google Fonts).
2. **Zeitstrahl** (fixe Leiste links, ausgeblendet < 1120 px): Mai 1771 –
   Dez. 1772 zeitproportional, Monats-/Jahresbeschriftung, pro Brief ein
   Marker (Hover = Datum-Tooltip, Klick = Scroll zum Brief, dichte Cluster
   weichen minimal nach unten aus).
3. **Stimmungsanzeige** (Kippschalter in der Topbar, Zustand in
   `localStorage`): Badge im Briefkopf („schwärmerisch · +4“) und eingefärbte
   Zeitstrahl-Marker. Farbskala: Sonnengelb (+5) → entsättigt (0) → dunkles
   Blau → fast Schwarz (−5). Die Klassifikation folgt bewusst der Lesart
   „manisch-depressiver Verlauf“: euphorischer Sommer 1771, dunkler Winter,
   hypomanes Zwischenhoch Frühjahr 1772, Absturz bis Dezember.
4. **Brief-Abo „Werther schreibt“** (Atom-Feeds, Overlay-Dialog über
   „Abonnieren“): Briefe erscheinen am „richtigen“ Datum.
   **Zweijahreszyklus**, da die Handlung 20 Monate umspannt:
   Zyklus A = 1771 in ungeraden Jahren, Zyklus B = 1771 in geraden; die
   Feeds enthalten jeweils alle bisherigen Briefe des laufenden Durchlaufs
   (Catch-up für Neueinsteiger). Schlusseintrag am 23.12. ist der
   Herausgeber-Bericht. Push-Kanäle als Adapter: RSS→Mail
   (Blogtrottr/Follow.it), Feedreader, Teams via Power Automate
   (RSS-Trigger → Kanal-Post) – bewusst keine eigene Adressverwaltung
   (Datenschutz bei Minderjährigen).

## Arbeitsweise

- **Workflow bei Änderungen:** Quelle anpassen (`build.py` für Layout/Logik,
  `moods.json` für Einstufungen) → `python3 build.py` und ggf.
  `python3 generate_feeds.py` → lokal prüfen → committen & pushen
  (Pages deployt automatisch, ~1 Min.).
- `build.py` validiert beim Bauen, dass `moods.json` vollständig ist und
  jeder Eintrag per Datumsabgleich zum richtigen Brief gehört (Assertions).
- Briefe werden per Regex an freistehenden Datumszeilen erkannt
  (`Am|Den <Tag>. <Monat> [Jahr]`, alte Monatsnamen Junius/Julius);
  Jahreszahlen fehlen meist und werden fortgeschrieben (Monatsrücksprung ⇒
  Jahreswechsel). Sonderfälle: „Nach Eilfe“ (= 22.12.1772), Briefende vor der
  Schluss-Erzählung („Ein Nachbar sah den Blick vom Pulver…“).
- **Konventionen:** Deutsch für UI, Kommentare und Commit-Messages;
  typografische Aufbereitung im Build („--“ → Geviertstrich, gerade
  Anführungszeichen → „…“); keine externen Python-Abhängigkeiten.
