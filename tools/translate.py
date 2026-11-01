"""Pre-translate every sentence (and chapter/livre titles) of a parsed tome, French -> English, offline.
Usage: python translate.py tome2.json tr2.json [limit]
Resumable: existing entries in the output file are kept.
"""
import json, os, re, sys, time
import torch
from transformers import MarianMTModel, MarianTokenizer

src, out = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
MODEL = "Helsinki-NLP/opus-mt-tc-big-fr-en"
dev = "mps" if torch.backends.mps.is_available() else "cpu"
tok = MarianTokenizer.from_pretrained(MODEL)
model = MarianMTModel.from_pretrained(MODEL).to(dev).eval()

livres = json.load(open(src, encoding="utf-8"))
items = []
for lv in livres:
    items.append(lv["title"])
    for ch in lv["chapters"]:
        items.append(ch["title"])
        for p in ch["paras"]:
            items.extend(p)
items = list(dict.fromkeys(items))
done = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
todo = [s for s in items if s not in done][:limit]

def prep(s):
    return s.replace("_", "").replace("«", "\"").replace("»", "\"")

def chunks(s, maxlen=300):
    """Split an overly long sentence at ; : or , boundaries into pieces of at most ~maxlen chars."""
    if len(s) <= maxlen:
        return [s]
    for sep in ["; ", ": ", ", "]:
        parts = s.split(sep)
        if len(parts) > 1:
            res, cur = [], ""
            for i, part in enumerate(parts):
                piece = part + (sep.strip() if i < len(parts) - 1 else "")
                if cur and len(cur) + len(piece) > maxlen:
                    res.append(cur); cur = piece
                else:
                    cur = (cur + " " + piece).strip()
            res.append(cur)
            if all(len(r) <= maxlen * 1.6 for r in res):
                return res
    return [s]

pieces = []  # (sentence, piece)
for s in todo:
    for c in chunks(prep(s)):
        pieces.append((s, c))
order = sorted(range(len(pieces)), key=lambda i: len(pieces[i][1]))
res = [None] * len(pieces)
B = 24
t0 = time.time()
for bi in range(0, len(order), B):
    idx = order[bi:bi + B]
    batch = [pieces[i][1] for i in idx]
    enc = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to(dev)
    with torch.no_grad():
        gen = model.generate(**enc, num_beams=4, max_new_tokens=512)
    for i, t in zip(idx, tok.batch_decode(gen, skip_special_tokens=True)):
        res[i] = t
    if (bi // B) % 20 == 0:
        print(f"{bi + len(idx)}/{len(order)} pieces, {time.time() - t0:.0f}s", flush=True)
# assemble per sentence in original piece order
acc = {}
for (s, _), t in zip(pieces, res):
    acc.setdefault(s, []).append(t)
for s, ts in acc.items():
    done[s] = " ".join(ts)
json.dump(done, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print(f"done {len(acc)} sentences in {time.time() - t0:.0f}s; total {len(done)}/{len(items)}")
