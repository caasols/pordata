#!/usr/bin/env python3
"""Fetch the reuse terms of the three upstream sources (roadmap 13).

Item 13 is the only thing gating item 14, and decision 1 is the
project's binding constraint: values are served from upstream *under
their terms*, so the archive job must refuse to write a series whose
source has no recorded licence entry. Decision 7 is why this exists as a
fetch rather than as a paragraph — an upstream was once asserted from
memory, and this sandbox has no route to ine.pt or europa.eu, so the
reading has to come from Actions.

**This spike does not decide anything.** It retrieves candidate
terms-of-use pages, records what each one actually returned, and saves
the text so a human reads the real words rather than a summary of a
summary. The four things item 13 asks for — licence name, URL, the exact
attribution string required, and whether redistribution of *derived*
series is permitted, not merely display — are judgements about a legal
document, and they stay the owner's.

**Candidates, not addresses.** Nobody here knows the current
terms-of-use URL for any of the three, so guessing one and reporting a
404 as "no licence found" would be the A3 mistake again: a negative
result produced by a wrong query. Each source gets several candidates
plus its front page, every outcome is recorded including the failures,
and the report says plainly which ones resolved.
"""

import pathlib
import re
import time
import urllib.error
import urllib.request

USER_AGENT = (
    "pordata-map research (github.com/caasols/pordata; "
    "reading reuse terms before archiving any values)"
)
RAW_DIR = pathlib.Path("data/spikes/raw/licences")
REPORT = pathlib.Path("data/spikes/licences.md")
DELAY_SECONDS = 8
TIMEOUT = 45
MAX_TEXT = 20000

# Front pages are included on purpose: when every specific candidate
# misses, the footer of the front page is where the real link lives, and
# a recorded miss plus a front page beats a confident wrong answer.
CANDIDATES = {
    "INE": [
        "https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_princ_termos",
        "https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_cont_inst&INST=6251013",
        "https://www.ine.pt/",
    ],
    "Eurostat": [
        "https://ec.europa.eu/eurostat/about-us/policies/copyright",
        "https://commission.europa.eu/legal-notice_en",
        "https://ec.europa.eu/eurostat",
    ],
    "BPstat": [
        "https://bpstat.bportugal.pt/conteudos/quem-somos",
        "https://bpstat.bportugal.pt/",
        "https://www.bportugal.pt/pagina/termos-e-condicoes",
    ],
}

# What a reader is looking for in the returned text. Reported as hit
# counts with the surrounding sentence, never as a verdict.
TERMS = re.compile(
    r"reutiliza|reuse|redistribu|licen[çc]|licence|license|creative commons"
    r"|CC[ -]BY|atribui|attribution|copyright|direitos de autor"
    r"|termos de utiliza|terms of use|condi[çc][õo]es de utiliza",
    re.I)
TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.S | re.I)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def strip_markup(html: str) -> str:
    text = TAG.sub(" ", html)
    for entity, char in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                         ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def sentences_with_terms(text: str, limit: int = 12) -> list[str]:
    """Sentences a reader would want to see, in the source's own words.

    Quoted rather than paraphrased: the whole point of item 13 is that
    the exact attribution string matters, and a paraphrase of a licence
    is not a licence."""
    out = []
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        if TERMS.search(sentence) and 30 < len(sentence) < 600:
            out.append(sentence.strip())
        if len(out) == limit:
            break
    return out


def fetch(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
            return {"url": url, "status": response.status,
                    "final_url": response.url, "bytes": len(body),
                    "body": body.decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        return {"url": url, "status": exc.code, "final_url": url,
                "bytes": 0, "body": "", "error": f"HTTP {exc.code}"}
    except Exception as exc:                       # noqa: BLE001
        return {"url": url, "status": 0, "final_url": url, "bytes": 0,
                "body": "", "error": f"{type(exc).__name__}: {exc}"}


def slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.lower())[:80].strip("-")


def render(results: dict) -> str:
    lines = [
        "# Upstream reuse terms — what the pages actually say (roadmap 13)",
        "",
        "Fetched by `scripts/spike_licences.py` via Actions, because this "
        "sandbox has no route to any of the three. **Nothing here is a "
        "decision.** Item 13 asks for four things per source — licence "
        "name, URL, the exact attribution string it requires, and whether "
        "it permits redistributing *derived* series rather than merely "
        "displaying them — and all four are judgements about a legal "
        "document. They stay the owner's. This is the reading material, "
        "quoted in the source's own words, so the call can be made in "
        "minutes instead of half an hour of hunting.",
        "",
        "Candidate URLs, not addresses: nobody knew the current terms page "
        "for any of the three, so every outcome is recorded — including "
        "the misses. A 404 here means the guess was wrong, never that a "
        "source has no terms.",
        "",
        "**The archive job (item 14) refuses to write any series whose "
        "source has no recorded entry.** That gate is the reason this is "
        "worth half an hour of anyone's attention.",
        "",
    ]
    for source, attempts in results.items():
        lines += [f"## {source}", ""]
        for attempt in attempts:
            mark = "ok" if attempt["status"] == 200 else "MISS"
            lines.append(f"- **{mark}** `{attempt['url']}` — "
                         f"status {attempt['status']}, "
                         f"{attempt['bytes'] / 1024:.0f} KB"
                         + (f" — {attempt['error']}" if attempt.get("error")
                            else ""))
            if attempt.get("final_url") != attempt["url"]:
                lines.append(f"  - redirected to `{attempt['final_url']}`")
            if attempt.get("title"):
                lines.append(f"  - title: {attempt['title']}")
        quoted = [(a, s) for a in attempts for s in a.get("sentences", [])]
        if quoted:
            lines += ["", f"### {source} — sentences that mention reuse, "
                          "licensing or attribution", ""]
            for attempt, sentence in quoted[:20]:
                lines.append(f"- {sentence}")
                lines.append(f"  - *from* `{attempt['final_url']}`")
        else:
            lines += ["", f"No sentence on any {source} candidate matched "
                          "the reuse/licence vocabulary. That is a result "
                          "about these URLs, not about the source — read "
                          "the saved front page for the real link.", ""]
        lines.append("")
    lines += [
        "## Record the outcome in `context.md` item 13",
        "",
        "For each source: licence name, its URL, the exact attribution "
        "string, and redistribution-of-derived-series yes/no. Then item 14 "
        "can be built, and its licence registry stops refusing.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {}
    first = True
    for source, urls in CANDIDATES.items():
        results[source] = []
        for url in urls:
            if not first:
                time.sleep(DELAY_SECONDS)
            first = False
            print(f"fetching {url}")
            attempt = fetch(url)
            if attempt["body"]:
                text = strip_markup(attempt["body"])
                title = TITLE.search(attempt["body"])
                attempt["title"] = strip_markup(title.group(1)) if title else ""
                attempt["sentences"] = sentences_with_terms(text)
                (RAW_DIR / f"{slug(url)}.txt").write_text(
                    text[:MAX_TEXT], encoding="utf-8")
            attempt.pop("body", None)
            results[source].append(attempt)
    REPORT.write_text(render(results), encoding="utf-8")
    served = sum(1 for a in results.values() for r in a if r["status"] == 200)
    total = sum(len(a) for a in results.values())
    print(f"licences: {served}/{total} candidates served; report at {REPORT}")


if __name__ == "__main__":
    main()
