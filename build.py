#!/usr/bin/env python3
"""Build the static site for The AI Papers."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

BASE_PATH = os.environ.get("BASE_PATH", "").rstrip("/")

REGIMES = [
    {
        "slug": "leviathan",
        "pseudonym": "Leviathan",
        "label": "State-led",
        "tagline": "Sovereign authority is the only reliable guarantor against catastrophe.",
        "color": "#7a1f2b",
        "color_soft": "#f5e6e8",
    },
    {
        "slug": "prometheus",
        "pseudonym": "Prometheus",
        "label": "Company-led",
        "tagline": "Those who build the technology must steward its development.",
        "color": "#b45309",
        "color_soft": "#fbecd5",
    },
    {
        "slug": "demos",
        "pseudonym": "Demos",
        "label": "Decentralized",
        "tagline": "No single hand should hold a power this consequential.",
        "color": "#2f5d3a",
        "color_soft": "#e3eee5",
    },
    {
        "slug": "concord",
        "pseudonym": "Concord",
        "label": "International",
        "tagline": "A planetary technology demands a planetary order.",
        "color": "#1e3a8a",
        "color_soft": "#e2e8f5",
    },
]
REGIMES_BY_SLUG = {r["slug"]: r for r in REGIMES}

QUESTIONS = [
    {
        "slug": "liberty-security",
        "number": "I",
        "title": "Liberty and Security",
        "prompt": "How can your governance regime preserve liberty while providing sufficient security against frontier AI risks?",
    },
    {
        "slug": "job-displacement",
        "number": "II",
        "title": "Work and Displacement",
        "prompt": "How does your regime handle widespread job loss and economic dislocation from AI?",
    },
    {
        "slug": "concentration",
        "number": "III",
        "title": "Concentrations of Power",
        "prompt": "How does your regime prevent dangerous concentrations of AI power, whether in states, firms, or movements?",
    },
]
QUESTIONS_BY_SLUG = {q["slug"]: q for q in QUESTIONS}

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class Doc:
    slug: str
    meta: dict
    body_md: str
    body_html: str = ""


@dataclass
class Essay:
    regime: dict
    question: dict
    title: str
    body_html: str
    rebuttals: list = field(default_factory=list)


@dataclass
class Rebuttal:
    author: dict
    target: dict
    question: dict
    title: str
    body_html: str


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), m.group(2)
    meta = {}
    for line in raw.splitlines():
        line = line.rstrip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def md_to_html(text: str) -> str:
    return markdown.markdown(text, extensions=["extra", "smarty"])


def load_doc(path: Path) -> Doc:
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return Doc(
        slug=path.stem,
        meta=meta,
        body_md=body,
        body_html=md_to_html(body),
    )


def load_regimes() -> dict:
    out = {}
    for r in REGIMES:
        path = CONTENT / "regimes" / f"{r['slug']}.md"
        if path.exists():
            doc = load_doc(path)
            out[r["slug"]] = {**r, "manifesto_html": doc.body_html, "manifesto_title": doc.meta.get("title", r["pseudonym"])}
        else:
            out[r["slug"]] = {**r, "manifesto_html": "", "manifesto_title": r["pseudonym"]}
    return out


def load_questions() -> dict:
    out = {}
    for q in QUESTIONS:
        path = CONTENT / "questions" / f"{q['slug']}.md"
        if path.exists():
            doc = load_doc(path)
            out[q["slug"]] = {**q, "intro_html": doc.body_html, "intro_title": doc.meta.get("title", q["title"])}
        else:
            out[q["slug"]] = {**q, "intro_html": "", "intro_title": q["title"]}
    return out


def load_essays(regimes: dict, questions: dict) -> dict:
    """Returns essays[question_slug][regime_slug] -> Essay (only those that exist)."""
    essays: dict = {}
    for q in QUESTIONS:
        essays[q["slug"]] = {}
        for r in REGIMES:
            path = CONTENT / "essays" / q["slug"] / f"{r['slug']}.md"
            if not path.exists():
                continue
            doc = load_doc(path)
            essay = Essay(
                regime=regimes[r["slug"]],
                question=questions[q["slug"]],
                title=doc.meta.get("title", f"{r['pseudonym']} on {q['title']}"),
                body_html=doc.body_html,
            )
            # Load rebuttals for this essay (rebuttals/<question>/<target>/<author>.md)
            rebuttal_dir = CONTENT / "rebuttals" / q["slug"] / r["slug"]
            if rebuttal_dir.exists():
                for other in REGIMES:
                    if other["slug"] == r["slug"]:
                        continue
                    reb_path = rebuttal_dir / f"{other['slug']}.md"
                    if not reb_path.exists():
                        continue
                    reb_doc = load_doc(reb_path)
                    essay.rebuttals.append(Rebuttal(
                        author=regimes[other["slug"]],
                        target=regimes[r["slug"]],
                        question=questions[q["slug"]],
                        title=reb_doc.meta.get("title", f"{other['pseudonym']} replies"),
                        body_html=reb_doc.body_html,
                    ))
            essays[q["slug"]][r["slug"]] = essay
    return essays


def render_site():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"]),
    )

    regimes = load_regimes()
    questions = load_questions()
    essays = load_essays(regimes, questions)

    # Static assets
    if STATIC.exists():
        shutil.copytree(STATIC, DIST / "static")

    base_ctx = {
        "regimes": regimes,
        "regimes_list": [regimes[r["slug"]] for r in REGIMES],
        "questions": questions,
        "questions_list": [questions[q["slug"]] for q in QUESTIONS],
        "base_path": BASE_PATH,
    }

    # Home
    (DIST / "index.html").write_text(
        env.get_template("home.html").render(**base_ctx, page="home"),
        encoding="utf-8",
    )

    # Questions
    for q in QUESTIONS:
        out_dir = DIST / "questions" / q["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            env.get_template("question.html").render(
                **base_ctx,
                page="question",
                question=questions[q["slug"]],
                essays=[essays[q["slug"]].get(r["slug"]) for r in REGIMES],
            ),
            encoding="utf-8",
        )

    # Regimes
    for r in REGIMES:
        out_dir = DIST / "regimes" / r["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        regime_essays = []
        for q in QUESTIONS:
            essay = essays[q["slug"]].get(r["slug"])
            if essay:
                regime_essays.append(essay)
        (out_dir / "index.html").write_text(
            env.get_template("regime.html").render(
                **base_ctx,
                page="regime",
                regime=regimes[r["slug"]],
                regime_essays=regime_essays,
            ),
            encoding="utf-8",
        )

    # Individual essay pages
    for q in QUESTIONS:
        for r in REGIMES:
            essay = essays[q["slug"]].get(r["slug"])
            if not essay:
                continue
            out_dir = DIST / "essays" / q["slug"] / r["slug"]
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.html").write_text(
                env.get_template("essay.html").render(
                    **base_ctx,
                    page="essay",
                    essay=essay,
                ),
                encoding="utf-8",
            )

    # About
    about_path = CONTENT / "about.md"
    if about_path.exists():
        doc = load_doc(about_path)
        (DIST / "about").mkdir(exist_ok=True)
        (DIST / "about" / "index.html").write_text(
            env.get_template("about.html").render(
                **base_ctx,
                page="about",
                body_html=doc.body_html,
            ),
            encoding="utf-8",
        )

    # Quick stats
    n_essays = sum(len(v) for v in essays.values())
    n_rebuttals = sum(len(e.rebuttals) for v in essays.values() for e in v.values())
    print(f"Built {n_essays} essays and {n_rebuttals} rebuttals -> {DIST}")


if __name__ == "__main__":
    render_site()
