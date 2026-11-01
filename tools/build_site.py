"""Write the reader's data files (script files, so the page works from file://).
Usage: python build_site.py SITE_DIR dict.json  ID:"Title":tome.json:tr.json [...]
"""
import json, os, sys

site, dict_path, *specs = sys.argv[1:]
data = os.path.join(site, "data")
os.makedirs(data, exist_ok=True)

def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

tomes = []
for spec in specs:
    tid, title, tome_path, tr_path = spec.split(":")
    livres = json.load(open(tome_path, encoding="utf-8"))
    tr = json.load(open(tr_path, encoding="utf-8"))
    missing = 0
    def T(s):
        global missing
        if s not in tr:
            missing += 1
        return tr.get(s, "")
    tdir = os.path.join(data, f"tome{tid}")
    os.makedirs(tdir, exist_ok=True)
    toc = {"id": tid, "title": title, "livres": []}
    offset = 0  # running character offset in the tome, used for approximate page numbers
    for li, lv in enumerate(livres, 1):
        tl = {"num": lv["num"], "title": lv["title"].replace("_", ""), "titleEn": T(lv["title"]), "chapters": []}
        for ci, ch in enumerate(lv["chapters"], 1):
            key = f"{tid}/{li}/{ci}"
            fname = f"l{li}c{ci:02d}.js"
            payload = {"fr": ch["paras"], "en": [[T(s) for s in p] for p in ch["paras"]]}
            with open(os.path.join(tdir, fname), "w", encoding="utf-8") as f:
                f.write(f"LM_CHAPTER({js(key)},{js(payload)});\n")
            n = sum(len(s) + 1 for p in ch["paras"] for s in p)
            tl["chapters"].append({"num": ch["num"], "title": ch["title"], "titleEn": T(ch["title"]),
                                   "file": f"data/tome{tid}/{fname}", "start": offset, "len": n})
            offset += n
        toc["livres"].append(tl)
    tomes.append(toc)
    print(f"tome {tid}: missing translations {missing}")

with open(os.path.join(data, "tomes.js"), "w", encoding="utf-8") as f:
    f.write("window.LM_TOMES=" + json.dumps(tomes, ensure_ascii=False, indent=1) + ";\n")
with open(os.path.join(data, "dict.js"), "w", encoding="utf-8") as f:
    f.write("window.LM_DICT=" + open(dict_path, encoding="utf-8").read() + ";\n")
print("ok")
