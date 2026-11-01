# Rebuilding / adding a tome

Scripts used to build `data/`. Sources: Project Gutenberg French text
(Tome I = 17489, II = 17493, III = 17494, IV = 17518, V = 17519),
dictionaries from kaikki.org (en.wiktionary French + fr.wiktionary Français).

    python3 parse.py pg17494.txt tome3.json                      # split into livres/chapitres/phrases
    venv/bin/python translate.py tome3.json tr3.json             # offline MT (torch + transformers, Opus-MT fr-en)
    python3 build_dict.py dict.json en-fr.jsonl fr-fr.jsonl tome2.json tome3.json
    python3 build_site.py .. dict.json '2:Tome II — Cosette:tome2.json:tr2.json' '3:Tome III — Marius:tome3.json:tr3.json'

After changing `index.html` or `data/`, bump `VERSION` in `sw.js` so installed copies
download the new files (see `sw.js`).
