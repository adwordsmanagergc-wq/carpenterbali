# carpenterbali.com

A fast, multilingual (English · Bahasa Indonesia · Français · Русский) static website for **Carpenter Bali**, built for local SEO across Bali's main expat areas.

## What's included

| Page type | Example URL | Count per language |
|---|---|---|
| Home | `/` `/id/` `/fr/` `/ru/` | 1 |
| Service pages | `/kitchens-bali/`, `/wardrobes-bali/`, `/walk-in-wardrobes-bali/` | 16 |
| Area pages | `/carpenter-canggu/`, `/carpenter-uluwatu/` | 16 |
| Service × area pages | `/kitchens-canggu/`, `/wardrobes-kuta/`, `/walk-in-wardrobes-seminyak/` | 256 |
| Guides | `/guides/kitchen-cost-bali/` | 2 |
| Services, areas & guides indexes, About, Contact | | 5 |

Each language uses its own local-language URLs (e.g. `/id/kitchen-set-canggu/`, `/fr/cuisine-sur-mesure-canggu/`, `/ru/kuhni-na-zakaz-canggu/`).

**Services:** custom kitchens, built-in wardrobes, walk-in wardrobes, bathroom vanities, TV & media units, doors/windows/frames, decking, pergolas/gazebos/bale, staircases, ceilings & wall panelling, beds & headboards, shelving & home office, custom furniture, villa fit-out, restaurant/café/retail fit-out, repairs & restoration.

**Areas:** Canggu, Pererenan, Berawa, Seminyak, Kerobokan, Umalas, Kuta, Legian, Jimbaran, Uluwatu, Ungasan, Nusa Dua, Sanur, Ubud, Tabanan, Denpasar.

### SEO built in
- Unique title, meta description, H1 and FAQs on every page, in every language
- `hreflang` alternates for all four languages plus `x-default`, self-referencing canonicals
- Structured data (JSON-LD): `HomeAndConstructionBusiness`, `Service`, `FAQPage`, `BreadcrumbList`, `Article`, `WebSite`
- `sitemap.xml` that lists every language version of each page, plus `robots.txt`
- Internal links between services, areas, nearby areas and related services
- Open Graph and Twitter tags, semantic HTML, breadcrumbs
- Plain HTML and CSS with no framework and one small JS file, so pages load fast and score well on Core Web Vitals
- Language switcher on every page. It also suggests (without forcing a redirect) the visitor's browser language.
- WhatsApp quote form that sends the enquiry to **Gede, Master Carpenter (+62 852-3789-6850)**

## Adding your photos

Every image placeholder shows the filename it expects (e.g. `images/kitchens.jpg`). Put your photos in the `images/` folder with that name, then rebuild. You can use `.jpg`, `.jpeg`, `.webp`, `.png` or `.avif`.

| File name | Used on |
|---|---|
| `hero.jpg` | Home page hero, and the default social-share image |
| `og.jpg` | (optional) Social-share image, 1200×630 |
| `workshop.jpg`, `about.jpg` | Home, About |
| `services.jpg`, `areas.jpg` | Services index, Areas index |
| `kitchens.jpg`, `wardrobes.jpg`, `walk-in-wardrobes.jpg`, `bathroom-vanities.jpg`, `tv-units.jpg`, `doors-windows.jpg`, `decking.jpg`, `pergolas.jpg`, `staircases.jpg`, `ceilings-panelling.jpg`, `beds.jpg`, `shelving-office.jpg`, `custom-furniture.jpg`, `villa-fitout.jpg`, `commercial-fitout.jpg`, `repairs.jpg` | Service page heroes and cards, and the fallback for every area version of that service |
| `kitchens-2.jpg`, `kitchens-3.jpg`, `kitchens-4.jpg` (same pattern for every service) | Gallery on each service page |
| `kitchens-canggu.jpg`, `wardrobes-uluwatu.jpg` … *(optional)* | A specific photo for one service × area page |
| `area-canggu.jpg`, `area-ubud.jpg` … | Area page heroes and cards |
| `guide-kitchen-cost.jpg`, `guide-materials.jpg` | Guide pages |

Use landscape photos, ideally 1600×1067 px (3:2), compressed to under about 300 KB.

## Editing content

- **Contact details, areas, services:** `content/site.json`
- **Text for each language:** `content/en.json`, `content/id.json`, `content/fr.json`, `content/ru.json`. All four files have the same structure.
- **Prices** are indicative budget ranges. Check them against your own rates before going live. You'll find them under `services → <service> → price`, and in the `combo_faqs` answers, in each language file.
- **Design:** `assets/css/style.css`

## Build

```bash
python3 build.py      # writes the full site to ./public
```

You only need Python 3. Nothing else has to be installed.

## Deploy

The built site is in `public/` (committed, so it can be deployed as-is).

- **Netlify / Cloudflare Pages:** connect this repo. Build command `python3 build.py`, output directory `public` (Netlify reads `netlify.toml` for these automatically).
- **GitHub Pages / any static host:** serve the `public/` folder. `public/CNAME` is already set to `carpenterbali.com`.

Then point the domain `carpenterbali.com` at the host, and submit `https://carpenterbali.com/sitemap.xml` in Google Search Console.

### After launch
1. Create or claim a **Google Business Profile** for Carpenter Bali, using the same name and phone number as the website.
2. Add your Instagram and Facebook URLs in `content/site.json` (they're added to the structured data automatically).
3. Replace the placeholders with real project photos. Ideally name the files by area (e.g. `kitchens-canggu.jpg`).
4. Ask happy clients for Google reviews.
