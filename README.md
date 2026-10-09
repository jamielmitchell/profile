# Jamie Mitchell · Personal Website

Live at **https://jamielmitchell.github.io/profile/**

## Where to edit what

| I want to change… | Edit this file |
|---|---|
| The About page (home page) | `index.md` |
| The CV page | `cv.md` |
| The downloadable CV PDF | Replace `assets/files/Mitchell_CV_long.pdf` (keep the same name) |
| Teaching | `teaching.md` |
| Service, leadership, mentorship | `service.md` |
| My name, sidebar bio, location, or profile links | `_config.yml` |
| My photo | Replace `assets/images/profile.jpg` (keep the same name) |
| The top menu (add, remove, or reorder pages) | `_data/navigation.yml` |
| Colors and fonts | The top of `assets/css/site.css` |
| Hide, fix, or add a publication | `_data/publication_settings.yml` |
| Add a peer review that isn't on ORCID | `_data/peer_reviews_manual.yml` |

Pages are written in [Markdown](https://www.markdownguide.org/cheat-sheet/): `## Heading`, `**bold**`, `*italic*`, `- bullet`, `[link text](https://...)`.

### Adding a new page

1. Copy `service.md` to a new file, e.g. `talks.md`.
2. Change the `title:` and `permalink:` at the top (e.g. `permalink: /talks/`).
3. Add it to the menu in `_data/navigation.yml`.

## Publications and peer reviews update themselves

The Publications page and the Peer Review list on the Service page are built
from your [ORCID record](https://orcid.org/0009-0002-0854-1875). Every Monday
(and every time you push a change), GitHub:

1. pulls your works and peer reviews from ORCID,
2. looks up full author lists and abstracts on Crossref,
3. combines each preprint with its published version,
4. links your datasets and code to the paper they belong to,
5. highlights papers where you're first author.

**To add a publication:** add it to ORCID. It'll appear on the site the next Monday.
To update right away: on GitHub, go to **Actions → Update from ORCID and deploy → Run workflow**.

**To tweak how a publication shows up** (hide one, mark co-first authorship,
add a note like "Under review", add something that isn't on ORCID), edit
`_data/publication_settings.yml`. Instructions are inside the file.

**To add a peer review that isn't on ORCID**, add two lines to
`_data/peer_reviews_manual.yml`. It's merged with your ORCID reviews on the Service page.

Don't edit `_data/publications.json` or `_data/peer_reviews.json` by hand.
They get overwritten each time the site rebuilds.

## Previewing changes on your computer

One-time setup (already done on Jamie's Mac):

```sh
brew install ruby@3.3
cd ~/claude_projects/profile
export PATH="/opt/homebrew/opt/ruby@3.3/bin:$PATH"
bundle config set --local path vendor/bundle
bundle install
```

Each time:

```sh
cd ~/claude_projects/profile
export PATH="/opt/homebrew/opt/ruby@3.3/bin:$PATH"
bundle exec jekyll serve
```

Then open http://localhost:4000/profile/. Pages reload as you save
(except `_config.yml`: stop with Ctrl+C and run the command again).

To refresh the publication list locally: `python3 scripts/update_from_orcid.py`

## How the pieces fit together

```
index.md, cv.md, teaching.md,     ← your pages (edit these)
  service.md, publications.md
_config.yml                       ← name, sidebar, links
_data/
  navigation.yml                  ← top menu
  publication_settings.yml        ← publication tweaks
  peer_reviews_manual.yml         ← reviews not on ORCID (edit this)
  publications.json               ← auto-generated from ORCID
  peer_reviews.json               ← auto-generated from ORCID
_layouts/default.html             ← page frame: menu + sidebar + footer
_includes/sidebar.html            ← the sidebar
_includes/publication.html        ← how one publication is displayed
assets/                           ← stylesheet, images, CV PDF
scripts/update_from_orcid.py      ← the ORCID updater
.github/workflows/deploy.yml      ← tells GitHub to update and publish the site
```
