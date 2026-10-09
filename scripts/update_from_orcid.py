#!/usr/bin/env python3
"""Rebuild the site's publication and peer-review lists from ORCID.

Usage:  python3 scripts/update_from_orcid.py

Reads   _data/publication_settings.yml
Writes  _data/publications.json   (shown on the Publications page)
        _data/peer_reviews.json   (shown on the Service page)

How it works:
  1. Fetch your works and peer reviews from the public ORCID API.
  2. Look up each DOI on Crossref for full author lists, venue and abstract.
  3. Fold each preprint into its published version (using Crossref's
     preprint links, falling back to matching titles).
  4. Attach datasets to the paper they belong to (using DataCite links),
     and drop anything that isn't a paper (datasets, corrections, etc.).
  5. Apply your tweaks from publication_settings.yml.

Requires PyYAML (pip install pyyaml). Everything else is standard library.
"""
import difflib
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "_data"
USER_AGENT = "profile-site-orcid-sync (https://github.com/jamielmitchell/profile)"

PREPRINT_DOI_PREFIXES = ("10.1101/", "10.64898/", "10.31219/", "10.31234/", "10.48550/", "10.21203/")
SKIP_TITLE = re.compile(r"^\s*(author correction|correction|erratum|corrigendum|retraction)\b", re.I)
# ORCID types that aren't papers. These are checked on DataCite: dissertations are
# kept, datasets are linked to their paper, and everything else is dropped.
NON_PAPER_TYPES = {"data-set", "other", "software", "physical-object", "lecture-speech", "dissertation-thesis"}
MAX_AUTHORS_SHOWN = 10


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def get_json(url, accept="application/json", tries=3):
    req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == tries - 1:
                raise
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
        time.sleep(2 * (attempt + 1))


def orcid(path, orcid_id):
    return get_json(f"https://pub.orcid.org/v3.0/{orcid_id}/{path}")


def crossref_work(doi):
    data = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    return data["message"] if data else None


_datacite_cache = {}


def datacite_attrs(doi):
    if doi not in _datacite_cache:
        data = get_json("https://api.datacite.org/dois/" + urllib.parse.quote(doi))
        _datacite_cache[doi] = data["data"]["attributes"] if data else None
    return _datacite_cache[doi]


def datacite_record(doi):
    """Return (related links, description) for a dataset DOI."""
    attrs = datacite_attrs(doi)
    if not attrs:
        return [], ""
    related = [r.get("relatedIdentifier", "") for r in attrs.get("relatedIdentifiers") or []]
    description = " ".join(strip_tags(d.get("description", "")) for d in attrs.get("descriptions") or [])
    return related, description


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def strip_tags(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def clean_abstract(jats):
    """Turn Crossref's JATS-XML abstract into a list of plain paragraphs."""
    if not jats:
        return []
    jats = re.sub(r"<jats:title>\s*Abstract\s*</jats:title>", "", jats, flags=re.I)
    # Keep section titles ("Methods") as their own short paragraph
    parts = re.split(r"</?jats:(?:p|title|sec)[^>]*>", jats)
    paragraphs = [re.sub(r"\s+", " ", strip_tags(p)) for p in parts]
    return [p for p in paragraphs if p and p.lower() != "abstract"]


def normalize_title(title):
    return re.sub(r"[^a-z0-9 ]", "", strip_tags(title).lower().replace("[preprint]", "")).strip()


def similar(a, b):
    return difflib.SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def initials(given):
    out = []
    for part in re.split(r"[\s.]+", given or ""):
        if part:
            out.append("-".join(p[0].upper() + "." for p in part.split("-") if p))
    return " ".join(out)


def is_me(author, my_names):
    family = (author.get("family") or "").lower()
    given = (author.get("given") or "").lower()
    return any(family == n["family"].lower() and given.startswith(n["given_initial"].lower()) for n in my_names)


def format_authors(authors, my_names):
    """List of {name, me}. Long lists are shortened around your position."""
    people = []
    for a in authors:
        if a.get("family"):
            name = a["family"] + (", " + initials(a.get("given")) if a.get("given") else "")
        else:
            name = a.get("name", "")
        people.append({"name": name, "me": is_me(a, my_names)})
    if len(people) <= MAX_AUTHORS_SHOWN:
        return people
    me_idx = next((i for i, p in enumerate(people) if p["me"]), None)
    keep = {0, 1, 2, len(people) - 1}
    if me_idx is not None:
        keep.add(me_idx)
    short, last = [], -1
    for i in sorted(keep):
        if i > last + 1:
            short.append({"name": "…", "me": False})
        short.append(people[i])
        last = i
    return short


# ---------------------------------------------------------------------------
# Building records
# ---------------------------------------------------------------------------
def year_of(msg):
    for key in ("published", "published-print", "published-online", "posted", "issued", "created"):
        parts = (msg.get(key) or {}).get("date-parts") or [[None]]
        if parts[0] and parts[0][0]:
            return parts[0][0]
    return None


def classify(doi, cr_type, orcid_type, venue):
    if (cr_type == "posted-content" or orcid_type == "preprint"
            or doi.startswith(PREPRINT_DOI_PREFIXES) or "rxiv" in (venue or "").lower()):
        return "Preprint"
    if cr_type in ("book-chapter", "reference-entry", "book-section", "book-part") or orcid_type == "book-chapter":
        return "Book chapter"
    if cr_type in ("book", "monograph", "edited-book") or orcid_type == "book":
        return "Book"
    if cr_type == "proceedings-article" or orcid_type == "conference-paper":
        return "Conference paper"
    return "Journal article"


def build_record(summary, doi, settings):
    cr = crossref_work(doi) or {}
    orcid_title = summary["title"]["title"]["value"]
    orcid_year = ((summary.get("publication-date") or {}).get("year") or {}).get("value")
    orcid_venue = (summary.get("journal-title") or {}).get("value")

    venue = (cr.get("container-title") or [None])[0]
    if not venue and cr.get("institution"):
        venue = cr["institution"][0].get("name")
    venue = venue or orcid_venue or cr.get("publisher") or ""
    if "rxiv" in venue.lower():
        venue = venue.split(":")[0].strip()  # "bioRxiv : the preprint server..." -> "bioRxiv"
    rec_type = classify(doi, cr.get("type"), summary.get("type"), venue)

    relation = cr.get("relation") or {}
    return {
        "doi": doi,
        "title": strip_tags((cr.get("title") or [orcid_title])[0]),
        "authors_raw": cr.get("author") or [],
        "year": year_of(cr) or (int(orcid_year) if orcid_year else None),
        "venue": venue,
        "type": rec_type,
        "url": "https://doi.org/" + doi,
        "abstract": clean_abstract(cr.get("abstract")),
        "preprint_of": [r["id"].lower() for r in relation.get("is-preprint-of", []) if r.get("id-type") == "doi"],
        "has_preprint": [r["id"].lower() for r in relation.get("has-preprint", []) if r.get("id-type") == "doi"],
    }


def dissertation_record(doi, attrs):
    """Build a record for a dissertation registered on DataCite (e.g. Stanford Digital Repository)."""
    creators = [c.get("name", "") for c in attrs.get("creators") or []]
    institution = next((c.split(".")[0] for c in creators if "University" in c), attrs.get("publisher", ""))
    family, _, given = creators[0].partition(", ") if creators else ("", "", "")
    abstract = [strip_tags(d["description"]) for d in attrs.get("descriptions") or []
                if d.get("descriptionType") == "Abstract" and d.get("description")]
    return {
        "doi": doi,
        "title": re.sub(r"\s+:\s+", ": ", strip_tags(attrs["titles"][0]["title"])),
        "authors_raw": [{"family": family, "given": given}],
        "year": attrs.get("publicationYear"),
        "venue": f"PhD dissertation, {institution}",
        "type": "Dissertation",
        "url": "https://doi.org/" + doi,
        "abstract": abstract,
        "preprint_of": [],
        "has_preprint": [],
    }


def work_dois(group):
    dois = []
    for s in group["work-summary"]:
        for eid in (s.get("external-ids") or {}).get("external-id", []):
            if eid["external-id-type"] == "doi" and eid.get("external-id-relationship") == "self":
                d = eid["external-id-value"].lower().replace("https://doi.org/", "")
                if d not in dois:
                    dois.append(d)
    return dois


def merge_preprints(records):
    published = [r for r in records if r["type"] != "Preprint"]
    preprints = sorted((r for r in records if r["type"] == "Preprint"), key=lambda r: -(r["year"] or 0))
    standalone = []
    for pre in preprints:
        target = next((p for p in published
                       if p["doi"] in pre["preprint_of"] or pre["doi"] in p["has_preprint"]), None)
        if not target:
            target = next((p for p in published
                           if similar(p["title"], pre["title"]) >= 0.85
                           and (p["year"] or 0) >= (pre["year"] or 0)), None)
        if target:
            target.setdefault("preprint_url", pre["url"])
            target.setdefault("merged_dois", []).append(pre["doi"])
            if not target["abstract"]:
                target["abstract"] = pre["abstract"]
            continue
        # Two versions of the same preprint (e.g. on different servers): keep the newest
        if any(similar(s["title"], pre["title"]) >= 0.9 for s in standalone):
            continue
        standalone.append(pre)
    return published + standalone


def attach_datasets(records, dataset_dois):
    """Link each dataset (and any GitHub repo it lists) to its paper."""
    for ds in dataset_dois:
        related, description = datacite_record(ds)
        related_text = " ".join(related).lower()
        match = next((r for r in records
                      if any(d in related_text for d in [r["doi"], *r.get("merged_dois", [])])), None)
        if not match and description:
            # No explicit link: fall back to the dataset description matching the paper's abstract
            match = next((r for r in records if r["abstract"] and difflib.SequenceMatcher(
                None, description[:300].lower(), " ".join(r["abstract"])[:300].lower()).ratio() >= 0.8), None)
        if match:
            match.setdefault("data_url", "https://doi.org/" + ds)
            code = next((u for u in related if "github.com" in u), None)
            if code:
                match.setdefault("code_url", code)


def build_publications(settings):
    oid = settings["orcid"]
    works = orcid("works", oid) or {"group": []}
    records, dataset_dois = [], []
    for group in works["group"]:
        summary = group["work-summary"][0]
        dois = work_dois(group)
        if not dois:
            print(f"  skipping (no DOI): {summary['title']['title']['value']}", file=sys.stderr)
            continue
        if summary.get("type") in NON_PAPER_TYPES:
            attrs = datacite_attrs(dois[0]) or {}
            if (attrs.get("types") or {}).get("resourceTypeGeneral") == "Dissertation":
                records.append(dissertation_record(dois[0], attrs))
            elif summary.get("type") == "data-set" or dois[0].startswith("10.25740/"):
                dataset_dois.extend(dois)
            continue
        if SKIP_TITLE.match(summary["title"]["title"]["value"]):
            continue
        records.append(build_record(summary, dois[0], settings))

    records = merge_preprints(records)
    attach_datasets(records, dataset_dois)

    hide = {d.lower() for d in settings.get("hide") or []}
    first = {d.lower() for d in settings.get("first_author") or []}
    fixes = {k.lower(): v for k, v in (settings.get("fixes") or {}).items()}
    my_names = settings.get("my_names") or []

    out = []
    for r in records:
        if r["doi"] in hide or any(d in hide for d in r.get("merged_dois", [])):
            continue
        authors = r.pop("authors_raw")
        r["first_author"] = bool(authors and is_me(authors[0], my_names)) or r["doi"] in first
        r["authors"] = format_authors(authors, my_names)
        for key in ("preprint_of", "has_preprint", "merged_dois"):
            r.pop(key, None)
        r.update(fixes.get(r["doi"], {}))
        out.append(r)

    for extra in settings.get("extra") or []:
        e = dict(extra)
        e["authors"] = [{"name": n, "me": any(n.lower().startswith(m["family"].lower()) for m in my_names)}
                        for n in e.get("authors", [])]
        e.setdefault("first_author", bool(e["authors"] and e["authors"][0]["me"]))
        e.setdefault("abstract", [])
        out.append(e)

    # Newest first; within a year, published work before preprints
    out.sort(key=lambda r: (-(int(r.get("year") or 0)), r.get("type") == "Preprint", r["title"].lower()))
    return out


def build_peer_reviews(settings):
    """One {journal, year} entry per review. The Service page merges these with
    _data/peer_reviews_manual.yml, so both lists use the same format."""
    data = orcid("peer-reviews", settings["orcid"]) or {"group": []}
    reviews = []
    for group in data["group"]:
        issn = next((e["external-id-value"].replace("issn:", "")
                     for e in (group.get("external-ids") or {}).get("external-id", [])
                     if e["external-id-value"].startswith("issn:")), None)
        years = []
        for sub in group.get("peer-review-group", []):
            for s in sub.get("peer-review-summary", []):
                y = ((s.get("completion-date") or {}).get("year") or {}).get("value")
                if y:
                    years.append(int(y))
        name = None
        if issn:
            j = get_json("https://api.crossref.org/journals/" + issn)
            name = j["message"]["title"] if j else None
        if not name:
            s = group["peer-review-group"][0]["peer-review-summary"][0]
            name = (s.get("convening-organization") or {}).get("name", "Journal")
        reviews.extend({"journal": name, "year": y} for y in years)
    reviews.sort(key=lambda r: (r["journal"].lower(), r["year"]))
    return reviews


def write_json(path, data):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text() == text:
        print(f"  {path.name}: no changes")
        return
    path.write_text(text)
    print(f"  {path.name}: updated")


def main():
    settings = yaml.safe_load((DATA / "publication_settings.yml").read_text())
    print("Fetching publications from ORCID + Crossref...")
    pubs = build_publications(settings)
    print(f"  {len(pubs)} publications ({sum(p['first_author'] for p in pubs)} first-author)")
    write_json(DATA / "publications.json", pubs)
    print("Fetching peer reviews from ORCID...")
    reviews = build_peer_reviews(settings)
    print(f"  {len(reviews)} reviews for {len({r['journal'] for r in reviews})} journal(s)")
    write_json(DATA / "peer_reviews.json", reviews)


if __name__ == "__main__":
    main()
