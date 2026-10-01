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
PLACEHOLDER_ICONS = {
    "default": '<path d="M-90 40h180M-70 40v-70h140v70M-70-30l70-50 70 50" />',
}


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


def img(keys, alt, cls="", eager=False, w=1200, h=800, L=None):
    if isinstance(keys, str):
        keys = [keys]
    src, real = find_image(*keys)
    if not src:
        src = placeholder(keys[-1] if len(keys) > 1 else keys[0])
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
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
            "name": f"{site.get('contact_name', '')} — {L['ui'].get('contact_role', '')}".strip(" —"),
            "availableLanguage": ["English", "Indonesian", "French", "Russian"],
        },
        "knowsLanguage": ["en", "id", "fr", "ru"],
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
# Layout
# --------------------------------------------------------------------------

CSS_VER = JS_VER = "1"


def wa_link(L, text=""):
    greet = fill(L["ui"].get("wa_greeting", ""), name=site.get("contact_name", ""))
    msg = (greet + " " + text).strip()
    from urllib.parse import quote
    return f"https://wa.me/{site['whatsapp']}?text={quote(msg)}"


def lang_switcher(L, pid):
    cur = L["lang"]
    items = []
    for code, T in LANGS.items():
        active = ' aria-current="true"' if code == cur else ""
        items.append(f'<li><a href="{page_path(code, pid)}" hreflang="{T["hreflang"]}" lang="{T["hreflang"]}" '
                     f'data-lang="{code}"{active}><span class="lang-code">{T["short"]}</span> {esc(T["label"])}</a></li>')
    return f"""<details class="lang">
<summary aria-label="{esc(L['ui']['language'])}"><svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.8" d="M12 3a9 9 0 100 18 9 9 0 000-18zm0 0c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9m0-18C9.5 5.6 8.2 8.6 8.2 12s1.3 6.4 3.8 9M3.5 9h17M3.5 15h17"/></svg><span>{L['short']}</span></summary>
<ul>{''.join(items)}</ul></details>"""


LOGO = ('<svg class="logo-mark" width="34" height="34" viewBox="0 0 40 40" aria-hidden="true">'
        '<rect width="40" height="40" rx="9" fill="currentColor"/>'
        '<path d="M10 28h20M12 28V17l8-6 8 6v11M17 28v-6h6v6" fill="none" stroke="#fff" stroke-width="2.4" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def header(L, pid):
    u = L["ui"]
    nav = [
        (("index", "services"), u["nav_services"]),
        (("index", "areas"), u["nav_areas"]),
        (("index", "guides"), u["nav_guides"]),
        (("page", "about"), u["nav_about"]),
        (("page", "contact"), u["nav_contact"]),
    ]
    links = "".join(
        f'<li><a href="{page_path(L["lang"], p)}"{" aria-current=" + chr(34) + "page" + chr(34) if p == pid else ""}>{esc(t)}</a></li>'
        for p, t in nav)
    return f"""<a class="skip" href="#main">{esc(u['skip'])}</a>
<header class="site-header"><div class="wrap header-inner">
<a class="logo" href="{prefix(L['lang'])}" aria-label="{BRAND} — {esc(u['home'])}">{LOGO}<span>{BRAND}</span></a>
<nav class="nav" id="nav" aria-label="Main"><ul>{links}</ul></nav>
<div class="header-actions">{lang_switcher(L, pid)}
<a class="btn btn-sm btn-wa header-cta" href="{wa_link(L)}" target="_blank" rel="noopener">{WA_ICON}<span>{esc(u['cta_whatsapp'])}</span></a>
<button class="nav-toggle" aria-controls="nav" aria-expanded="false" aria-label="{esc(u['menu'])}"><span></span><span></span><span></span></button>
</div></div></header>"""


WA_ICON = ('<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 00-8.6 15.1L2 22l5-1.3A10 10 0 1012 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1112 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 01-3.3-2.9c-.2-.4.2-.4.7-1.3a.5.5 0 000-.4l-.8-1.9c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 00-.7.3 3 3 0 00-.9 2.2 5.2 5.2 0 001.1 2.8 11.9 11.9 0 004.6 4c1.7.7 2.4.8 3.2.7a2.8 2.8 0 001.8-1.3 2.3 2.3 0 00.2-1.3c-.1-.1-.3-.2-.6-.3z"/></svg>')


def footer(L, pid):
    u = L["ui"]
    lg = L["lang"]
    svc = "".join(f'<li><a href="{page_path(lg, ("service", k))}">{esc(L["services"][k]["name"])}</a></li>'
                  for k in site["services"])
    areas = "".join(f'<li><a href="{page_path(lg, ("area", a["key"]))}">{esc(L["areas"][a["key"]]["name"])}</a></li>'
                    for a in site["areas"])
    langs = " · ".join(f'<a href="{page_path(c, pid)}" hreflang="{T["hreflang"]}" lang="{T["hreflang"]}">{esc(T["label"])}</a>'
                       for c, T in LANGS.items())
    guides = "".join(f'<li><a href="{page_path(lg, ("guide", g))}">{esc(L["guides"][g]["h1"])}</a></li>' for g in site["guides"])
    return f"""<footer class="site-footer"><div class="wrap footer-grid">
<div class="footer-brand"><a class="logo logo-light" href="{prefix(lg)}">{LOGO}<span>{BRAND}</span></a>
<p>{esc(u['footer_about'])}</p>
<p class="footer-contact"><strong>{esc(site.get('contact_name', ''))}</strong> — {esc(u.get('contact_role', ''))}<br>
<a href="{wa_link(L)}" target="_blank" rel="noopener">WhatsApp {esc(site['phone_display'])}</a><br>
<a href="mailto:{site['email']}">{site['email']}</a></p></div>
<div><h2>{esc(u['footer_services'])}</h2><ul class="cols-2">{svc}</ul></div>
<div><h2>{esc(u['footer_areas'])}</h2><ul class="cols-2">{areas}</ul></div>
<div><h2>{esc(u['footer_company'])}</h2><ul>
<li><a href="{page_path(lg, ('page', 'about'))}">{esc(u['nav_about'])}</a></li>
<li><a href="{page_path(lg, ('page', 'contact'))}">{esc(u['nav_contact'])}</a></li>
<li><a href="{page_path(lg, ('index', 'guides'))}">{esc(u['nav_guides'])}</a></li>{guides}</ul></div>
</div>
<div class="wrap footer-bottom"><p>© {datetime.date.today().year} {BRAND}. {esc(u['footer_rights'])}</p><p class="footer-langs">{langs}</p></div>
</footer>
<a class="wa-float" href="{wa_link(L)}" target="_blank" rel="noopener" aria-label="{esc(u['cta_whatsapp'])}">{WA_ICON}</a>"""


def i18n_blob():
    data = {c: [T["ui"]["lang_suggest"], T["ui"]["lang_suggest_btn"], T["ui"]["close"]] for c, T in LANGS.items()}
    return json.dumps(data, ensure_ascii=False)


def layout(L, pid, title, meta, body, ld=(), og_keys=(), og_type="website"):
    lg = L["lang"]
    path = page_path(lg, pid)
    alts = "\n".join(f'<link rel="alternate" hreflang="{T["hreflang"]}" href="{abs_url(page_path(c, pid))}">'
                     for c, T in LANGS.items())
    alts += f'\n<link rel="alternate" hreflang="x-default" href="{abs_url(page_path(DEFAULT, pid))}">'
    og_alt = "\n".join(f'<meta property="og:locale:alternate" content="{T["locale"]}">' for c, T in LANGS.items() if c != lg)
    im = og_image(og_keys)
    og_img = f'<meta property="og:image" content="{im}">\n<meta name="twitter:image" content="{im}">' if im else ""
    lds = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>'
                    for x in (business_ld(L),) + tuple(ld))
    return f"""<!doctype html>
<html lang="{L['hreflang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
<meta name="theme-color" content="#2b211a">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/style.css?v={CSS_VER}">
{lds}
</head>
<body data-lang="{lg}">
{header(L, pid)}
<main id="main">
{body}
</main>
{footer(L, pid)}
<script id="i18n" type="application/json">{i18n_blob()}</script>
<script src="/assets/js/main.js?v={JS_VER}" defer></script>
</body>
</html>
"""


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------

def breadcrumbs(L, items):
    lis = []
    for i, (name, url) in enumerate(items):
        if i == len(items) - 1:
            lis.append(f'<li aria-current="page">{esc(name)}</li>')
        else:
            lis.append(f'<li><a href="{url}">{esc(name)}</a></li>')
    return f'<nav class="crumbs" aria-label="{esc(L["ui"]["breadcrumb"])}"><ol>{"".join(lis)}</ol></nav>'


def hero(L, h1, lead, image_html, crumbs_html="", eyebrow="", points=(), wa_text=""):
    u = L["ui"]
    pts = "".join(f"<li>{esc(p)}</li>" for p in points)
    return f"""<section class="hero"><div class="wrap hero-grid">
<div class="hero-text">{crumbs_html}
{f'<p class="eyebrow">{esc(eyebrow)}</p>' if eyebrow else ''}
<h1>{esc(h1)}</h1>
<p class="lead">{esc(lead)}</p>
<div class="btns"><a class="btn btn-wa" href="{wa_link(L, wa_text)}" target="_blank" rel="noopener">{WA_ICON}<span>{esc(u['cta_whatsapp'])}</span></a>
<a class="btn btn-ghost" href="#quote">{esc(u['cta_quote'])}</a></div>
{f'<ul class="ticks">{pts}</ul>' if pts else ''}
</div>
<div class="hero-media">{image_html}</div>
</div></section>"""


def service_cards(L, keys, area=None):
    lg = L["lang"]
    cards = []
    for k in keys:
        S = L["services"][k]
        if area:
            url = page_path(lg, ("combo", k, area))
            title = fill(S["combo_h1"], in_area=L["areas"][area]["in_area"], area=L["areas"][area]["name"])
            im = img([f"{k}-{area}", k], title, w=600, h=400, L=L)
        else:
            url = page_path(lg, ("service", k))
            title = S["name"]
            im = img(k, title, w=600, h=400, L=L)
        cards.append(f"""<article class="card"><a href="{url}" class="card-link">
<div class="card-media">{im}</div>
<div class="card-body"><h3>{esc(title)}</h3><p>{esc(S['short'])}</p><span class="more">{esc(L['ui']['cta_view'])} →</span></div></a></article>""")
    return f'<div class="cards">{"".join(cards)}</div>'


def area_chips(L, keys, service=None):
    lg = L["lang"]
    out = []
    for a in keys:
        A = L["areas"][a]
        if service:
            url = page_path(lg, ("combo", service, a))
            label = fill(L["services"][service]["combo_h1"], in_area=A["in_area"], area=A["name"])
        else:
            url = page_path(lg, ("area", a))
            label = A["name"]
        out.append(f'<li><a href="{url}"><svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 00-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 00-7-7zm0 9.5A2.5 2.5 0 1112 6a2.5 2.5 0 010 5.5z"/></svg>{esc(label)}</a></li>')
    return f'<ul class="chips">{"".join(out)}</ul>'


def section(title, inner, cls="", sid=""):
    return (f'<section class="section {cls}"{f" id={chr(34)}{sid}{chr(34)}" if sid else ""}><div class="wrap">'
            f'{f"<h2>{esc(title)}</h2>" if title else ""}{inner}</div></section>')


def paras(ps):
    return "".join(f"<p>{esc(p)}</p>" for p in ps)


def features(items):
    return '<div class="features">' + "".join(
        f'<div class="feature"><h3>{esc(f["t"])}</h3><p>{esc(f["d"])}</p></div>' for f in items) + "</div>"


def trust(L):
    return '<div class="trust">' + "".join(
        f'<div class="trust-item"><span class="trust-num">{i + 1:02d}</span><h3>{esc(t["t"])}</h3><p>{esc(t["d"])}</p></div>'
        for i, t in enumerate(L["ui"]["trust"])) + "</div>"


def process(L):
    return '<ol class="process">' + "".join(
        f'<li><span class="step">{i + 1}</span><h3>{esc(p["t"])}</h3><p>{esc(p["d"])}</p></li>'
        for i, p in enumerate(L["ui"]["process"])) + "</ol>"


def price_table(L, rows, lead_time=None):
    u = L["ui"]
    trs = "".join(f"<tr><th scope=\"row\">{esc(r[0])}</th><td>{esc(r[1])}</td></tr>" for r in rows)
    lt = f'<p class="lead-time"><strong>{esc(u["lead_time"])}:</strong> {esc(lead_time)}</p>' if lead_time else ""
    return f"""<div class="table-wrap"><table class="prices"><thead><tr><th scope="col">{esc(u['pricing_item'])}</th><th scope="col">{esc(u['pricing_price'])}</th></tr></thead>
<tbody>{trs}</tbody></table></div>{lt}<p class="note">{esc(u['pricing_note'])}</p>"""


def faq_block(faqs):
    return '<div class="faq">' + "".join(
        f'<details><summary>{esc(f["q"])}</summary><div><p>{esc(f["a"])}</p></div></details>' for f in faqs) + "</div>"


def quote_form(L, service=None, area=None):
    u = L["ui"]
    svc_opts = "".join(
        f'<option value="{esc(L["services"][k]["name"])}"{" selected" if k == service else ""}>{esc(L["services"][k]["name"])}</option>'
        for k in site["services"])
    area_opts = "".join(
        f'<option value="{esc(L["areas"][a["key"]]["name"])}"{" selected" if a["key"] == area else ""}>{esc(L["areas"][a["key"]]["name"])}</option>'
        for a in site["areas"])
    direct = fill(u.get("contact_direct", ""), name=site.get("contact_name", ""))
    return f"""<section class="section cta-band" id="quote"><div class="wrap cta-grid">
<div class="cta-text"><h2>{esc(u['cta_band_title'])}</h2><p>{esc(u['cta_band_text'])}</p>
<div class="contact-card"><div class="avatar" aria-hidden="true">{esc(site.get('contact_name', 'G')[:1])}</div>
<div><strong>{esc(site.get('contact_name', ''))}</strong><span>{esc(u.get('contact_role', ''))}</span>
<a href="{wa_link(L)}" target="_blank" rel="noopener">{esc(site['phone_display'])}</a></div></div>
<p class="small">{esc(direct)}</p></div>
<form class="quote-form" data-wa="{site['whatsapp']}" data-greeting="{esc(fill(u.get('wa_greeting', ''), name=site.get('contact_name', '')))}" action="https://wa.me/{site['whatsapp']}" method="get" target="_blank">
<h3>{esc(u['form_title'])}</h3>
<label>{esc(u['form_name'])}<input name="name" autocomplete="name" required></label>
<div class="row2"><label>{esc(u['form_service'])}<select name="service"><option value="">{esc(u['form_select'])}</option>{svc_opts}<option value="{esc(u['form_other'])}">{esc(u['form_other'])}</option></select></label>
<label>{esc(u['form_area'])}<select name="area"><option value="">{esc(u['form_select'])}</option>{area_opts}<option value="{esc(u['form_other'])}">{esc(u['form_other'])}</option></select></label></div>
<label>{esc(u['form_message'])}<textarea name="text" rows="4"></textarea></label>
<button class="btn btn-wa btn-block" type="submit">{WA_ICON}<span>{esc(u['form_send'])}</span></button>
<p class="small center"><a href="mailto:{site['email']}">{esc(u['form_email'])}: {site['email']}</a></p>
</form></div></section>"""


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------

pages_written = []


def write(lang, pid, content):
    path = page_path(lang, pid)
    fp = os.path.join(OUT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(content)
    if lang == DEFAULT:
        pages_written.append(pid)


def build_home(L):
    lg, u, H = L["lang"], L["ui"], L["home"]
    pid = ("home",)
    body = hero(L, H["h1"], H["lead"], img("hero", H["h1"], eager=True, L=L), eyebrow=H["eyebrow"], points=H["points"])
    body += section(u["why_title"], trust(L), "section-trust")
    body += section(u["services_title"], f'<p class="section-lead">{esc(u["services_lead"])}</p>'
                    + service_cards(L, site["services"]), sid="services")
    body += section("", f"""<div class="split"><div><h2>{esc(H['intro_title'])}</h2>{paras(fill(p) for p in H['intro'])}
<p><a class="btn btn-ghost" href="{page_path(lg, ('guide', 'materials'))}">{esc(L['guides']['materials']['h1'])} →</a></p></div>
<div>{img('workshop', H['intro_title'], L=L)}</div></div>""", "section-alt")
    body += section(u["process_title"], process(L))
    body += section(u["areas_title"], f'<p class="section-lead">{esc(H["areas_teaser"])}</p>' + area_chips(L, [a["key"] for a in site["areas"]]), "section-alt")
    guides = "".join(f"""<article class="guide-card"><a href="{page_path(lg, ('guide', g))}"><h3>{esc(L['guides'][g]['h1'])}</h3>
<p>{esc(L['guides'][g]['meta'])}</p><span class="more">{esc(u['read_more'])} →</span></a></article>""" for g in site["guides"])
    body += section(u["guides_title"], f'<div class="guide-cards">{guides}</div>')
    faqs = u["faq_general"]
    body += section(u["faq_title"], faq_block(faqs), "section-alt")
    body += quote_form(L)
    website_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": abs_url(prefix(lg)),
                  "inLanguage": L["hreflang"]}
    write(lg, pid, layout(L, pid, H["title"], H["meta"], body, ld=(website_ld, faq_ld(faqs)), og_keys=["hero"]))


def build_services_index(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["services"]
    pid = ("index", "services")
    cr = [(u["home"], prefix(lg)), (P["h1"], page_path(lg, pid))]
    body = hero(L, P["h1"], u["services_lead"], img("services", P["h1"], eager=True, L=L), breadcrumbs(L, cr))
    body += section("", service_cards(L, site["services"]))
    body += section(u["process_title"], process(L), "section-alt")
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),)))


def build_areas_index(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["areas"]
    pid = ("index", "areas")
    cr = [(u["home"], prefix(lg)), (P["h1"], page_path(lg, pid))]
    body = hero(L, P["h1"], u["areas_lead"], img("areas", P["h1"], eager=True, L=L), breadcrumbs(L, cr))
    cards = []
    for a in site["areas"]:
        A = L["areas"][a["key"]]
        cards.append(f"""<article class="card"><a href="{page_path(lg, ('area', a['key']))}" class="card-link">
<div class="card-media">{img('area-' + a['key'], A['h1'], w=600, h=400, L=L)}</div>
<div class="card-body"><h3>{esc(A['h1'])}</h3><p>{esc(A['intro'][:150].rsplit(' ', 1)[0])}…</p><span class="more">{esc(u['cta_view'])} →</span></div></a></article>""")
    body += section("", f'<div class="cards">{"".join(cards)}</div>')
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),)))


def build_service(L, k):
    lg, u, S = L["lang"], L["ui"], L["services"][k]
    pid = ("service", k)
    cr = [(u["home"], prefix(lg)), (L["pages"]["services"]["h1"], page_path(lg, ("index", "services"))),
          (S["name"], page_path(lg, pid))]
    body = hero(L, S["h1"], S["short"], img(k, S["h1"], eager=True, L=L), breadcrumbs(L, cr), wa_text=S["name"])
    body += section("", f'<div class="prose">{paras(fill(p) for p in S["intro"])}</div>')
    body += section(u["features_title"], features(S["features"]), "section-alt")
    body += section(u["materials_title"], f'<div class="prose"><p>{esc(S["materials"])}</p></div>')
    body += section(u["pricing_title"], price_table(L, S["price"], S["lead_time"]), "section-alt")
    body += section(fill(u["service_areas_title"], service=S["name"]), area_chips(L, [a["key"] for a in site["areas"]], k), "section-alt")
    body += section(u["process_title"], process(L))
    faqs = S["faqs"] + u["faq_general"]
    body += section(u["faq_title"], faq_block(faqs), "section-alt")
    others = [s for s in site["services"] if s != k][:6]
    body += section(u["services_title"], service_cards(L, others))
    body += quote_form(L, service=k)
    area_names = [L["areas"][a["key"]]["name"] + ", Bali" for a in site["areas"]]
    lds = (service_ld(L, S["name"], S["meta"], page_path(lg, pid), area_names), faq_ld(faqs), crumbs_ld(cr))
    write(lg, pid, layout(L, pid, S["title"], S["meta"], body, ld=lds, og_keys=[k]))


def build_area(L, a):
    lg, u, A = L["lang"], L["ui"], L["areas"][a]
    pid = ("area", a)
    cr = [(u["home"], prefix(lg)), (L["pages"]["areas"]["h1"], page_path(lg, ("index", "areas"))),
          (A["name"], page_path(lg, pid))]
    body = hero(L, A["h1"], A["intro"], img("area-" + a, A["h1"], eager=True, L=L), breadcrumbs(L, cr), wa_text=A["name"])
    body += section("", f"""<div class="info-grid">
<div><h2>{esc(fill(u['homes_title'], in_area=A['in_area'], area=A['name']))}</h2><p>{esc(A['homes'])}</p></div>
<div><h2>{esc(fill(u['local_title'], in_area=A['in_area'], area=A['name']))}</h2><p>{esc(A['climate'])}</p></div>
<div><h2>{esc(fill(u['style_title'], in_area=A['in_area'], area=A['name']))}</h2><p>{esc(A['style'])}</p></div></div>""")
    body += section(fill(u["services_in_area"], in_area=A["in_area"], area=A["name"]), service_cards(L, site["services"], area=a), "section-alt")
    body += section(u["why_title"], trust(L))
    body += section(u["process_title"], process(L), "section-alt")
    faqs = A["faqs"] + u["faq_general"]
    body += section(u["faq_title"], faq_block(faqs))
    body += section(u["areas_title"], area_chips(L, AREA_CFG[a]["nearby"]), "section-alt")
    body += quote_form(L, area=a)
    place_ld = {"@context": "https://schema.org", "@type": "Service", "name": A["h1"], "url": abs_url(page_path(lg, pid)),
                "provider": {"@id": DOMAIN + "/#business"},
                "areaServed": {"@type": "Place", "name": A["name"] + ", Bali",
                               "geo": {"@type": "GeoCoordinates", "latitude": AREA_CFG[a]["lat"], "longitude": AREA_CFG[a]["lng"]}}}
    write(lg, pid, layout(L, pid, A["title"], A["meta"], body, ld=(place_ld, faq_ld(faqs), crumbs_ld(cr)), og_keys=["area-" + a]))


def build_combo(L, k, a):
    lg, u, S, A = L["lang"], L["ui"], L["services"][k], L["areas"][a]
    kw = dict(in_area=A["in_area"], area=A["name"], service=S["name"])
    pid = ("combo", k, a)
    h1 = fill(S["combo_h1"], **kw)
    cr = [(u["home"], prefix(lg)), (S["name"], page_path(lg, ("service", k))),
          (A["name"], page_path(lg, ("area", a))), (h1, page_path(lg, pid))]
    body = hero(L, h1, fill(S["combo_intro"], **kw), img([f"{k}-{a}", k], h1, eager=True, L=L),
                breadcrumbs(L, cr), wa_text=h1)
    body += section("", f'<div class="prose">{paras(fill(p, **kw) for p in S["intro"])}</div>')
    body += section("", f"""<div class="info-grid">
<div><h2>{esc(fill(u['local_title'], **kw))}</h2><p>{esc(A['climate'])}</p></div>
<div><h2>{esc(fill(u['style_title'], **kw))}</h2><p>{esc(A['style'])}</p></div>
<div><h2>{esc(fill(u['homes_title'], **kw))}</h2><p>{esc(A['homes'])}</p></div></div>""", "section-alt")
    body += section(u["features_title"], features(S["features"]))
    body += section(u["materials_title"], f'<div class="prose"><p>{esc(S["materials"])}</p></div>', "section-alt")
    body += section(u["pricing_title"], price_table(L, S["price"], S["lead_time"]))
    body += section(u["process_title"], process(L), "section-alt")
    faqs = [{"q": fill(f["q"], **kw), "a": fill(f["a"], **kw)} for f in S["combo_faqs"]] + S["faqs"][:2] + A["faqs"]
    body += section(u["faq_title"], faq_block(faqs))
    body += section(fill(u["nearby_areas"], **kw), area_chips(L, AREA_CFG[a]["nearby"], k), "section-alt")
    others = [s for s in site["services"] if s != k][:6]
    body += section(fill(u["related_services"], **kw), service_cards(L, others, area=a))
    body += quote_form(L, service=k, area=a)
    sld = service_ld(L, h1, fill(S["combo_meta"], **kw), page_path(lg, pid), [A["name"] + ", Bali"])
    write(lg, pid, layout(L, pid, fill(S["combo_title"], **kw), fill(S["combo_meta"], **kw), body,
                          ld=(sld, faq_ld(faqs), crumbs_ld(cr)), og_keys=[f"{k}-{a}", k]))


def build_about(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["about"]
    pid = ("page", "about")
    h1 = fill(P["h1"])
    cr = [(u["home"], prefix(lg)), (u["nav_about"], page_path(lg, pid))]
    body = hero(L, h1, fill(P["body"][0]), img("about", h1, eager=True, L=L), breadcrumbs(L, cr))
    body += section("", f'<div class="split"><div class="prose">{paras(fill(p) for p in P["body"][1:])}</div><div>{img("workshop", h1, L=L)}</div></div>')
    body += section(P["values_title"], features(P["values"]), "section-alt")
    body += section(u["why_title"], trust(L))
    body += section(u["process_title"], process(L), "section-alt")
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),)))


def build_contact(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["contact"]
    pid = ("page", "contact")
    cr = [(u["home"], prefix(lg)), (u["nav_contact"], page_path(lg, pid))]
    body = f"""<section class="hero hero-slim"><div class="wrap">{breadcrumbs(L, cr)}<h1>{esc(P['h1'])}</h1><p class="lead">{esc(P['lead'])}</p></div></section>"""
    body += section("", f"""<div class="info-grid">
<div><h2>WhatsApp</h2><p><strong>{esc(site.get('contact_name', ''))}</strong> — {esc(u.get('contact_role', ''))}<br><a href="{wa_link(L)}" target="_blank" rel="noopener">{esc(site['phone_display'])}</a></p>
<p><a href="mailto:{site['email']}">{site['email']}</a></p></div>
<div><h2>{esc(P['hours_title'])}</h2><p>{esc(P['hours'])}</p></div>
<div><h2>{esc(P['area_title'])}</h2><p>{esc(P['area'])}</p>{area_chips(L, [a['key'] for a in site['areas']])}</div></div>""")
    body += quote_form(L)
    body += section(u["faq_title"], faq_block(u["faq_general"]))
    cp = {"@context": "https://schema.org", "@type": "ContactPage", "name": P["h1"], "url": abs_url(page_path(lg, pid)),
          "about": {"@id": DOMAIN + "/#business"}}
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(cp, crumbs_ld(cr), faq_ld(u["faq_general"]))))


def build_guides_index(L):
    lg, u, P = L["lang"], L["ui"], L["pages"]["guides"]
    pid = ("index", "guides")
    cr = [(u["home"], prefix(lg)), (P["h1"], page_path(lg, pid))]
    cards = "".join(f"""<article class="guide-card"><a href="{page_path(lg, ('guide', g))}"><h2>{esc(L['guides'][g]['h1'])}</h2>
<p>{esc(L['guides'][g]['intro'])}</p><span class="more">{esc(u['read_more'])} →</span></a></article>""" for g in site["guides"])
    body = f"""<section class="hero hero-slim"><div class="wrap">{breadcrumbs(L, cr)}<h1>{esc(P['h1'])}</h1><p class="lead">{esc(u['guides_lead'])}</p></div></section>"""
    body += section("", f'<div class="guide-cards">{cards}</div>')
    body += quote_form(L)
    write(lg, pid, layout(L, pid, P["title"], P["meta"], body, ld=(crumbs_ld(cr),)))


def build_guide(L, g):
    lg, u, G = L["lang"], L["ui"], L["guides"][g]
    pid = ("guide", g)
    cr = [(u["home"], prefix(lg)), (L["pages"]["guides"]["h1"], page_path(lg, ("index", "guides"))), (G["h1"], page_path(lg, pid))]
    toc = "".join(f'<li><a href="#s{i + 1}">{esc(s["h"])}</a></li>' for i, s in enumerate(G["sections"]))
    secs = "".join(f'<h2 id="s{i + 1}">{esc(s["h"])}</h2>{paras(s["p"])}' for i, s in enumerate(G["sections"]))
    body = f"""<article class="article"><header class="hero hero-slim"><div class="wrap narrow">{breadcrumbs(L, cr)}<h1>{esc(G['h1'])}</h1>
<p class="lead">{esc(G['intro'])}</p><p class="small">{esc(u['updated'])}: <time datetime="{TODAY}">{TODAY}</time></p></div></header>
<div class="section"><div class="wrap narrow prose">{img('guide-' + g, G['h1'], eager=True, L=L)}<nav class="toc"><ol>{toc}</ol></nav>{secs}</div></div></article>"""
    related = ["kitchens", "wardrobes", "bathroom-vanities"] if g == "kitchen-cost" else ["doors-windows", "decking", "custom-furniture"]
    body += section(u["services_title"], service_cards(L, related), "section-alt")
    body += quote_form(L)
    art = {"@context": "https://schema.org", "@type": "Article", "headline": G["h1"], "description": G["meta"],
           "inLanguage": L["hreflang"], "datePublished": TODAY, "dateModified": TODAY,
           "author": {"@id": DOMAIN + "/#business"}, "publisher": {"@id": DOMAIN + "/#business"},
           "mainEntityOfPage": abs_url(page_path(lg, pid))}
    write(lg, pid, layout(L, pid, G["title"], G["meta"], body, ld=(art, crumbs_ld(cr)), og_keys=["guide-" + g], og_type="article"))


def build_404():
    L = LANGS[DEFAULT]
    u, P = L["ui"], L["pages"]["notfound"]
    body = f"""<section class="hero hero-slim"><div class="wrap"><h1>{esc(P['h1'])}</h1><p class="lead">{esc(P['text'])}</p>
<p class="btns"><a class="btn" href="{page_path(DEFAULT, ('index', 'services'))}">{esc(u['cta_all_services'])}</a>
<a class="btn btn-ghost" href="{page_path(DEFAULT, ('index', 'areas'))}">{esc(u['cta_all_areas'])}</a></p></div></section>"""
    body += section("", service_cards(L, site["featured_services"]))
    html_ = layout(L, ("home",), P["title"], P["text"], body).replace(
        '<meta name="robots" content="index, follow, max-image-preview:large">', '<meta name="robots" content="noindex">')
    open(os.path.join(OUT, "404.html"), "w", encoding="utf-8").write(html_)


def build_sitemap():
    urls = []
    for pid in pages_written:
        alts = "".join(f'<xhtml:link rel="alternate" hreflang="{T["hreflang"]}" href="{abs_url(page_path(c, pid))}"/>'
                       for c, T in LANGS.items())
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
    for c, L in LANGS.items():
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
    shutil.copytree(ASSETS, os.path.join(OUT, "assets"))
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
