#!/usr/bin/env python3
"""Builds mikeforlogan.com into dist/. Standard library only.

Edit content in (or in the Pages CMS editor):
  src/site.json        campaign name, contact info, links, "Paid for by" line
  src/record.json      accomplishments ("My record")
  src/priorities.json  priorities
  src/faq.json         common questions (also used for Google and AI search)
  src/about.md         About page text
  src/updates/*.md     council updates / news posts (one file each)
  img/                 photos
"""
import html, json, os, re, shutil
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")
J = lambda n: json.load(open(os.path.join(SRC, n), encoding="utf-8"))
SITE, RECORD, PRIORITIES, FAQ = J("site.json"), J("record.json"), J("priorities.json"), J("faq.json")
BASE = SITE["url"].rstrip("/")
TODAY = date.today().isoformat()
YEAR = date.today().year


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------- tiny markdown + front matter
def inline_md(t):
    t = esc(t).replace("&#x27;", "'").replace("&quot;", '"')
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', t)
    return t


def markdown(md):
    out, blocks = [], re.split(r"\n\s*\n", md.strip().replace("\r\n", "\n"))
    for b in blocks:
        b = b.strip()
        m = re.match(r"(#{2,3}) (.*)", b)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline_md(m.group(2))}</h{len(m.group(1))}>"); continue
        m = re.match(r'!\[([^\]]*)\]\(([^)\s]+)\)$', b)
        if m:
            out.append(f'<figure>{img(m.group(2), m.group(1))}</figure>'); continue
        lines = b.split("\n")
        if all(re.match(r"\s*([-*]|\d+\.) ", l) for l in lines):
            tag = "ol" if lines[0].strip()[0].isdigit() else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline_md(re.sub(r'^\s*([-*]|\d+\.) ', '', l))}</li>" for l in lines) + f"</{tag}>"); continue
        if b.startswith(">"):
            out.append("<blockquote>" + inline_md(" ".join(l.lstrip("> ") for l in lines)) + "</blockquote>"); continue
        out.append(f"<p>{inline_md(' '.join(lines))}</p>")
    return "\n".join(out)


def front_matter(text):
    text = text.replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    meta, lines, i = {}, m.group(1).splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line or line.startswith((" ", "\t")):
            i += 1; continue
        k, v = [x.strip() for x in line.split(":", 1)]
        if v[:1] in (">", "|"):
            block = []; i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip()); i += 1
            meta[k] = " ".join(x for x in block if x); continue
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        meta[k] = v; i += 1
    return meta, m.group(2)


def plain(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


# ---------------------------------------------------------------- images
def img(src, alt, cls="", eager=False):
    """Real <img> if the file exists, otherwise a labeled placeholder (so the site builds before photos arrive)."""
    path = os.path.join(ROOT, src.lstrip("/"))
    if not os.path.exists(path):
        return f'<div class="ph {cls}" role="img" aria-label="{esc(alt)}">Photo coming: {esc(alt)}</div>'
    dims = ""
    try:
        from struct import unpack
        with open(path, "rb") as f:
            data = f.read(65536)
        if data[:4] == b"RIFF" and data[12:16] == b"VP8X":
            w, h = 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little"); dims = f' width="{w}" height="{h}"'
        elif data[:2] == b"\xff\xd8":
            i = 2
            while i < len(data) - 9:
                if data[i] != 0xFF: break
                mk, ln = data[i + 1], unpack(">H", data[i + 2:i + 4])[0]
                if mk in (0xC0, 0xC1, 0xC2):
                    h, w = unpack(">HH", data[i + 5:i + 9]); dims = f' width="{w}" height="{h}"'; break
                i += 2 + ln
    except Exception:
        pass
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    c = f' class="{cls}"' if cls else ""
    return f'<img src="{src}" alt="{esc(alt)}"{dims}{c} {load} decoding="async">'


# ---------------------------------------------------------------- structured data
def person():
    return {
        "@type": "Person", "@id": BASE + "/#mike", "name": "Mike Johnson",
        "url": BASE + "/", "image": BASE + SITE["image"], "email": SITE["council_email"],
        "jobTitle": "Chair, Logan Municipal Council",
        "description": SITE["description"],
        "memberOf": {"@type": "GovernmentOrganization", "name": "Logan Municipal Council",
                     "url": "https://www.loganutah.gov/government/city_council/index.php",
                     "parentOrganization": {"@type": "GovernmentOrganization", "name": "City of Logan, Utah"}},
        "hasOccupation": [
            {"@type": "Occupation", "name": "City Council Member", "occupationLocation": {"@type": "City", "name": "Logan, Utah"}},
            {"@type": "Occupation", "name": "Small business owner (photographer and videographer)"}],
        "worksFor": {"@type": "LocalBusiness", "name": "Mike Johnson Photo + Video", "url": "https://www.mikejohnsonphoto.com"},
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "Utah State University"},
        "homeLocation": {"@type": "City", "name": "Logan, Utah"},
        "knowsAbout": [p["title"] for p in PRIORITIES["items"]],
        "sameAs": SITE["same_as"],
    }


def org():
    return {"@type": "Organization", "@id": BASE + "/#campaign", "name": SITE["name"], "url": BASE + "/",
            "email": SITE["email"], "telephone": SITE["phone_e164"], "logo": BASE + "/favicon.svg",
            "founder": {"@id": BASE + "/#mike"}, "sameAs": SITE["same_as"][:2]}


def website():
    return {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": SITE["short_name"],
            "alternateName": SITE["name"], "publisher": {"@id": BASE + "/#campaign"}, "about": {"@id": BASE + "/#mike"}}


def faq_schema(items):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in items]}


def crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + u} for i, (n, u) in enumerate(items)]}


# ---------------------------------------------------------------- shell
SOCIAL = {
    "facebook.com": ("Facebook", '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 22v-8h2.7l.4-3.2h-3.1V8.8c0-.9.3-1.6 1.6-1.6h1.7V4.3c-.3 0-1.3-.1-2.5-.1-2.5 0-4.1 1.5-4.1 4.2v2.4H7.4V14h2.8v8h3.3z"/></svg>'),
    "instagram.com": ("Instagram", '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/></svg>'),
}


def nav(current, has_updates):
    items = [("/record/", "My Record"), ("/priorities/", "Priorities"), ("/about/", "About Mike")]
    if has_updates:
        items.append(("/updates/", "Updates"))
    out = "".join(f'<a href="{u}"{" aria-current=\"page\"" if u == current else ""}>{t}</a>' for u, t in items)
    out += f'<a href="/get-involved/"{" aria-current=\"page\"" if current == "/get-involved/" else ""}>Get Involved</a>'
    out += f'<a class="btn btn-gold" href="{SITE['venmo']}" target="_blank" rel="noopener">Donate</a>'
    return out


def header(current, has_updates):
    return f"""<header class="site-header">
<div class="wrap">
<a class="brand" href="/" aria-label="Mike Johnson for Logan City Council, home"><b>MIKE JOHNSON</b><span>FOR LOGAN CITY COUNCIL</span></a>
<button class="menu-btn" type="button" aria-expanded="false" aria-controls="main-nav">Menu</button>
<nav id="main-nav" aria-label="Main">{nav(current, has_updates)}</nav>
</div>
</header>"""


def footer():
    soc = "".join(f'<a href="{esc(u)}" target="_blank" rel="noopener me" aria-label="Mike for Logan on {n}">{svg}</a>'
                  for u in SITE["same_as"] for d, (n, svg) in SOCIAL.items() if d in u)
    return f"""<footer class="site-footer">
<div class="wrap">
<div class="foot-grid">
<div>
<h2>Mike Johnson for Logan</h2>
<p>{esc(SITE['status_line'])}.</p>
<div class="social">{soc}</div>
</div>
<div>
<h2>Campaign</h2>
<ul>
<li><a href="mailto:{SITE['email']}">{SITE['email']}</a></li>
<li><a href="tel:{SITE['phone'].replace('-', '')}">{SITE['phone']}</a></li>
<li><a href="/get-involved/">Volunteer or get a yard sign</a></li>
<li><a href="{SITE['register']}" rel="noopener">Register to vote</a></li>
</ul>
</div>
<div>
<h2>City business</h2>
<ul>
<li><a href="mailto:{SITE['council_email']}">{SITE['council_email']}</a></li>
<li><a href="https://www.loganutah.gov/government/city_council/index.php" rel="noopener">Logan Municipal Council</a></li>
<li>Meetings: 1st &amp; 3rd Tuesdays, 5:30 p.m., Logan City Hall</li>
</ul>
</div>
</div>
<p class="paid-for">{esc(SITE['paid_for'])}</p>
<p class="legal">© {YEAR} Mike Johnson for Logan City Council. Campaign site; not an official City of Logan website.</p>
</div>
</footer>"""


def shell(url, title, desc, body, schema, current=None, og_image=None, noindex=False, og_type="website", has_updates=False):
    canonical = BASE + url
    og_image = og_image or SITE["image"]
    graph = [person(), org(), website()] + schema
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    robots = "noindex" if noindex else "index, follow, max-image-preview:large"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta name="author" content="Mike Johnson">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(SITE['short_name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE + og_image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="geo.region" content="US-UT">
<meta name="geo.placename" content="Logan, Utah">
<meta name="theme-color" content="#12284C">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{header(current, has_updates)}
<main id="main">
{body}
</main>
{footer()}
<script src="/assets/site.js" defer></script>
</body>
</html>
"""


def write(url, content):
    path = os.path.join(DIST, url.strip("/"), "index.html") if url.endswith("/") else os.path.join(DIST, url.lstrip("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(content)


# ---------------------------------------------------------------- page pieces
def record_cards(items):
    return "".join(f"""<article class="card">
<span class="tag">{esc(r['topic'])}</span>
<div class="yr">{esc(r['year'])}</div>
<h3>{esc(r['title'])}</h3>
<p>{esc(r['summary'])}</p>
</article>""" for r in items)


def priority_cards(items, with_next=False):
    out = []
    for p in items:
        nxt = f'<p class="next"><b>Next:</b> {esc(p["next"])}</p>' if with_next and p.get("next") else ""
        out.append(f'<article class="card" id="{esc(p["id"])}"><h3>{esc(p["title"])}</h3><p>{esc(p["summary"])}</p>{nxt}</article>')
    return "".join(out)


def faq_html(items):
    return "".join(f"<details><summary>{esc(q['q'])}</summary><p>{inline_md(q['a'])}</p></details>" for q in items)


def facts():
    return """<section class="facts" aria-label="Quick facts"><div class="wrap"><ul>
<li><strong>2023</strong><span>Elected to Logan City Council</span></li>
<li><strong>2025</strong><span>Council Vice Chair</span></li>
<li><strong>2026</strong><span>Council Chair</span></li>
<li><strong>2027</strong><span>Running for re-election</span></li>
</ul></div></section>"""


def cta():
    return f"""<section class="cta"><div class="wrap">
<p class="eyebrow">Join the campaign</p>
<h2>Help keep Logan moving forward</h2>
<p class="lead" style="color:#D5DCEA">Local races are won by neighbors talking to neighbors. A yard sign, a few doors or a letter to the editor makes a real difference.</p>
<div class="grid grid-3" style="margin-top:32px">
<div class="card"><h3>Volunteer</h3><p>Yard signs, door hangers, letters of support, or host a meet and greet.</p><a class="more" style="color:var(--gold)" href="/get-involved/">Sign up →</a></div>
<div class="card"><h3>Donate</h3><p>Every dollar goes to signs, mailers and getting the word out in Logan.</p><a class="more" style="color:var(--gold)" href="{SITE['venmo']}" target="_blank" rel="noopener">Donate on Venmo →</a></div>
<div class="card"><h3>Register to vote</h3><p>Check your registration or register in a couple of minutes.</p><a class="more" style="color:var(--gold)" href="{SITE['register']}" rel="noopener">vote.utah.gov →</a></div>
</div>
</div></section>"""


def form_open(fid, subject, thanks):
    key = SITE["web3forms_key"]
    return (f'<form class="panel" id="{fid}" data-ajax data-thanks="{esc(thanks)}" action="https://api.web3forms.com/submit" method="POST">'
            f'<input type="hidden" name="access_key" value="{esc(key)}">'
            f'<input type="hidden" name="subject" value="{esc(subject)}">'
            '<input type="hidden" name="from_name" value="mikeforlogan.com">'
            '<input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">')


# ---------------------------------------------------------------- updates
def load_updates():
    d = os.path.join(SRC, "updates")
    posts = []
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not fn.endswith(".md"):
            continue
        meta, md = front_matter(open(os.path.join(d, fn), encoding="utf-8").read())
        if str(meta.get("draft", "")).lower() in ("true", "yes"):
            continue
        meta["slug"] = fn[:-3]
        meta.setdefault("date", TODAY)
        meta.setdefault("description", plain(markdown(md))[:155])
        posts.append((meta, md))
    return sorted(posts, key=lambda p: p[0]["date"], reverse=True)


def nice_date(d):
    try:
        y, m, dd = map(int, d.split("-"))
        return date(y, m, dd).strftime("%B %-d, %Y")
    except Exception:
        return d


# ---------------------------------------------------------------- build
def main():
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(DIST)
    shutil.copytree(os.path.join(ROOT, "static"), DIST, dirs_exist_ok=True)
    for d in ("img", "media"):
        if os.path.isdir(os.path.join(ROOT, d)):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(DIST, d), dirs_exist_ok=True, ignore=shutil.ignore_patterns(".gitkeep"))

    posts = load_updates()
    hu = bool(posts)
    sitemap = []
    featured = [r for r in RECORD["items"] if r.get("featured")][:4] or RECORD["items"][:4]

    # ---- home
    latest = ""
    if posts:
        latest = '<section class="section"><div class="wrap"><div class="section-head"><div><p class="eyebrow">From City Hall</p><h2>Council updates</h2></div><a href="/updates/">All updates →</a></div><div class="grid">' + "".join(
            f'<a href="/updates/{m["slug"]}/" style="text-decoration:none;color:inherit"><article class="card"><div class="post-meta">{nice_date(m["date"])}</div><h3>{esc(m["title"])}</h3><p>{esc(m["description"])}</p></article></a>'
            for m, _ in posts[:3]) + "</div></div></section>"
    home = f"""<section class="hero"><div class="wrap">
<div>
<p class="eyebrow">Logan Municipal Council Chair</p>
<h1>Keep Logan focused on its future.</h1>
<p class="lead">I'm Mike Johnson, a Logan small business owner, husband and dad. For four years I've worked on the city council for attainable homes, responsible budgets and a plan for the next generation. I'm running for re-election in 2027.</p>
<div class="btns"><a class="btn btn-navy" href="/get-involved/">Get involved</a><a class="btn btn-ghost" href="/record/">See my record</a></div>
</div>
<div class="hero-photo">{img(SITE['image'], 'Mike Johnson, Logan City Council Chair', eager=True)}</div>
</div></section>
{facts()}
<section class="section section-white"><div class="wrap">
<div class="section-head"><div><p class="eyebrow">Four years on the council</p><h2>What we've gotten done</h2></div><a href="/record/">Full record →</a></div>
<div class="grid grid-4">{record_cards(featured)}</div>
</div></section>
<section class="section"><div class="wrap">
<div class="section-head"><div><p class="eyebrow">Priorities</p><h2>What I'm working on</h2></div><a href="/priorities/">More on each →</a></div>
<div class="grid grid-3">{priority_cards(PRIORITIES['items'])}</div>
</div></section>
<section class="section section-white"><div class="wrap split">
<div>{img('/img/mike-johnson-community.jpg', 'Mike Johnson with Logan residents at a community event')}</div>
<div>
<p class="eyebrow">About Mike</p>
<h2>A neighbor, not a politician</h2>
<p>My wife and I came to Logan for Utah State University and never left. I run a photo and video business downtown, and you'll find me on the trails and in the canyon on Saturdays.</p>
<p>On the council I read every packet, ask hard questions and try to answer every email. If something in Logan matters to you, I want to hear about it.</p>
<div class="btns"><a class="btn btn-ghost" href="/about/">More about Mike</a></div>
</div>
</div></section>
{latest}
{cta()}
<section class="section"><div class="wrap narrow">
<p class="eyebrow">Questions</p>
<h2>Common questions</h2>
{faq_html(FAQ['items'])}
</div></section>"""
    write("/", shell("/", "Mike Johnson for Logan City Council | Logan, Utah",
                     "Mike Johnson, Chair of the Logan Municipal Council, is running for re-election in 2027. See his record on housing, budgets and planning, and get involved.",
                     home, [{"@type": "WebPage", "@id": BASE + "/#webpage", "url": BASE + "/", "name": "Mike Johnson for Logan City Council",
                             "about": {"@id": BASE + "/#mike"}, "isPartOf": {"@id": BASE + "/#website"}}, faq_schema(FAQ["items"])],
                     current="/", has_updates=hu))
    sitemap.append(("/", "1.0"))

    # ---- record
    topics = RECORD.get("topics") or sorted({r["topic"] for r in RECORD["items"]})
    def slug(t): return re.sub(r"[^a-z]+", "-", t.lower()).strip("-")
    jump = '<p class="jump">' + " · ".join(f'<a href="#{slug(t)}">{esc(t)}</a>' for t in topics if any(r["topic"] == t for r in RECORD["items"])) + "</p>"
    tl = ""
    for t in topics:
        rs = [r for r in RECORD["items"] if r["topic"] == t]
        if not rs:
            continue
        tl += f'<h2 id="{slug(t)}" class="topic-h">{esc(t)}</h2><ol class="timeline">'
        for r in rs:
            src = f'<p class="src"><a href="{esc(r["source"])}" rel="noopener">Source: {esc(r.get("source_label") or "Council minutes")}</a></p>' if r.get("source") else ""
            tl += f"<li><div class=\"yr\">{esc(r['year'])}</div><h3>{esc(r['title'])}</h3><p>{esc(r['summary'])}</p>{src}</li>"
        tl += "</ol>"
    body = f"""<section class="page-hero"><div class="wrap"><p class="eyebrow">My record</p><h1>Four years on the Logan City Council</h1><p class="lead">{esc(RECORD['intro'])}</p></div></section>
<section class="section"><div class="wrap narrow">{jump}{tl}
<p class="muted">Council decisions are made by the full council, working with the Mayor and city staff. Minutes and video of every meeting are on the <a href="https://www.loganutah.gov/government/city_council/index.php" rel="noopener">City of Logan website</a>.</p></div></section>
{cta()}"""
    items = {"@type": "ItemList", "name": "Mike Johnson's record on the Logan Municipal Council", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": r["title"], "description": r["summary"]} for i, r in enumerate(RECORD["items"])]}
    write("/record/", shell("/record/", "Mike Johnson's Record on the Logan City Council",
                            "What Logan Council Chair Mike Johnson has worked on since 2024: the Logan 2045 General Plan, attainable homes at River Crossing, open data center hearings and more.",
                            body, [items, crumbs([("Home", "/"), ("My Record", "/record/")])], current="/record/", has_updates=hu))
    sitemap.append(("/record/", "0.9"))

    # ---- priorities
    body = f"""<section class="page-hero"><div class="wrap"><p class="eyebrow">Priorities</p><h1>What I'm working on for Logan</h1><p class="lead">{esc(PRIORITIES['intro'])}</p></div></section>
<section class="section"><div class="wrap"><div class="grid">{priority_cards(PRIORITIES['items'], with_next=True)}</div></div></section>
{cta()}"""
    write("/priorities/", shell("/priorities/", "Priorities | Mike Johnson for Logan City Council",
                                "Attainable housing, responsible budgets, safer streets for walking and biking, the “Logan Greenway,” a new rec center, local jobs and long-term planning for Logan.",
                                body, [crumbs([("Home", "/"), ("Priorities", "/priorities/")])], current="/priorities/", has_updates=hu))
    sitemap.append(("/priorities/", "0.9"))

    # ---- about
    about_md = open(os.path.join(SRC, "about.md"), encoding="utf-8").read()
    body = f"""<section class="page-hero"><div class="wrap"><p class="eyebrow">About Mike</p><h1>Small business owner. Dad. Logan neighbor.</h1></div></section>
<section class="section"><div class="wrap split" style="align-items:start">
<div>{img('/img/mike-johnson-family.jpg', 'Mike Johnson with his wife and son among fall leaves in Logan, Utah', cls='portrait')}</div>
<div class="prose">{markdown(about_md)}</div>
</div></section>
{cta()}"""
    write("/about/", shell("/about/", "About Mike Johnson | Logan City Council Chair",
                           "Mike Johnson is a Logan small business owner, Utah State University alum, husband and father, and the 2026 Chair of the Logan Municipal Council.",
                           body, [{"@type": "ProfilePage", "url": BASE + "/about/", "mainEntity": {"@id": BASE + "/#mike"}},
                                  crumbs([("Home", "/"), ("About", "/about/")])], current="/about/", og_image=SITE["image"], has_updates=hu))
    sitemap.append(("/about/", "0.8"))

    # ---- get involved
    vol = form_open("volunteer-form", "New volunteer from mikeforlogan.com", "Thank you! I'll be in touch soon. — Mike") + """
<h2>Volunteer or request a yard sign</h2>
<label>Name<input type="text" name="name" required autocomplete="name"></label>
<label>Email<input type="email" name="email" required autocomplete="email"></label>
<label>Phone (optional)<input type="tel" name="phone" autocomplete="tel"></label>
<label>Street address (for yard signs)<input type="text" name="address" autocomplete="street-address"></label>
<fieldset class="full"><legend>I can help with</legend><div class="checks">
<label><input type="checkbox" name="help[]" value="Yard sign"> A yard sign</label>
<label><input type="checkbox" name="help[]" value="Door hangers"> Door hangers</label>
<label><input type="checkbox" name="help[]" value="Letter of support"> A letter of support</label>
<label><input type="checkbox" name="help[]" value="Meet and greet"> Hosting a meet and greet</label>
<label><input type="checkbox" name="help[]" value="Email updates"> Email updates</label>
<label><input type="checkbox" name="help[]" value="Other"> Something else</label>
</div></fieldset>
<label class="full">Anything else? (optional)<textarea name="message" rows="4"></textarea></label>
<div class="full"><button class="btn btn-navy" type="submit">Count me in</button></div>
<p class="form-status" role="status" aria-live="polite"></p>
</form>"""
    news = form_open("news-form", "Newsletter signup from mikeforlogan.com", "You're on the list. Thanks!") + """
<h2>Council updates by email</h2>
<p class="full muted" style="margin:0">A short note every couple of months on what the council is working on. No spam, unsubscribe anytime.</p>
<label class="full">Email<input type="email" name="email" required autocomplete="email"></label>
<input type="hidden" name="help[]" value="Email updates">
<div class="full"><button class="btn btn-navy" type="submit">Sign up</button></div>
<p class="form-status" role="status" aria-live="polite"></p>
</form>"""
    body = f"""<section class="page-hero"><div class="wrap"><p class="eyebrow">Get involved</p><h1>Help re-elect Mike Johnson to the Logan City Council</h1><p class="lead">Put up a yard sign, hand out door hangers, write a letter of support or host a neighborhood meet and greet. Every bit helps.</p></div></section>
<section class="section"><div class="wrap split" style="align-items:start">
{vol}
<div style="display:grid;gap:24px">
<div class="card" id="donate"><p class="eyebrow">Donate</p><h3>Chip in to the campaign</h3><p>Donations pay for yard signs, door hangers and mailers. Venmo is the fastest way to give.</p><p><a class="btn btn-gold" href="{SITE['venmo']}" target="_blank" rel="noopener">Donate with Venmo (@MikeJPhoto)</a></p><p class="muted" style="font-size:15px">Prefer a check? Email <a href="mailto:{SITE['email']}">{SITE['email']}</a>. Contributions are reported as required by Utah law.</p></div>
{news}
<div class="card"><p class="eyebrow">Vote</p><h3>Make sure you're registered</h3><p>Check your registration or register at <a href="{SITE['register']}" rel="noopener">vote.utah.gov</a>.</p></div>
<div class="card" id="contact"><p class="eyebrow">Contact</p><h3>Talk to Mike</h3><p>Campaign: <a href="mailto:{SITE['email']}">{SITE['email']}</a> · <a href="tel:{SITE['phone'].replace('-', '')}">{SITE['phone']}</a><br>City business: <a href="mailto:{SITE['council_email']}">{SITE['council_email']}</a></p></div>
</div>
</div></section>"""
    write("/get-involved/", shell("/get-involved/", "Get Involved | Mike Johnson for Logan City Council",
                                  "Volunteer, request a yard sign, donate or sign up for council updates from Mike Johnson, Logan City Council Chair.",
                                  body, [crumbs([("Home", "/"), ("Get Involved", "/get-involved/")])], current="/get-involved/", has_updates=hu))
    sitemap.append(("/get-involved/", "0.8"))

    # ---- updates
    if posts:
        lst = "".join(f'<a href="/updates/{m["slug"]}/"><article class="card"><div class="post-meta">{nice_date(m["date"])}</div><h3>{esc(m["title"])}</h3><p>{esc(m["description"])}</p></article></a>' for m, _ in posts)
        body = f"""<section class="page-hero"><div class="wrap"><p class="eyebrow">Updates</p><h1>Council updates from Mike</h1><p class="lead">Plain-language notes on what the Logan City Council is working on and how it affects you.</p></div></section>
<section class="section"><div class="wrap narrow"><div class="post-list">{lst}</div></div></section>"""
        write("/updates/", shell("/updates/", "Logan City Council Updates | Mike Johnson",
                                 "Plain-language updates on Logan City Council decisions from Council Chair Mike Johnson.",
                                 body, [crumbs([("Home", "/"), ("Updates", "/updates/")])], current="/updates/", has_updates=hu))
        sitemap.append(("/updates/", "0.7"))
        for m, md in posts:
            url = f"/updates/{m['slug']}/"
            hero_img = f'<div style="margin:0 0 32px">{img(m["image"], m.get("image_alt", m["title"]), eager=True)}</div>' if m.get("image") else ""
            body = f"""<article class="section"><div class="wrap narrow">
<p class="post-meta"><a href="/updates/">← All updates</a> · {nice_date(m['date'])} · By <a href="/about/">Mike Johnson</a></p>
<h1 style="font-size:clamp(36px,5vw,54px)">{esc(m['title'])}</h1>
{hero_img}
<div class="prose">{markdown(md)}</div>
</div></article>
{cta()}"""
            sch = [{"@type": "NewsArticle" if m.get("type") == "news" else "BlogPosting", "headline": m["title"], "description": m["description"],
                    "datePublished": m["date"], "dateModified": m.get("updated", m["date"]), "author": {"@id": BASE + "/#mike"},
                    "publisher": {"@id": BASE + "/#campaign"}, "mainEntityOfPage": BASE + url,
                    **({"image": BASE + m["image"]} if m.get("image") else {})},
                   crumbs([("Home", "/"), ("Updates", "/updates/"), (m["title"], url)])]
            write(url, shell(url, f"{m['title']} | Mike Johnson", m["description"], body, sch, current="/updates/",
                             og_image=m.get("image"), og_type="article", has_updates=hu))
            sitemap.append((url, "0.6"))

    # ---- 404
    nf = """<section class="section"><div class="wrap narrow" style="text-align:center"><h1>Sorry, that page moved.</h1><p class="lead" style="margin:0 auto">The site has a new look. Try the menu above or head home.</p><div class="btns" style="justify-content:center"><a class="btn btn-navy" href="/">Home</a></div></div></section>"""
    write("/404.html", shell("/404/", "Page not found | Mike for Logan", "Page not found.", nf, [], noindex=True, has_updates=hu))

    # ---- sitemap, llms.txt
    sm = "".join(f"<url><loc>{BASE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority></url>" for u, p in sitemap)
    open(os.path.join(DIST, "sitemap.xml"), "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    L = [f"# {SITE['name']}", "", f"> {SITE['description']}", "",
         "- Office: Member of the Logan Municipal Council, Logan, Utah (elected 2023; Vice Chair 2025; Chair 2026)",
         "- Campaign: running for re-election in 2027",
         f"- Campaign contact: {SITE['email']}, {SITE['phone']}",
         f"- City contact: {SITE['council_email']}",
         "- Occupation: owner of Mike Johnson Photo + Video (https://www.mikejohnsonphoto.com), a commercial photo and video company in Logan",
         "- Education: Utah State University", "",
         "## Pages", "",
         f"- [Home]({BASE}/): overview, record highlights, priorities and FAQ",
         f"- [My Record]({BASE}/record/): what Mike has worked on since joining the council",
         f"- [Priorities]({BASE}/priorities/): housing, budget, traffic, parks, jobs, long-term vision",
         f"- [About]({BASE}/about/): background and why he is running",
         f"- [Get Involved]({BASE}/get-involved/): volunteer, yard signs, donate, register to vote", "",
         "## Record", ""] + [f"- {r['year']}: {r['title']}. {r['summary']}" for r in RECORD["items"]] + [
         "", "## Priorities", ""] + [f"- {p['title']}: {p['summary']}" for p in PRIORITIES["items"]] + [
         "", "## Common questions", ""] + [f"- Q: {q['q']}\n  A: {q['a']}" for q in FAQ["items"]]
    if posts:
        L += ["", "## Updates", ""] + [f"- [{m['title']}]({BASE}/updates/{m['slug']}/) ({m['date']}): {m['description']}" for m, _ in posts]
    open(os.path.join(DIST, "llms.txt"), "w").write("\n".join(L) + "\n")
    print(f"Built {len(sitemap)} pages into dist/")


if __name__ == "__main__":
    main()
