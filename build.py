#!/usr/bin/env python3
"""
Carpenter Bali — static site generator.

Reads content/site.json + content/<lang>.json and writes a complete,
SEO-ready multilingual static website to ./public.

    python3 build.py

No dependencies beyond the Python 3 standard library.

Images: drop real photos into ./images using the file names shown on the
placeholders (e.g. images/kitchens.jpg, images/kitchens-canggu.jpg,
images/area-ubud.jpg). Supported: .webp .jpg .jpeg .png .avif.
Rebuild and the placeholders are replaced automatically.
"""
import datetime
import hashlib
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
IMAGES = os.path.join(ROOT, "images")
ASSETS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "public")
ICONS = os.path.join(ASSETS, "icons")
IMG_EXTS = (".webp", ".jpg", ".jpeg", ".png", ".avif")
TODAY = datetime.date.today().isoformat()

site = json.load(open(os.path.join(CONTENT, "site.json"), encoding="utf-8"))
DOMAIN = site["domain"].rstrip("/")
BRAND = site["brand"]

LANGS = {}
for code in site["languages"]:
    path = os.path.join(CONTENT, f"{code}.json")
    if os.path.exists(path):
        LANGS[code] = json.load(open(path, encoding="utf-8"))
    else:
        print(f"! content/{code}.json missing — skipping language '{code}'")
DEFAULT = site["default_lang"]
AREA_CFG = {a["key"]: a for a in site["areas"]}


def esc(s):
    return html.escape(str(s), quote=True)


def fill(s, **kw):
    s = s.replace("{brand}", BRAND)
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


# --------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------

def prefix(lang):
    p = LANGS[lang]["path_prefix"]
    return f"/{p}/" if p else "/"


def page_path(lang, pid):
    """Return the site-relative URL path for a page id in a language."""
    L = LANGS[lang]
    kind = pid[0]
    base = prefix(lang)
    if kind == "home":
        return base
    if kind == "index":
        return f"{base}{L['pages'][pid[1]]['slug']}/"
    if kind == "page":
        return f"{base}{L['pages'][pid[1]]['slug']}/"
    if kind == "service":
        return f"{base}{L['services'][pid[1]]['slug']}/"
    if kind == "area":
        return f"{base}{L['areas'][pid[1]]['slug']}/"
    if kind == "combo":
        return f"{base}{L['services'][pid[1]]['combo_slug']}-{pid[2]}/"
    if kind == "guide":
        return f"{base}{L['pages']['guides']['slug']}/{L['guides'][pid[1]]['slug']}/"
    raise ValueError(pid)


def abs_url(path):
    return DOMAIN + path


# --------------------------------------------------------------------------
# Images (real photo if present in ./images, otherwise generated SVG placeholder)
# --------------------------------------------------------------------------

_copied = {}


def find_image(*keys):
    for key in keys:
        for ext in IMG_EXTS:
            fp = os.path.join(IMAGES, key + ext)
            if os.path.exists(fp):
                if key + ext not in _copied:
                    os.makedirs(os.path.join(OUT, "images"), exist_ok=True)
                    shutil.copy2(fp, os.path.join(OUT, "images", key + ext))
                    _copied[key + ext] = True
                return f"/images/{key}{ext}", True
    return None, False


def placeholder(key):
    """Write a warm, wood-toned SVG placeholder that shows the file name to replace."""
    name = f"{key}.svg"
    out = os.path.join(OUT, "images", "placeholder", name)
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        h = int(hashlib.md5(key.encode()).hexdigest()[:2], 16)
        hue = 22 + h % 18
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="hsl({hue},38%,82%)"/><stop offset="1" stop-color="hsl({hue},32%,64%)"/></linearGradient>
<pattern id="w" width="1200" height="40" patternUnits="userSpaceOnUse"><path d="M0 20 Q300 {8 + h % 10} 600 20 T1200 20" fill="none" stroke="hsl({hue},30%,55%)" stroke-opacity=".25" stroke-width="2"/></pattern></defs>
<rect width="1200" height="800" fill="url(#g)"/><rect width="1200" height="800" fill="url(#w)"/>
<g transform="translate(600 360)" fill="none" stroke="hsl({hue},35%,30%)" stroke-opacity=".55" stroke-width="10" stroke-linecap="round" stroke-linejoin="round">
<rect x="-110" y="-80" width="220" height="160" rx="14"/><circle cx="0" cy="0" r="42"/><path d="M-60-80l20-28h80l20 28"/></g>
<text x="600" y="520" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="30" font-weight="600" fill="hsl({hue},35%,22%)" fill-opacity=".8">images/{esc(key)}.jpg</text>
</svg>"""
        open(out, "w", encoding="utf-8").write(svg)
    return f"/images/placeholder/{name}"


def img(keys, alt, cls="", eager=False, w=1600, h=1067, L=None, sizes=None):
    if isinstance(keys, str):
        keys = [keys]
    src, real = find_image(*keys)
    if not src:
        src = placeholder(keys[-1] if len(keys) > 1 else keys[0])
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    if sizes:
        load += f' sizes="{sizes}"'
    tag = (f'<img src="{src}" alt="{esc(alt)}" width="{w}" height="{h}" {load} '
           f'decoding="async"{(" class=" + chr(34) + cls + chr(34)) if cls else ""}>')
    if not real and L:
        return f'<span class="ph">{tag}<span class="ph-badge">{esc(L["ui"]["placeholder_img"])}</span></span>'
    return tag


def og_image(keys):
    src, real = find_image(*(list(keys) + ["og", "hero"]))
    return abs_url(src) if src else None


# --------------------------------------------------------------------------
# Structured data
# --------------------------------------------------------------------------

def business_ld(L):
    ld = {
        "@context": "https://schema.org",
        "@type": "HomeAndConstructionBusiness",
        "@id": DOMAIN + "/#business",
        "name": BRAND,
        "url": abs_url(prefix(L["lang"])),
        "telephone": "+" + site["whatsapp"],
        "email": site["email"],
        "priceRange": "Rp",
        "description": L["ui"]["footer_about"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": site["address_locality"],
            "addressRegion": site["address_region"],
            "addressCountry": site["address_country"],
        },
        "geo": {"@type": "GeoCoordinates", "latitude": site["geo"]["lat"], "longitude": site["geo"]["lng"]},
        "openingHours": site["opening_hours"],
        "areaServed": [{"@type": "Place", "name": f"{LANGS['en']['areas'][a['key']]['name']}, Bali"} for a in site["areas"]],
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+" + site["whatsapp"],
            "contactType": "customer service",
            "name": f"{site.get('contact_name', '')}, {L['ui'].get('contact_role', '')}".strip(" ,"),
            "availableLanguage": ["English", "Indonesian"],
        },
        "knowsLanguage": ["en", "id"],
    }
    same = [u for u in (site.get("instagram"), site.get("facebook")) if u]
    if same:
        ld["sameAs"] = same
    im = og_image([])
    if im:
        ld["image"] = im
    return ld


def faq_ld(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs],
    }


def crumbs_ld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": abs_url(u)}
                            for i, (n, u) in enumerate(items)],
    }


def service_ld(L, name, desc, url, area_names):
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": name,
        "serviceType": name,
        "description": desc,
        "url": abs_url(url),
        "provider": {"@id": DOMAIN + "/#business"},
        "areaServed": [{"@type": "Place", "name": n} for n in area_names],
        "inLanguage": L["hreflang"],
    }




# --------------------------------------------------------------------------
# Layout primitives
# --------------------------------------------------------------------------

CSS_VER = JS_VER = "1"


def font_preload(lang):
    sub = "cyrillic" if lang == "ru" else "latin"
    return "\n".join(f'<link rel="preload" as="font" type="font/woff2" href="/assets/fonts/{f}" crossorigin>'
                     for f in sorted(os.listdir(os.path.join(ASSETS, "fonts"))) if f"-normal-{sub}-" in f and "ext" not in f)


_icon_cache = {}


def icon(name, cls="i"):
    """Inline a Phosphor icon (assets/icons/<name>.svg)."""
    if name not in _icon_cache:
        _icon_cache[name] = open(os.path.join(ICONS, name + ".svg"), encoding="utf-8").read().strip()
    return _icon_cache[name].replace("<svg ", f'<svg class="{cls}" aria-hidden="true" focusable="false" ', 1)


def wa_link(L, text=""):
    from urllib.parse import quote
    greet = fill(L["ui"].get("wa_greeting", ""), name=site.get("contact_name", ""))
    return f"https://wa.me/{site['whatsapp']}?text={quote((greet + ' ' + text).strip())}"


def first_sentence(text):
    m = re.search(r"^(.+?[.!?])\s+(.+)$", text, re.S)
    return (m.group(1), m.group(2)) if m else (text, "")


def split_words(text, em_last=False):
    """Wrap each word for the masked headline reveal."""
    words = text.split()
    out = []
    for i, w in enumerate(words):
        inner = esc(w)
        if em_last and i == len(words) - 1:
            inner = f"<em>{inner}</em>"
        out.append(f'<span class="w"><span style="--i:{i}">{inner}</span></span>')
    return " ".join(out)


def svc_img(k):
    return find_image(k)[0] or placeholder(k)


LOGO = ('<svg class="logo-mark" width="30" height="30" viewBox="0 0 40 40" aria-hidden="true">'
        '<rect x="1" y="1" width="38" height="38" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path d="M10 29h20M13 29V18l7-6 7 6v11M18 29v-6h4v6" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linejoin="round"/></svg>')


def lang_switcher(L, pid):
    items = []
    for code, T in LANGS.items():
        cur = ' aria-current="true"' if code == L["lang"] else ""
        items.append(f'<li><a href="{page_path(code, pid)}" hreflang="{T["hreflang"]}" lang="{T["hreflang"]}" '
                     f'data-lang="{code}"{cur}><span class="lang-code">{T["short"]}</span>{esc(T["label"])}</a></li>')
    return (f'<details class="lang"><summary aria-label="{esc(L["ui"]["language"])}">{icon("globe-simple")}'
            f'<span>{L["short"]}</span></summary><ul>{"".join(items)}</ul></details>')


def header(L, pid):
    u, lg = L["ui"], L["lang"]
    nav = [(("index", "services"), u["nav_services"]), (("index", "areas"), u["nav_areas"]),
           (("index", "guides"), u["nav_guides"]), (("page", "about"), u["nav_about"]),
           (("page", "contact"), u["nav_contact"])]
    links = "".join(f'<li><a href="{page_path(lg, p)}"{" aria-current=" + chr(34) + "page" + chr(34) if p == pid else ""}>{esc(t)}</a></li>'
                    for p, t in nav)
    return f"""<a class="skip" href="#main">{esc(u['skip'])}</a>
<div class="ruler" aria-hidden="true"></div>
<header class="site-header"><div class="wrap header-inner">
<a class="logo" href="{prefix(lg)}" aria-label="{BRAND}, {esc(u['home'])}">{LOGO}<span>{BRAND}</span></a>
<nav class="nav" id="nav" aria-label="Main"><ul>{links}</ul></nav>
<div class="header-actions">{lang_switcher(L, pid)}
<a class="btn btn-sm header-cta" href="{wa_link(L)}" target="_blank" rel="noopener">{icon('whatsapp-logo')}<span>{esc(u['cta_whatsapp'])}</span></a>
<button class="nav-toggle" aria-controls="nav" aria-expanded="false" aria-label="{esc(u['menu'])}">{icon('list', 'i i-open')}{icon('x', 'i i-close')}</button>
</div></div></header>"""


def footer(L, pid):
    u, lg = L["ui"], L["lang"]
    svc = "".join(f'<li><a href="{page_path(lg, ("service", k))}">{esc(L["services"][k]["name"])}</a></li>' for k in site["services"])
    areas = "".join(f'<li><a href="{page_path(lg, ("area", a["key"]))}">{esc(L["areas"][a["key"]]["name"])}</a></li>' for a in site["areas"])
    langs = "".join(f'<a href="{page_path(c, pid)}" hreflang="{T["hreflang"]}" lang="{T["hreflang"]}">{esc(T["label"])}</a>' for c, T in LANGS.items())
    guides = "".join(f'<li><a href="{page_path(lg, ("guide", g))}">{esc(L["guides"][g]["h1"])}</a></li>' for g in site["guides"])
    return f"""<footer class="site-footer"><div class="wrap">
<div class="footer-top"><p class="footer-big">{esc(u['cta_band_title'])}</p>
<a class="btn" href="{wa_link(L)}" target="_blank" rel="noopener">{icon('whatsapp-logo')}<span>{esc(u['cta_whatsapp'])}</span></a></div>
<div class="footer-grid">
<div class="footer-brand"><a class="logo" href="{prefix(lg)}">{LOGO}<span>{BRAND}</span></a>
<p>{esc(u['footer_about'])}</p>
<p><strong>{esc(site.get('contact_name', ''))}</strong>, {esc(u.get('contact_role', ''))}<br>
<a href="{wa_link(L)}" target="_blank" rel="noopener">{esc(site['phone_display'])}</a><br>
<a href="mailto:{site['email']}">{site['email']}</a></p></div>
<div><h2>{esc(u['footer_services'])}</h2><ul class="cols-2">{svc}</ul></div>
<div><h2>{esc(u['footer_areas'])}</h2><ul class="cols-2">{areas}</ul></div>
<div><h2>{esc(u['footer_company'])}</h2><ul>
<li><a href="{page_path(lg, ('page', 'about'))}">{esc(u['nav_about'])}</a></li>
<li><a href="{page_path(lg, ('page', 'contact'))}">{esc(u['nav_contact'])}</a></li>
<li><a href="{page_path(lg, ('index', 'guides'))}">{esc(u['nav_guides'])}</a></li>{guides}</ul></div>
</div>
<div class="footer-bottom"><p>© {datetime.date.today().year} {BRAND}. {esc(u['footer_rights'])}</p><p class="footer-langs">{langs}</p></div>
</div></footer>
<a class="wa-float" href="{wa_link(L)}" target="_blank" rel="noopener" aria-label="{esc(u['cta_whatsapp'])}">{icon('whatsapp-logo')}</a>"""


def i18n_blob():
    return json.dumps({c: [T["ui"]["lang_suggest"], T["ui"]["lang_suggest_btn"], T["ui"]["close"]] for c, T in LANGS.items()},
                      ensure_ascii=False)


def layout(L, pid, title, meta, body, ld=(), og_keys=(), og_type="website", preload=None):
    lg = L["lang"]
    path = page_path(lg, pid)
    alts = "\n".join(f'<link rel="alternate" hreflang="{T["hreflang"]}" href="{abs_url(page_path(c, pid))}">' for c, T in LANGS.items())
    alts += f'\n<link rel="alternate" hreflang="x-default" href="{abs_url(page_path(DEFAULT, pid))}">'
    og_alt = "\n".join(f'<meta property="og:locale:alternate" content="{T["locale"]}">' for c, T in LANGS.items() if c != lg)
    im = og_image(og_keys)
    og_img = f'<meta property="og:image" content="{im}">\n<meta name="twitter:image" content="{im}">' if im else ""
    pre = f'<link rel="preload" as="image" href="{preload}" fetchpriority="high">' if preload else ""
    lds = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>'
                    for x in (business_ld(L),) + tuple(ld))
    return f"""<!doctype html>
<html lang="{L['hreflang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>document.documentElement.classList.add('js')</script>
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta)}">
<link rel="canonical" href="{abs_url(path)}">
{alts}
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(meta)}">
<meta property="og:url" content="{abs_url(path)}">
<meta property="og:locale" content="{L['locale']}">
{og_alt}
{og_img}
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0f1a15">
<meta name="color-scheme" content="dark">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
{pre}
{font_preload(lg)}
<link rel="stylesheet" href="/assets/css/style.css?v={CSS_VER}">
{lds}
</head>
<body data-lang="{lg}">
<div class="grain" aria-hidden="true"></div>
{header(L, pid)}
<main id="main">
{body}
</main>
{footer(L, pid)}
<script id="i18n" type="application/json">{i18n_blob()}</script>
<script src="/assets/js/main.js?v={JS_VER}" defer></script>
<script>window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};</script>
<script defer src="/_vercel/insights/script.js"></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------

def breadcrumbs(L, items):
    lis = "".join(f'<li aria-current="page">{esc(n)}</li>' if i == len(items) - 1 else f'<li><a href="{u}">{esc(n)}</a></li>'
                  for i, (n, u) in enumerate(items))
    return f'<nav class="crumbs" aria-label="{esc(L["ui"]["breadcrumb"])}"><ol>{lis}</ol></nav>'


def btn_wa(L, text="", cls="btn"):
    return f'<a class="{cls}" href="{wa_link(L, text)}" target="_blank" rel="noopener">{icon("whatsapp-logo")}<span>{esc(L["ui"]["cta_whatsapp"])}</span></a>'


def hero(L, h1, lead, keys, crumbs_html="", eyebrow="", wa_text="", home=False):
    u = L["ui"]
    keys = [keys] if isinstance(keys, str) else keys
    planks = "".join(f'<i style="--i:{i}"></i>' for i in range(5))
    return f"""<section class="hero{' hero-home' if home else ''}"><div class="wrap hero-grid">
<div class="hero-text">{crumbs_html}
{f'<p class="eyebrow">{esc(eyebrow)}</p>' if eyebrow else ''}
<h1 class="split">{split_words(h1, em_last=home)}</h1>
<p class="lead rise" style="--d:5">{esc(lead)}</p>
<div class="btns rise" style="--d:6">{btn_wa(L, wa_text)}<a class="btn btn-line" href="#quote">{esc(u['cta_quote'])}{icon('arrow-right')}</a></div>
</div>
<figure class="hero-media"><div class="hero-img"><div class="px">{img(keys, h1, eager=True, L=L, sizes="(max-width: 860px) 100vw, 50vw")}</div></div>
<div class="planks" aria-hidden="true">{planks}</div></figure>
</div></section>"""


def section(title, inner, cls="", sid="", lead=""):
    head = ""
    if title:
        head = f'<div class="sec-head rv"><h2>{esc(title)}</h2>{f"<p>{esc(lead)}</p>" if lead else ""}</div>'
    return (f'<section class="section {cls}"{f" id={chr(34)}{sid}{chr(34)}" if sid else ""}><div class="wrap">'
            f'{head}{inner}</div></section>')


def paras(ps):
    return "".join(f"<p>{esc(p)}</p>" for p in ps)


def points_strip(points):
    return ('<div class="points"><div class="wrap"><ul>' +
            "".join(f'<li class="rv" style="--i:{i}">{icon("check")}<span>{esc(p)}</span></li>' for i, p in enumerate(points)) +
            "</ul></div></div>")


def bento_why(L):
    t = L["ui"]["trust"]
    cells = [f'<div class="b-cell b-photo rv">{img("workshop", t[0]["t"], L=L, sizes="(max-width: 860px) 100vw, 60vw")}'
             f'<div class="b-over"><h3>{esc(t[0]["t"])}</h3><p>{esc(t[0]["d"])}</p></div></div>']
    for i, x in enumerate(t[1:], 1):
        cells.append(f'<div class="b-cell b-{i} rv" style="--i:{i}"><h3>{esc(x["t"])}</h3><p>{esc(x["d"])}</p></div>')
    return f'<div class="bento">{"".join(cells)}</div>'


def service_index(L, area=None):
    """Grouped index of services with a cursor-following photo preview on desktop."""
    lg, u = L["lang"], L["ui"]
    cols = []
    for gi, keys in enumerate(site["service_groups"]):
        rows = []
        for k in keys:
            S = L["services"][k]
            url = page_path(lg, ("combo", k, area) if area else ("service", k))
            src = svc_img(k)
            rows.append(f'<li><a href="{url}" data-img="{src}"><img src="{src}" alt="" width="1600" height="1067" loading="lazy" decoding="async">'
                        f'<span class="ix-name">{esc(S["name"])}</span>{icon("arrow-up-right")}</a></li>')
        cols.append(f'<div class="ix-col rv" style="--i:{gi}"><h3>{esc(u["groups"][gi])}</h3><ul>{"".join(rows)}</ul></div>')
    return f'<div class="ix">{"".join(cols)}<div class="ix-preview" aria-hidden="true"><img alt="" width="1600" height="1067"></div></div>'


def material_explorer(L):
    u = L["ui"]
    tabs, panels = [], []
    for i, (m, cfg) in enumerate(zip(u["materials"], site["materials"])):
        sel = "true" if i == 0 else "false"
        tabs.append(f'<button role="tab" id="mt-{cfg["key"]}" aria-controls="mp-{cfg["key"]}" aria-selected="{sel}"'
                    f'{"" if i == 0 else " tabindex=" + chr(34) + "-1" + chr(34)}>{esc(m["name"])}</button>')
        bars = "".join(f'<div class="bar"><dt>{esc(lbl)}</dt><dd><span class="track"><span class="fill" style="--v:{v / 5}"></span></span>'
                       f'<span class="val">{v}/5</span></dd></div>' for lbl, v in zip(u["mat_labels"], cfg["ratings"]))
        panels.append(f"""<div class="m-panel" role="tabpanel" id="mp-{cfg['key']}" aria-labelledby="mt-{cfg['key']}">
<div class="m-img">{img(cfg['image'], m['name'], L=L, sizes="(max-width: 860px) 100vw, 45vw")}</div>
<div class="m-body"><h3>{esc(m['name'])}</h3><p>{esc(m['d'])}</p>
<p class="m-best"><strong>{esc(u['mat_best'])}:</strong> {esc(m['best'])}</p>
<dl class="bars">{bars}</dl><p class="note">{esc(u['mat_scale'])}</p></div></div>""")
    return f'<div class="mx rv"><div class="m-tabs" role="tablist" aria-label="{esc(u["materials_explorer_title"])}">{"".join(tabs)}</div>{"".join(panels)}</div>'


def timeline(L):
    steps = "".join(f'<li class="rv"><h3>{esc(p["t"])}</h3><p>{esc(p["d"])}</p></li>' for p in L["ui"]["process"])
    return f'<div class="tl"><div class="tl-line" aria-hidden="true"><span></span></div><ol>{steps}</ol></div>'


def marquee(L, keys, service=None):
    lg = L["lang"]

    def items(hidden):
        out = []
        for a in keys:
            A = L["areas"][a]
            url = page_path(lg, ("combo", service, a) if service else ("area", a))
            tab = ' tabindex="-1"' if hidden else ""
            out.append(f'<li><a href="{url}"{tab}>{esc(A["name"])}</a>{icon("map-pin")}</li>')
        return "".join(out)
    return (f'<div class="mq"><ul class="mq-track">{items(False)}</ul>'
            f'<ul class="mq-track" aria-hidden="true">{items(True)}</ul></div>')


def chips(L, keys, service=None):
    lg = L["lang"]
    out = []
    for a in keys:
        A = L["areas"][a]
        if service:
            url, label = page_path(lg, ("combo", service, a)), fill(L["services"][service]["combo_h1"], in_area=A["in_area"], area=A["name"])
        else:
            url, label = page_path(lg, ("area", a)), A["name"]
        out.append(f'<li><a href="{url}">{icon("map-pin")}<span>{esc(label)}</span></a></li>')
    return f'<ul class="chips rv">{"".join(out)}</ul>'


def spec_grid(items):
    return '<dl class="spec">' + "".join(
        f'<div class="rv" style="--i:{i % 2}"><dt>{esc(f["t"])}</dt><dd>{esc(f["d"])}</dd></div>' for i, f in enumerate(items)) + "</dl>"


def notes_bento(L, A, kw, image_keys):
    u = L["ui"]
    n = [(fill(u["local_title"], **kw), A["climate"]), (fill(u["style_title"], **kw), A["style"]), (fill(u["homes_title"], **kw), A["homes"])]
    return f"""<div class="notes">
<div class="n-main rv"><div class="n-img">{img(image_keys, n[0][0], L=L, sizes="(max-width: 860px) 100vw, 55vw")}</div><div class="n-txt"><h2>{esc(n[0][0])}</h2><p>{esc(n[0][1])}</p></div></div>
<div class="n-side"><div class="rv" style="--i:1"><h2>{esc(n[1][0])}</h2><p>{esc(n[1][1])}</p></div>
<div class="rv" style="--i:2"><h2>{esc(n[2][0])}</h2><p>{esc(n[2][1])}</p></div></div></div>"""


def price_table(L, rows, lead_time=None):
    u = L["ui"]
    trs = "".join(f'<tr><th scope="row">{esc(r[0])}</th><td>{esc(r[1])}</td></tr>' for r in rows)
    lt = f'<p class="lead-time"><span>{esc(u["lead_time"])}</span><strong>{esc(lead_time)}</strong></p>' if lead_time else ""
    return f"""<div class="price rv"><div class="table-wrap"><table class="prices"><thead><tr><th scope="col">{esc(u['pricing_item'])}</th><th scope="col">{esc(u['pricing_price'])}</th></tr></thead>
<tbody>{trs}</tbody></table></div><aside>{lt}<p class="note">{esc(u['pricing_note'])}</p></aside></div>"""


def faq_block(faqs):
    return '<div class="faq">' + "".join(
        f'<details class="rv"><summary><span>{esc(f["q"])}</span>{icon("plus")}</summary><div><p>{esc(f["a"])}</p></div></details>'
        for f in faqs) + "</div>"


def carousel(L, keys, area=None):
    lg, u = L["lang"], L["ui"]
    tiles = []
    for k in keys:
        S = L["services"][k]
        if area:
            url, title = page_path(lg, ("combo", k, area)), fill(S["combo_h1"], in_area=L["areas"][area]["in_area"], area=L["areas"][area]["name"])
            im = img([f"{k}-{area}", k], title, L=L, sizes="(max-width: 600px) 80vw, 30vw")
        else:
            url, title = page_path(lg, ("service", k)), S["name"]
            im = img(k, title, L=L, sizes="(max-width: 600px) 80vw, 30vw")
        tiles.append(f'<li><a href="{url}"><div class="c-img">{im}</div><h3>{esc(title)}</h3><p>{esc(S["short"])}</p></a></li>')
    return f'<div class="car rv"><ul class="car-track">{"".join(tiles)}</ul><p class="car-hint">{esc(u["scroll_hint"])} {icon("arrow-right")}</p></div>'


def mosaic(items):
    """items: list of (url, title, text, image_html). Varied tile sizes."""
    out = []
    for i, (url, title, text, im) in enumerate(items):
        out.append(f'<li class="mo-{i % 7} rv" style="--i:{i % 3}"><a href="{url}"><div class="mo-img">{im}</div>'
                   f'<div class="mo-txt"><h3>{esc(title)}</h3><p>{esc(text)}</p></div></a></li>')
    return f'<ul class="mosaic">{"".join(out)}</ul>'


def quote_form(L, service=None, area=None):
    u = L["ui"]
    svc_opts = "".join(f'<option value="{esc(L["services"][k]["name"])}"{" selected" if k == service else ""}>{esc(L["services"][k]["name"])}</option>'
                       for k in site["services"])
    area_opts = "".join(f'<option value="{esc(L["areas"][a["key"]]["name"])}"{" selected" if a["key"] == area else ""}>{esc(L["areas"][a["key"]]["name"])}</option>'
                        for a in site["areas"])
    name = site.get("contact_name", "")
    return f"""<section class="section quote" id="quote"><div class="wrap q-grid">
<div class="q-text rv"><h2>{esc(u['cta_band_title'])}</h2><p>{esc(u['cta_band_text'])}</p>
<div class="contact-card"><div class="avatar" aria-hidden="true">{esc(name[:1])}</div>
<div><strong>{esc(name)}</strong><span>{esc(u.get('contact_role', ''))}</span>
<a href="{wa_link(L)}" target="_blank" rel="noopener">{icon('whatsapp-logo')}{esc(site['phone_display'])}</a></div></div>
<p class="small">{esc(fill(u.get('contact_direct', ''), name=name))}</p></div>
<form class="quote-form rv" style="--i:1" data-wa="{site['whatsapp']}" data-greeting="{esc(fill(u.get('wa_greeting', ''), name=name))}" action="https://wa.me/{site['whatsapp']}" method="get" target="_blank">
<h3>{esc(u['form_title'])}</h3>
<label>{esc(u['form_name'])}<input name="name" autocomplete="name" required></label>
<div class="row2"><label>{esc(u['form_service'])}<select name="service"><option value="">{esc(u['form_select'])}</option>{svc_opts}<option value="{esc(u['form_other'])}">{esc(u['form_other'])}</option></select></label>
<label>{esc(u['form_area'])}<select name="area"><option value="">{esc(u['form_select'])}</option>{area_opts}<option value="{esc(u['form_other'])}">{esc(u['form_other'])}</option></select></label></div>
<label>{esc(u['form_message'])}<textarea name="text" rows="4"></textarea></label>
<button class="btn btn-block" type="submit">{icon('whatsapp-logo')}<span>{esc(u['form_send'])}</span></button>
<p class="small center"><a href="mailto:{site['email']}">{esc(u['form_email'])}: {site['email']}</a></p>
</form></div></section>"""


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

pages_written = []


def write(lang, pid, content):
    fp = os.path.join(OUT, page_path(lang, pid).strip("/"), "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(content)
    if lang == DEFAULT:
        pages_written.append(pid)


def pre(keys):
    keys = [keys] if isinstance(keys, str) else keys
    return find_image(*keys)[0]


def build_home(L):
    lg, u, H = L["lang"], L["ui"], L["home"]
    pid = ("home",)
    body = hero(L, H["h1"], H["lead"], "hero", eyebrow=H["eyebrow"], home=True)
    body += points_strip(H["points"])
    body += section(u["why_title"], bento_why(L), "sec-why")
    body += section(u["services_title"], service_index(L), "sec-ix", sid="services", lead=u["services_lead"])
    intro = f"""<div class="intro"><div class="intro-txt rv"><h2>{esc(H['intro_title'])}</h2>{paras(fill(p) for p in H['intro'])}</div>
<div class="intro-mx"><div class="sec-head rv"><h2 class="h-sm">{esc(u['materials_explorer_title'])}</h2><p>{esc(u['materials_explorer_lead'])}</p></div>{material_explorer(L)}</div></div>"""
    body += section("", intro, "sec-intro")
    body += section("", f'<div class="tl-wrap"><div class="tl-head rv"><h2>{esc(u["process_title"])}</h2></div>{timeline(L)}</div>', "sec-tl")
    body += f'<section class="section sec-areas"><div class="wrap"><div class="sec-head rv"><h2>{esc(u["areas_title"])}</h2><p>{esc(H["areas_teaser"])}</p></div></div>{marquee(L, [a["key"] for a in site["areas"]])}</section>'
    guides = "".join(f"""<a class="g-link rv" style="--i:{i}" href="{page_path(lg, ('guide', g))}"><div class="g-img">{img('guide-' + g, L['guides'][g]['h1'], L=L, sizes="(max-width: 860px) 100vw, 50vw")}</div>
<h3>{esc(L['guides'][g]['h1'])}</h3><p>{esc(L['guides'][g]['meta'])}</p><span class="more">{esc(u['read_more'])}{icon('arrow-right')}</span></a>""" for i, g in enumerate(site["guides"]))
    body += section(u["guides_title"], f'<div class="guides">{guides}</div>', "sec-guides")
    body += section(u["faq_title"], faq_block(u["faq_general"]), "sec-faq narrow-sec")
    body += quote_form(L)
    website_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": abs_url(prefix(lg)), "inLanguage": L["hreflang"]}
    write(lg, pid, layout(L, pid, H["title"], H["meta"], body, ld=(website_ld, faq_ld(u["faq_general"])), og_keys=["hero"], preload=pre("hero")))


def build_services_index(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["services"]
    pid = ("index", "services")
    cr = [(u["home"], prefix(lg)), (P["h1"], page_path(lg, pid))]
    body = hero(L, P["h1"], first_sentence(u["services_lead"])[0], "services", breadcrumbs(L, cr))
    items = [(page_path(lg, ("service", k)), L["services"][k]["name"], L["services"][k]["short"],
              img(k, L["services"][k]["name"], L=L, sizes="(max-width: 860px) 100vw, 40vw")) for k in site["services"]]
    body += section("", mosaic(items))
    body += section("", f'<div class="tl-wrap"><div class="tl-head rv"><h2>{esc(u["process_title"])}</h2></div>{timeline(L)}</div>', "sec-tl")
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),), preload=pre("services")))


def build_areas_index(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["areas"]
    pid = ("index", "areas")
    cr = [(u["home"], prefix(lg)), (P["h1"], page_path(lg, pid))]
    body = hero(L, P["h1"], first_sentence(u["areas_lead"])[0], "areas", breadcrumbs(L, cr))
    items = [(page_path(lg, ("area", a["key"])), L["areas"][a["key"]]["h1"], first_sentence(L["areas"][a["key"]]["intro"])[0],
              img("area-" + a["key"], L["areas"][a["key"]]["h1"], L=L, sizes="(max-width: 860px) 100vw, 40vw")) for a in site["areas"]]
    body += section("", mosaic(items))
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),), preload=pre("areas")))


def build_service(L, k):
    lg, u, S = L["lang"], L["ui"], L["services"][k]
    pid = ("service", k)
    cr = [(u["home"], prefix(lg)), (L["pages"]["services"]["h1"], page_path(lg, ("index", "services"))), (S["name"], page_path(lg, pid))]
    body = hero(L, S["h1"], S["short"], k, breadcrumbs(L, cr), wa_text=S["name"])
    body += section("", f"""<div class="two-col"><div class="prose rv">{paras(fill(p) for p in S['intro'])}</div>
<aside class="aside rv" style="--i:1"><h2 class="h-sm">{esc(u['materials_title'])}</h2><p>{esc(S['materials'])}</p></aside></div>""")
    body += section(u["features_title"], spec_grid(S["features"]), "sec-spec")
    body += section(u["pricing_title"], price_table(L, S["price"], S["lead_time"]))
    body += section(fill(u["service_areas_title"], service=S["name"]), chips(L, [a["key"] for a in site["areas"]], k), "sec-chips")
    body += section("", f'<div class="tl-wrap"><div class="tl-head rv"><h2>{esc(u["process_title"])}</h2></div>{timeline(L)}</div>', "sec-tl")
    faqs = S["faqs"] + u["faq_general"]
    body += section(u["faq_title"], faq_block(faqs), "narrow-sec")
    body += section(u["services_title"], carousel(L, [s for s in site["services"] if s != k][:8]), "sec-car")
    body += quote_form(L, service=k)
    area_names = [L["areas"][a["key"]]["name"] + ", Bali" for a in site["areas"]]
    lds = (service_ld(L, S["name"], S["meta"], page_path(lg, pid), area_names), faq_ld(faqs), crumbs_ld(cr))
    write(lg, pid, layout(L, pid, S["title"], S["meta"], body, ld=lds, og_keys=[k], preload=pre(k)))


def build_area(L, a):
    lg, u, A = L["lang"], L["ui"], L["areas"][a]
    kw = dict(in_area=A["in_area"], area=A["name"])
    pid = ("area", a)
    cr = [(u["home"], prefix(lg)), (L["pages"]["areas"]["h1"], page_path(lg, ("index", "areas"))), (A["name"], page_path(lg, pid))]
    lead, rest = first_sentence(A["intro"])
    body = hero(L, A["h1"], lead, "area-" + a, breadcrumbs(L, cr), wa_text=A["name"])
    if rest:
        body += section("", f'<div class="prose big rv"><p>{esc(rest)}</p></div>')
    body += section("", notes_bento(L, A, kw, "area-" + a), "sec-notes")
    body += section(fill(u["services_in_area"], **kw), service_index(L, area=a), "sec-ix")
    body += section("", f'<div class="tl-wrap"><div class="tl-head rv"><h2>{esc(u["process_title"])}</h2></div>{timeline(L)}</div>', "sec-tl")
    faqs = A["faqs"] + u["faq_general"]
    body += section(u["faq_title"], faq_block(faqs), "narrow-sec")
    body += section(u["areas_title"], chips(L, AREA_CFG[a]["nearby"]), "sec-chips")
    body += quote_form(L, area=a)
    place_ld = {"@context": "https://schema.org", "@type": "Service", "name": A["h1"], "url": abs_url(page_path(lg, pid)),
                "provider": {"@id": DOMAIN + "/#business"},
                "areaServed": {"@type": "Place", "name": A["name"] + ", Bali",
                               "geo": {"@type": "GeoCoordinates", "latitude": AREA_CFG[a]["lat"], "longitude": AREA_CFG[a]["lng"]}}}
    write(lg, pid, layout(L, pid, A["title"], A["meta"], body, ld=(place_ld, faq_ld(faqs), crumbs_ld(cr)), og_keys=["area-" + a], preload=pre("area-" + a)))


def build_combo(L, k, a):
    lg, u, S, A = L["lang"], L["ui"], L["services"][k], L["areas"][a]
    kw = dict(in_area=A["in_area"], area=A["name"], service=S["name"])
    pid = ("combo", k, a)
    h1 = fill(S["combo_h1"], **kw)
    cr = [(u["home"], prefix(lg)), (S["name"], page_path(lg, ("service", k))), (A["name"], page_path(lg, ("area", a))), (h1, page_path(lg, pid))]
    lead, rest = first_sentence(fill(S["combo_intro"], **kw))
    body = hero(L, h1, lead, [f"{k}-{a}", k], breadcrumbs(L, cr), wa_text=h1)
    body += section("", f"""<div class="two-col"><div class="prose rv">{f'<p class="big">{esc(rest)}</p>' if rest else ''}{paras(fill(p, **kw) for p in S['intro'])}</div>
<aside class="aside rv" style="--i:1"><h2 class="h-sm">{esc(u['materials_title'])}</h2><p>{esc(S['materials'])}</p></aside></div>""")
    body += section("", notes_bento(L, A, kw, "area-" + a), "sec-notes")
    body += section(u["features_title"], spec_grid(S["features"]), "sec-spec")
    body += section(u["pricing_title"], price_table(L, S["price"], S["lead_time"]))
    faqs = [{"q": fill(f["q"], **kw), "a": fill(f["a"], **kw)} for f in S["combo_faqs"]] + S["faqs"][:2] + A["faqs"]
    body += section(u["faq_title"], faq_block(faqs), "narrow-sec")
    body += section(fill(u["nearby_areas"], **kw), chips(L, AREA_CFG[a]["nearby"], k), "sec-chips")
    body += section(fill(u["related_services"], **kw), carousel(L, [s for s in site["services"] if s != k][:8], area=a), "sec-car")
    body += quote_form(L, service=k, area=a)
    sld = service_ld(L, h1, fill(S["combo_meta"], **kw), page_path(lg, pid), [A["name"] + ", Bali"])
    write(lg, pid, layout(L, pid, fill(S["combo_title"], **kw), fill(S["combo_meta"], **kw), body,
                          ld=(sld, faq_ld(faqs), crumbs_ld(cr)), og_keys=[f"{k}-{a}", k], preload=pre([f"{k}-{a}", k])))


def build_about(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["about"]
    pid = ("page", "about")
    h1 = fill(P["h1"])
    cr = [(u["home"], prefix(lg)), (u["nav_about"], page_path(lg, pid))]
    lead, rest = first_sentence(fill(P["body"][0]))
    body = hero(L, h1, lead, "about", breadcrumbs(L, cr))
    body += section("", f'<div class="two-col"><div class="prose rv">{f"<p class=big>{esc(rest)}</p>" if rest else ""}{paras(fill(p) for p in P["body"][1:])}</div>'
                        f'<div class="aside-img rv" style="--i:1">{img("workshop", h1, L=L, sizes="(max-width: 860px) 100vw, 40vw")}</div></div>')
    body += section(P["values_title"], spec_grid(P["values"]), "sec-spec")
    body += section(u["why_title"], bento_why(L), "sec-why")
    body += section("", f'<div class="tl-wrap"><div class="tl-head rv"><h2>{esc(u["process_title"])}</h2></div>{timeline(L)}</div>', "sec-tl")
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),), preload=pre("about")))


def build_contact(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["contact"]
    pid = ("page", "contact")
    cr = [(u["home"], prefix(lg)), (u["nav_contact"], page_path(lg, pid))]
    body = f"""<section class="hero hero-slim"><div class="wrap">{breadcrumbs(L, cr)}<h1 class="split">{split_words(P['h1'])}</h1><p class="lead rise" style="--d:3">{esc(P['lead'])}</p></div></section>"""
    body += quote_form(L)
    body += section("", f"""<dl class="spec spec-3">
<div class="rv"><dt>WhatsApp</dt><dd><strong>{esc(site.get('contact_name', ''))}</strong>, {esc(u.get('contact_role', ''))}<br><a href="{wa_link(L)}" target="_blank" rel="noopener">{esc(site['phone_display'])}</a><br><a href="mailto:{site['email']}">{site['email']}</a></dd></div>
<div class="rv" style="--i:1"><dt>{esc(P['hours_title'])}</dt><dd>{esc(P['hours'])}</dd></div>
<div class="rv" style="--i:2"><dt>{esc(P['area_title'])}</dt><dd>{esc(P['area'])}</dd></div></dl>""")
    body += section(u["areas_title"], chips(L, [a["key"] for a in site["areas"]]), "sec-chips")
    body += section(u["faq_title"], faq_block(u["faq_general"]), "narrow-sec")
    cp = {"@context": "https://schema.org", "@type": "ContactPage", "name": P["h1"], "url": abs_url(page_path(lg, pid)), "about": {"@id": DOMAIN + "/#business"}}
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(cp, crumbs_ld(cr), faq_ld(u["faq_general"]))))


def build_guides_index(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["guides"]
    pid = ("index", "guides")
    cr = [(u["home"], prefix(lg)), (P["h1"], page_path(lg, pid))]
    guides = "".join(f"""<a class="g-link rv" style="--i:{i}" href="{page_path(lg, ('guide', g))}"><div class="g-img">{img('guide-' + g, L['guides'][g]['h1'], L=L, sizes="(max-width: 860px) 100vw, 50vw")}</div>
<h2 class="h-sm">{esc(L['guides'][g]['h1'])}</h2><p>{esc(L['guides'][g]['intro'])}</p><span class="more">{esc(u['read_more'])}{icon('arrow-right')}</span></a>""" for i, g in enumerate(site["guides"]))
    body = f"""<section class="hero hero-slim"><div class="wrap">{breadcrumbs(L, cr)}<h1 class="split">{split_words(P['h1'])}</h1><p class="lead rise" style="--d:3">{esc(u['guides_lead'])}</p></div></section>"""
    body += section("", f'<div class="guides">{guides}</div>')
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),)))


def build_guide(L, g):
    lg, u, G = L["lang"], L["ui"], L["guides"][g]
    pid = ("guide", g)
    cr = [(u["home"], prefix(lg)), (L["pages"]["guides"]["h1"], page_path(lg, ("index", "guides"))), (G["h1"], page_path(lg, pid))]
    toc = "".join(f'<li><a href="#s{i + 1}">{esc(s["h"])}</a></li>' for i, s in enumerate(G["sections"]))
    secs = "".join(f'<h2 id="s{i + 1}">{esc(s["h"])}</h2>{paras(s["p"])}' for i, s in enumerate(G["sections"]))
    body = f"""<article><header class="hero hero-slim"><div class="wrap narrow">{breadcrumbs(L, cr)}<h1 class="split">{split_words(G['h1'])}</h1>
<p class="lead rise" style="--d:4">{esc(G['intro'])}</p><p class="small rise" style="--d:5">{esc(u['updated'])}: <time datetime="{TODAY}">{TODAY}</time></p></div></header>
<div class="section"><div class="wrap article-grid"><nav class="toc"><ol>{toc}</ol></nav><div class="prose article">
<div class="a-img">{img('guide-' + g, G['h1'], eager=True, L=L, sizes="(max-width: 860px) 100vw, 60vw")}</div>{secs}</div></div></div></article>"""
    related = ["kitchens", "wardrobes", "bathroom-vanities", "walk-in-wardrobes"] if g == "kitchen-cost" else ["doors-windows", "decking", "custom-furniture", "staircases"]
    body += section(u["services_title"], carousel(L, related), "sec-car")
    body += quote_form(L)
    art = {"@context": "https://schema.org", "@type": "Article", "headline": G["h1"], "description": G["meta"],
           "inLanguage": L["hreflang"], "datePublished": TODAY, "dateModified": TODAY,
           "author": {"@id": DOMAIN + "/#business"}, "publisher": {"@id": DOMAIN + "/#business"},
           "mainEntityOfPage": abs_url(page_path(lg, pid))}
    write(lg, pid, layout(L, pid, G["title"], G["meta"], body, ld=(art, crumbs_ld(cr)), og_keys=["guide-" + g], og_type="article"))


def build_404():
    L = LANGS[DEFAULT]
    u, P = L["ui"], L["pages"]["notfound"]
    body = f"""<section class="hero hero-slim"><div class="wrap"><h1 class="split">{split_words(P['h1'])}</h1><p class="lead rise" style="--d:3">{esc(P['text'])}</p>
<p class="btns rise" style="--d:4"><a class="btn" href="{page_path(DEFAULT, ('index', 'services'))}">{esc(u['cta_all_services'])}</a>
<a class="btn btn-line" href="{page_path(DEFAULT, ('index', 'areas'))}">{esc(u['cta_all_areas'])}</a></p></div></section>"""
    body += section("", service_index(L))
    html_ = layout(L, ("home",), P["title"], P["text"], body).replace(
        '<meta name="robots" content="index, follow, max-image-preview:large">', '<meta name="robots" content="noindex">')
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(html_)


def build_sitemap():
    urls = []
    for pid in pages_written:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{T["hreflang"]}" href="{abs_url(page_path(c, pid))}"/>' for c, T in LANGS.items())
        alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{abs_url(page_path(DEFAULT, pid))}"/>'
        pr = {"home": "1.0", "service": "0.9", "area": "0.8", "combo": "0.7"}.get(pid[0], "0.6")
        for c in LANGS:
            urls.append(f"<url><loc>{abs_url(page_path(c, pid))}</loc><lastmod>{TODAY}</lastmod><priority>{pr}</priority>{alts}</url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(xml)
    return len(urls)


def check_slugs():
    for c in LANGS:
        seen = {}
        pids = [("home",)] + [("index", p) for p in ("services", "areas", "guides")] + [("page", p) for p in ("about", "contact")]
        pids += [("service", k) for k in site["services"]] + [("area", a["key"]) for a in site["areas"]]
        pids += [("combo", k, a["key"]) for k in site["services"] for a in site["areas"]] + [("guide", g) for g in site["guides"]]
        for pid in pids:
            p = page_path(c, pid)
            if p in seen:
                raise SystemExit(f"Duplicate URL in {c}: {p} ({pid} vs {seen[p]})")
            if not re.fullmatch(r"[a-z0-9/\-]+", p):
                raise SystemExit(f"Non-ASCII/invalid URL in {c}: {p}")
            seen[p] = pid


def main():
    global CSS_VER, JS_VER
    check_slugs()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    shutil.copytree(ASSETS, os.path.join(OUT, "assets"), ignore=shutil.ignore_patterns("icons"))
    CSS_VER = hashlib.md5(open(os.path.join(ASSETS, "css", "style.css"), "rb").read()).hexdigest()[:8]
    JS_VER = hashlib.md5(open(os.path.join(ASSETS, "js", "main.js"), "rb").read()).hexdigest()[:8]
    for f in os.listdir(os.path.join(ROOT, "static")):
        shutil.copy2(os.path.join(ROOT, "static", f), os.path.join(OUT, f))
    for L in LANGS.values():
        build_home(L)
        build_services_index(L)
        build_areas_index(L)
        build_guides_index(L)
        build_about(L)
        build_contact(L)
        for k in site["services"]:
            build_service(L, k)
            for a in site["areas"]:
                build_combo(L, k, a["key"])
        for a in site["areas"]:
            build_area(L, a["key"])
        for g in site["guides"]:
            build_guide(L, g)
    build_404()
    n = build_sitemap()
    open(os.path.join(OUT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
    print(f"Built {n} pages in {len(LANGS)} languages ({', '.join(LANGS)}) → {OUT}")


if __name__ == "__main__":
    main()
