"""Render every slideshow in content/ that hasn't been rendered yet, then rebuild the site.

Usage: python3 scripts/build.py [--force <id>|all]
Output: site/index.html (newest first) and site/days/<id>/{01.jpg..,index.html}
"""
import glob, html, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import render  # noqa: E402
import fetch_assets  # noqa: E402

SITE = os.path.join(ROOT, "site")

CSS = """
:root{--ink:#1F1714;--cream:#F6EEE4;--terra:#C8643F;--muted:#9C8A80;--card:#2A201C}
*{box-sizing:border-box}body{margin:0;background:var(--ink);color:var(--cream);
font-family:-apple-system,BlinkMacSystemFont,"Inter",sans-serif;line-height:1.45}
main{max-width:560px;margin:0 auto;padding:20px 16px 60px}
h1{font-family:Georgia,serif;font-weight:600;font-size:28px;margin:8px 0 4px}
.sub{color:var(--muted);font-size:14px;margin-bottom:18px}
.btn{display:block;width:100%;border:0;border-radius:14px;padding:16px;font-size:17px;font-weight:600;
background:var(--terra);color:#fff;margin:10px 0}
.btn.alt{background:var(--card);color:var(--cream)}
.cap{background:var(--card);border-radius:14px;padding:14px;font-size:15px;white-space:pre-wrap}
.warn{background:#4a2a1c;border-radius:14px;padding:12px 14px;font-size:14px;margin:12px 0}
.slides img{width:100%;border-radius:12px;margin:10px 0;display:block}
a.day{display:flex;gap:12px;align-items:center;background:var(--card);border-radius:14px;padding:10px;
margin:10px 0;color:inherit;text-decoration:none}
a.day img{width:64px;height:114px;object-fit:cover;border-radius:8px}
a.day b{display:block;font-size:16px}a.day span{color:var(--muted);font-size:13px}
.new{color:var(--terra);font-weight:700;font-size:12px;letter-spacing:.06em}
"""

_UNUSED_DAY_JS = """
const files=%s;
async function saveAll(btn){
  btn.textContent='Hazırlanıyor…';
  try{
    const blobs=await Promise.all(files.map(f=>fetch(f).then(r=>r.blob())));
    const fs=blobs.map((b,i)=>new File([b],files[i],{type:'image/jpeg'}));
    if(navigator.canShare&&navigator.canShare({files:fs})){await navigator.share({files:fs});btn.textContent='Kaydedildi ✓';}
    else{btn.textContent='Görsellere basılı tutup tek tek kaydet';}
  }catch(e){btn.textContent='Hepsini Fotoğraflara kaydet';}
}
function copyCap(btn){navigator.clipboard.writeText(document.getElementById('cap').innerText);btn.textContent='Kopyalandı ✓';}
"""


LANG_LABEL = {"en": "🇺🇸 English (ABD hesabı)", "tr": "🇹🇷 Türkçe (Işılda hesabı)"}


def lang_block(lang, data, files, prefix):
    names = [prefix + os.path.basename(f) for f in files]
    warn = ""
    if data.get("mentions_app"):
        warn = ('<div class="warn">Bu slideshow uygulamadan bahsediyor. Paylaşırken '
                '<b>More options → Disclose post content → Your brand</b> anahtarını aç.</div>')
    imgs = "\n".join(f'<img src="{n}" alt="slayt {i}" loading="lazy">' for i, n in enumerate(names, 1))
    return f"""<section class="lang" id="l-{lang}" data-files='{json.dumps(names)}'>
<button class="btn" onclick="saveAll(this,'{lang}')">Hepsini Fotoğraflara kaydet</button>
<div class="cap" id="cap-{lang}">{html.escape(data.get('caption', ''))}</div>
<button class="btn alt" onclick="copyCap(this,'{lang}')">Açıklamayı kopyala</button>
{warn}<div class="slides">{imgs}</div></section>"""


def day_page(variants):
    """variants: list of (lang, localized_data, files); first one is the default tab."""
    base = variants[0][1]
    tabs = "".join(f'<button class="tab" data-l="{l}" onclick="show(\'{l}\')">{LANG_LABEL.get(l, l)}</button>'
                   for l, _, _ in variants) if len(variants) > 1 else ""
    blocks = "".join(lang_block(l, d, f, "" if l == "en" else f"{l}/") for l, d, f in variants)
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{html.escape(base['id'])}</title><style>{CSS}
.tabs{{display:flex;gap:8px;margin:6px 0 4px}}.tab{{flex:1;border:0;border-radius:12px;padding:12px 6px;font-size:14px;
background:var(--card);color:var(--muted)}}.tab.on{{background:var(--cream);color:var(--ink);font-weight:700}}
</style></head><body><main>
<a href="../../" style="color:var(--muted);text-decoration:none">← Tüm günler</a>
<h1>{html.escape(base.get('title', base['id']))}</h1>
<div class="sub">{html.escape(base.get('date', ''))} · {base.get('slot', 1)}. paylaşım · {len(variants[0][2])} slayt</div>
<div class="tabs">{tabs}</div>{blocks}
<script>
function show(l){{document.querySelectorAll('.lang').forEach(s=>s.style.display=s.id==='l-'+l?'block':'none');
document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.dataset.l===l));
try{{localStorage.setItem('lang',l)}}catch(e){{}}}}
let pref='en';try{{pref=localStorage.getItem('lang')||'en'}}catch(e){{}}
show(document.getElementById('l-'+pref)?pref:'en');
async function saveAll(btn,l){{
  const files=JSON.parse(document.getElementById('l-'+l).dataset.files);
  btn.textContent='Hazırlanıyor…';
  try{{
    const blobs=await Promise.all(files.map(f=>fetch(f).then(r=>r.blob())));
    const fs=blobs.map((b,i)=>new File([b],l+'-'+(i+1)+'.jpg',{{type:'image/jpeg'}}));
    if(navigator.canShare&&navigator.canShare({{files:fs}})){{await navigator.share({{files:fs}});btn.textContent='Kaydedildi ✓';}}
    else{{btn.textContent='Görsellere basılı tutup tek tek kaydet';}}
  }}catch(e){{btn.textContent='Hepsini Fotoğraflara kaydet';}}
}}
function copyCap(btn,l){{navigator.clipboard.writeText(document.getElementById('cap-'+l).innerText);btn.textContent='Kopyalandı ✓';}}
</script></main></body></html>"""


def index_page(days):
    rows = []
    for k, (data, files) in enumerate(days):
        thumb = f"days/{data['id']}/{os.path.basename(files[0])}"
        tag = '<div class="new"></div>'
        rows.append(f'<a class="day" data-date="{data.get("date", "")}" href="days/{data["id"]}/"><img src="{thumb}" alt="">'
                    f'<div>{tag}<b>{html.escape(data.get("title", data["id"]))}</b>'
                    f'<span>{html.escape(data.get("date", ""))} · {data.get("slot", 1)}. paylaşım · {len(files)} slayt</span></div></a>')
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Işılda slaytları</title><style>{CSS}</style></head><body><main>
<h1>Işılda slaytları</h1><div class="sub">BUGÜN yazanı aç → Hepsini kaydet → TikTok'ta paylaş.</div>
{''.join(rows)}</main><script>
const t=new Date(),today=t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0');
let first=null;
document.querySelectorAll('a.day').forEach(a=>{{const d=a.dataset.date,b=a.querySelector('.new');
 if(d===today){{b.textContent='BUGÜN';first=first||a;}}
 else if(d<today){{a.style.opacity=.45;}}
 else{{b.textContent='SIRADA';b.style.color='var(--muted)';}}}});
if(first)first.scrollIntoView({{block:'center'}});
</script></body></html>"""


def main():
    force = sys.argv[sys.argv.index("--force") + 1] if "--force" in sys.argv else None
    days = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content", "*.json"))):
        data = json.load(open(path))
        out = os.path.join(SITE, "days", data["id"])
        langs = ["en"] + [l for l in ("tr",) if l in data]
        missing = any(not glob.glob(os.path.join(out, *([] if l == "en" else [l]), "[0-9][0-9].jpg")) for l in langs)
        if missing or force in (data["id"], "all"):
            fetch_assets.main(path)
            for l in langs:
                render.render(path, lang=l)
            print("rendered", data["id"], "+".join(langs))
        variants = []
        for l in langs:
            d = os.path.join(out, *([] if l == "en" else [l]))
            variants.append((l, render.localized(data, l), sorted(glob.glob(os.path.join(d, "[0-9][0-9].jpg")))))
        files = variants[0][2]
        with open(os.path.join(out, "index.html"), "w") as f:
            f.write(day_page(variants))
        days.append((data, files))
    days.sort(key=lambda d: (d[0].get("date", ""), d[0].get("slot", 1), d[0]["id"]))
    with open(os.path.join(SITE, "index.html"), "w") as f:
        f.write(index_page(days))
    open(os.path.join(SITE, ".nojekyll"), "w").close()


if __name__ == "__main__":
    main()
