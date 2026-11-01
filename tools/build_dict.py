"""Build a compact French dictionary restricted to the vocabulary of the parsed tome(s).
Usage: python build_dict.py out.json en-fr.jsonl fr-fr.jsonl tome2.json [tome3.json ...]
Output: {"d": {word: [[src, pos, gender, [glosses], lemma], ...]}, "i": {word: ipa}}
src is "e" (English glosses, en.wiktionary) or "f" (French definitions, fr.wiktionary).
"""
import json, re, sys

out, en_path, fr_path, *tomes = sys.argv[1:]

L = "A-Za-zÀ-ÖØ-öø-ÿŒœÆæ"
WORD = re.compile(rf"[{L}]+(?:['’-][{L}]+)*'?")
ELISION = {"l": ["le", "la"], "d": ["de"], "j": ["je"], "m": ["me"], "t": ["te"], "s": ["se", "si"],
           "c": ["ce"], "n": ["ne"], "qu": ["que"], "jusqu": ["jusque"], "lorsqu": ["lorsque"],
           "puisqu": ["puisque"], "quoiqu": ["quoique"]}

vocab = set()
def add(w):
    vocab.add(w); vocab.add(w.lower())

for t in tomes:
    for lv in json.load(open(t, encoding="utf-8")):
        texts = [lv["title"]]
        for ch in lv["chapters"]:
            texts.append(ch["title"])
            for p in ch["paras"]:
                texts.extend(p)
        for s in texts:
            for w in WORD.findall(s.replace("’", "'")):
                w = w.rstrip("'")
                add(w)
                for part in re.split(r"['-]", w):
                    if part:
                        add(part)
                if "'" in w:
                    pre = w.split("'")[0].lower()
                    for e in ELISION.get(pre, []):
                        add(e)
print("vocab", len(vocab))

WORD_KEY = re.compile(r'"word": "((?:[^"\\]|\\.)*)"')
MAX_SENSES, MAX_LEN = 6, 240

def gender(e, s=None):
    tags = set(e.get("tags", [])) | set((s or {}).get("tags", []))
    g = ("m" if "masculine" in tags else "") + ("f" if "feminine" in tags else "")
    return g

def compact(e, src):
    gl, lemma = [], None
    for s in e.get("senses", []):
        g = s.get("glosses")
        if not g:
            continue
        text = " ".join(g) if src == "e" else g[-1]
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > MAX_LEN:
            text = text[:MAX_LEN].rsplit(" ", 1)[0] + "…"
        if text and text not in gl:
            gl.append(text)
        if s.get("form_of") and not lemma:
            lemma = (s["form_of"][0].get("word") or "").replace("’", "'") or None
        if len(gl) >= MAX_SENSES:
            break
    if not gl:
        return None
    g = gender(e) or next((gender(e, s) for s in e.get("senses", []) if gender(e, s)), "")
    return [src, e.get("pos", ""), g, gl, lemma]

def scan(path, src, wanted, D, IPA):
    lemmas = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = WORD_KEY.search(line)
            if not m:
                continue
            w = json.loads('"' + m.group(1) + '"').replace("’", "'")
            if w not in wanted:
                continue
            e = json.loads(line)
            if e.get("word", "").replace("’", "'") != w or e.get("lang_code") != "fr":
                continue
            c = compact(e, src)
            if not c:
                continue
            D.setdefault(w, []).append(c)
            if c[4]:
                lemmas.add(c[4])
            if w not in IPA:
                ipa = next((s["ipa"] for s in e.get("sounds", []) if s.get("ipa")), None)
                if ipa:
                    IPA[w] = ipa.strip("\\/[]")
    return lemmas

D, IPA = {}, {}
need = set(vocab)
for rnd in range(2):
    new = set()
    for path, src in [(en_path, "e"), (fr_path, "f")]:
        new |= scan(path, src, need, D, IPA)
        print(f"round {rnd} {src}: {len(D)} words", flush=True)
    need = new - set(D)
    if not need:
        break

# drop duplicates within a word, keep english first
for w, es in D.items():
    seen, res = set(), []
    for e in sorted(es, key=lambda e: e[0] != "e"):
        k = json.dumps(e, ensure_ascii=False)
        if k not in seen:
            seen.add(k); res.append(e)
    D[w] = res

json.dump({"d": D, "i": IPA}, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
missing = sorted(w for w in vocab if w not in D and w.lower() not in D and w.islower())
print("entries", len(D), "missing lowercase words", len(missing), missing[:80])
