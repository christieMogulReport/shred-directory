# Where to Shred Documents

Static directory site (Python + Markdown) published at https://shred.christiejustice.com via GitHub Pages. Brand: Black Swan Sibyl.

## Commands
```bash
python3 build.py            # build into dist/ (drafts excluded)
python3 serve.py            # build and preview at http://127.0.0.1:8000
python3 build.py --drafts   # include draft: true pages
```
The first run creates a local `.venv` and installs `requirements.txt`.

## Add a page
Create `content/pages/<slug>.md` with front matter: `title`, `slug`, `description`, `last_updated` (YYYY-MM-DD), optional `draft`, optional `listings` (each with `name`, `url`, optional `affiliate_url`, `summary`, `category`). Quote any value containing a colon. Homepage intro is `content/home.md`; site settings are `config.yml`.

## Rules for content
- Only real, sourced information. Link the source for hours, prices, and event dates, and say "call to confirm".
- Don't publish expired event dates as upcoming. Label past events as past.
- Before adding an affiliate link, fill `affiliate_disclosure` in `config.yml`.

## Deploy
Push to `main`; `.github/workflows/pages.yml` builds and deploys to GitHub Pages. `static/CNAME` holds the custom domain.
`data/` and `tools/` are gitignored (private earnings and outreach notes).
