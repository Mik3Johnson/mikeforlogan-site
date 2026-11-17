# mikeforlogan.com

Campaign website for Mike Johnson, Logan (Utah) Municipal Council. Same setup as mikejohnsonphoto.com:
GitHub → Cloudflare (free), edited with Pages CMS or by asking Claude.

## Where things live

- `src/record.json` — My Record (accomplishments). Mark up to 4 as featured for the home page.
- `src/priorities.json` — Priorities.
- `src/updates/` — Council updates, one Markdown file per post (the Updates menu item appears once there's one published post).
- `src/about.md` — About page text.
- `src/faq.json` — Common questions (also used for Google/AI search structured data).
- `src/site.json` — contact info, donation link, "Paid for by" line, form key.
- `img/` — photos. Expected: `mike-johnson-headshot.jpg` (hero, portrait 4:5), `mike-johnson-community.jpg` (home, 4:3), `mike-johnson-family.jpg` (About, 4:3). Missing photos show a placeholder.
- `static/` — robots.txt, `_redirects` (old Squarespace URLs), `_headers`, CSS/JS, favicon.
- `build.py` — builds everything into `dist/` with titles, descriptions, schema.org data, `sitemap.xml` and `llms.txt`.

Cloudflare: build command `python3 build.py`, deploy command `npx wrangler deploy`.

## Preview locally

```
python3 build.py && cd dist && python3 -m http.server 8000
```

## Editing (Pages CMS)

Sign in at https://app.pagescms.org with GitHub and open **Mik3Johnson/mikeforlogan-site**. Every save is a commit; the live site updates in about 2 minutes.
