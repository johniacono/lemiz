"""Parse the Gutenberg text of a Les Misérables tome into livres/chapitres/paragraphs/sentences.
Usage: python parse.py pgNNNN.txt out.json
"""
import json, re, sys

src, out = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read().replace("\r\n", "\n")
text = text.split("*** START OF")[1].split("\n", 1)[1]
text = text.split("*** END OF")[0]

lines = text.split("\n")
# Body starts at the second occurrence of the first "Livre" heading (the first is the table of contents).
livre_re = re.compile(r"^Livre [^\s]+--")
livre_idx = [i for i, l in enumerate(lines) if livre_re.match(l)]
first = lines[livre_idx[0]]
body_start = next(i for i in livre_idx[1:] if lines[i] == first)
lines = lines[body_start:]

ROMAN = re.compile(r"^Chapitre ([IVXLC]+)\s*$")

livres = []
cur_livre = cur_ch = None
para = []

def flush_para():
    global para
    if para and cur_ch is not None:
        p = " ".join(s.strip() for s in para).strip()
        if p:
            cur_ch["raw"].append(p)
    para = []

i = 0
while i < len(lines):
    l = lines[i]
    if livre_re.match(l):
        flush_para()
        num, title = l.split("--", 1)
        cur_livre = {"num": num.strip(), "title": title.strip(), "chapters": []}
        livres.append(cur_livre)
        cur_ch = None
    elif ROMAN.match(l) and cur_livre is not None:
        flush_para()
        # title is the next non-empty line(s) until a blank line
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        tl = []
        while j < len(lines) and lines[j].strip():
            tl.append(lines[j].strip()); j += 1
        cur_ch = {"num": ROMAN.match(l).group(1), "title": " ".join(tl), "raw": []}
        cur_livre["chapters"].append(cur_ch)
        i = j
        continue
    elif not l.strip():
        flush_para()
    else:
        para.append(l)
    i += 1
flush_para()

ABBR = {"M", "MM", "Mme", "Mmes", "Mlle", "Mlles", "St", "Ste", "Dr", "etc", "cf", "p", "No", "no", "Mgr", "S", "J.-C", "c"}

def clean(s):
    s = s.replace("--", "—")
    s = re.sub(r"oe(?=u|il)", "œ", s)
    s = re.sub(r"Oe(?=u|il)", "Œ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def split_sentences(p):
    # Split after . ! ? … (optionally followed by closing quotes/brackets) when followed by a space and
    # an uppercase letter, an opening quote or a dash.
    out, start = [], 0
    for m in re.finditer(r"[.!?…]+[»)\]_]*\s+(?=[«—\"(_A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŒ0-9])", p):
        end = m.end()
        before = p[start:m.start() + 1]
        w = re.search(r"([\w.-]+)\.$", before)
        if w and p[m.start()] == "." and (w.group(1) in ABBR or re.fullmatch(r"[A-Z]", w.group(1))):
            continue
        if p[start:end].count("_") % 2:  # don't split inside an italic span
            continue
        out.append(p[start:end].strip())
        start = end
    tail = p[start:].strip()
    if tail:
        out.append(tail)
    # merge very short fragments (like "—") into the next
    merged = []
    for s in out:
        if merged and len(merged[-1]) < 3:
            merged[-1] += " " + s
        else:
            merged.append(s)
    return merged

for lv in livres:
    for ch in lv["chapters"]:
        ch["title"] = clean(ch["title"])
        ch["paras"] = [split_sentences(clean(p)) for p in ch.pop("raw")]
    lv["title"] = clean(lv["title"])

json.dump(livres, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
n_ch = sum(len(l["chapters"]) for l in livres)
n_s = sum(len(p) for l in livres for c in l["chapters"] for p in c["paras"])
n_p = sum(len(c["paras"]) for l in livres for c in l["chapters"])
print(f"{len(livres)} livres, {n_ch} chapitres, {n_p} paragraphes, {n_s} phrases")
for l in livres:
    print(l["num"], l["title"], len(l["chapters"]))
