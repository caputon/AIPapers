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

# Editorial cruxes per question — the underlying disagreements that
# remain after all four essays have made their case. Body is rendered
# as markdown.
CRUXES = {
    "liberty-security": [
        {
            "title": "Offense-defense balance.",
            "body": "Does the broad availability of frontier capability favor defenders — through more eyes on the system, more counter-applications, and more distributed expertise — or attackers, who acquire an asymmetric capability the polity cannot recall? Demos assumes the former. Leviathan and Prometheus assume the latter. The empirical record is thin and contested, and most of the disagreement among the regimes resolves into different priors on this question.",
        },
        {
            "title": "State capacity versus laboratory knowledge.",
            "body": "Can a public agency develop the technical fluency to govern frontier systems on the timescale they evolve, or does the operational knowledge required for safety necessarily accumulate inside the laboratories? Leviathan and Concord defer to public capacity built over time. Prometheus holds that the laboratory is the irreducible site of safety knowledge and that displacing it weakens the work it produces.",
        },
        {
            "title": "Sufficiency of unilateral action.",
            "body": "Can a single polity meaningfully secure itself against frontier AI risk through domestic instruments alone? Leviathan, Prometheus, and Demos answer at the polity level. Concord argues that frontier AI is sufficiently transboundary that any unilateral regime is undermined by foreign development arriving over the same network.",
        },
    ],
    "job-displacement": [
        {
            "title": "Substitution versus complementarity.",
            "body": "Is frontier AI primarily substituting for cognitive labor, or augmenting it? Prometheus argues that complementary creation will, on average, dominate substitution — and points to early data from the laboratories' own customers. Leviathan and Demos read the same data as masking a sharper substitutionary trajectory at the relevant margin. The implied transition magnitudes differ by an order of magnitude.",
        },
        {
            "title": "Cause of displacement: technology or concentration.",
            "body": "Is the displacement caused by the technology itself, calling for income and retraining instruments downstream — or by the concentration of who controls the technology, calling for structural plurality upstream? Leviathan, Prometheus, and Concord locate the response at the income or protection layer. Demos locates it at the layer of who holds the tools.",
        },
        {
            "title": "Durability of domestic instruments under arbitrage.",
            "body": "Can a polity sustain meaningful AI-rents taxation, labor protections, or transition financing in isolation, or do international competitive pressures erode them within a generation? Leviathan and Demos design at the domestic level and treat international coordination as a later phase. Concord argues durability requires international coordination from the start.",
        },
    ],
    "concentration": [
        {
            "title": "Public authority: instrument or danger.",
            "body": "Is sovereign authority a necessary check on dangerous private concentration, or itself a concentration to be feared? Leviathan defends the agency as constitutionally limited and democratically accountable. Demos argues that an agency with licensing, antitrust, and interruption authority is — on the day it is operational — the most consequential actor in the AI economy, and that constitutional limits are not the same as structural plurality.",
        },
        {
            "title": "Where is plurality achievable.",
            "body": "Is genuine plurality sustainable at the model frontier, where capital intensity is high (Prometheus), or only at the layers above the frontier (Demos)? Should plurality be maintained through industry commitments and lighter antitrust (Prometheus) or through aggressive structural breakups (Leviathan and Demos)? The disagreement turns on the underlying economics of frontier development — capital, network effects, talent — and on what level of intervention is required to keep the configuration contestable.",
        },
        {
            "title": "Reach of domestic instruments.",
            "body": "Do antitrust and structural separation in a single polity reach the most consequential AI concentrations, or are those concentrations transboundary by construction? Leviathan, Prometheus, and Demos design at the polity level. Concord argues the most consequential concentrations exceed any single polity's reach, and that without coordinated multilateral action the domestic instruments operate on the smaller half of the problem.",
        },
    ],
}

# Position grid — concrete policy levers and where each regime stands.
# Stance is a 1-3 word label. Summary is a 20-30 word qualifier.
# `essay` points to the question slug whose essay best supports the position.
COMPARISON_GROUPS = [
    {
        "title": "Safety and catastrophic risk",
        "summary": "Instruments aimed at preventing the worst uses of frontier AI.",
        "levers": [
            {
                "slug": "frontier-licensing",
                "title": "Frontier compute licensing",
                "prompt": "Should training runs above a defined compute or capability threshold require government authorization?",
                "positions": {
                    "leviathan": {"stance": "Central instrument", "summary": "Licensure of frontier compute is foundational; thresholds set so ordinary research is unaffected and no frontier actor escapes oversight by accident.", "essay": "liberty-security"},
                    "prometheus": {"stance": "Conditional", "summary": "Licensure where genuinely necessary, designed in concert with the laboratories' technical input, calibrated not to freeze a moving target.", "essay": "liberty-security"},
                    "demos": {"stance": "Skeptical", "summary": "A single licensing agency is itself a concentration; public authority on this question should be plural and distributed, not unified.", "essay": "liberty-security"},
                    "concord": {"stance": "Yes, with verification", "summary": "Domestic licensure is the precondition; its credibility depends on multilateral verification that other states have built the same.", "essay": "liberty-security"},
                },
            },
            {
                "slug": "open-weights-frontier",
                "title": "Open weights at the frontier",
                "prompt": "Should the weights of frontier-scale models be released openly by default?",
                "positions": {
                    "leviathan": {"stance": "Opposes", "summary": "Frontier weights warrant classification when they confer identified catastrophic capabilities; release should be the exception, not the default.", "essay": "liberty-security"},
                    "prometheus": {"stance": "Opposes at the frontier", "summary": "Open release distributes capability in a form from which retreat is impossible; closure should be the default for hazardous frontier capabilities.", "essay": "liberty-security"},
                    "demos": {"stance": "Central commitment", "summary": "Open weights are the default; narrow, technically grounded exceptions for identified catastrophic hazard. Closure must be justified, not assumed.", "essay": "liberty-security"},
                    "concord": {"stance": "Conditional", "summary": "Acceptable below a treaty floor on identified catastrophic capabilities; foreclosed above it by mutual commitment among the parties.", "essay": "concentration"},
                },
            },
            {
                "slug": "pre-deployment-eval",
                "title": "Pre-deployment hazard evaluation",
                "prompt": "Should frontier models be evaluated for hazardous capabilities before they are deployed?",
                "positions": {
                    "leviathan": {"stance": "Mandatory", "summary": "Standardized hazard tests by developer and independent reviewers; findings of significant hazard trigger remediation before deployment, not after.", "essay": "liberty-security"},
                    "prometheus": {"stance": "Mandatory", "summary": "Pre-release red-teaming on biosecurity, cyber, mass persuasion, and self-replication; findings reported to a credible recipient, not suppressed.", "essay": "liberty-security"},
                    "demos": {"stance": "Yes, plural", "summary": "Evaluation by parties with no financial stake in the conclusions; civic auditors and academics, not only the developer or its agency.", "essay": "liberty-security"},
                    "concord": {"stance": "Yes, shared protocol", "summary": "Shared international evaluation methodology on highest-consequence capabilities; jointly developed and reported through standing channels.", "essay": "liberty-security"},
                },
            },
            {
                "slug": "pause-recall",
                "title": "Public authority to pause or recall",
                "prompt": "Should the state retain authority to interrupt or restrict an AI deployment in extremis?",
                "positions": {
                    "leviathan": {"stance": "Yes, hedged", "summary": "On findings of fact, with judicial review and sunset provisions. Authority that does not sunset is no longer emergency authority.", "essay": "liberty-security"},
                    "prometheus": {"stance": "Reluctant", "summary": "Reserved for genuine emergencies under strong process; routine resort would chill the operational latitude that produces safety in practice.", "essay": "liberty-security"},
                    "demos": {"stance": "Distrusts", "summary": "An agency with interruption authority can weaponize AI against the public; the authority should be plural, distributed, and constitutionally constrained.", "essay": "liberty-security"},
                    "concord": {"stance": "Yes, internationalized", "summary": "Domestic authority hedged by international review where the deployment's effects cross borders; unilateral interruption is unstable.", "essay": "liberty-security"},
                },
            },
        ],
    },
    {
        "title": "Concentration and structure",
        "summary": "Instruments aimed at preventing dangerous accumulations of AI power.",
        "levers": [
            {
                "slug": "antitrust",
                "title": "Antitrust against AI concentration",
                "prompt": "Should the polity actively use antitrust to prevent AI concentration?",
                "positions": {
                    "leviathan": {"stance": "Aggressive", "summary": "Active antitrust including structural breakups, restrictions on compute holdings, and vertical separation by legislative mandate where lighter instruments fail.", "essay": "concentration"},
                    "prometheus": {"stance": "Light-touch", "summary": "Targeted antitrust at configurations most likely to foreclose plurality; lighter instruments preferred while plural frontier persists.", "essay": "concentration"},
                    "demos": {"stance": "Aggressive, structural", "summary": "Antitrust against vertical integration across the stack; structural separation as a precondition of meaningful competition at any layer.", "essay": "concentration"},
                    "concord": {"stance": "Coordinated", "summary": "Antitrust action coordinated across jurisdictions; transboundary concentrations require multilateral instruments domestic ones cannot reach.", "essay": "concentration"},
                },
            },
            {
                "slug": "structural-separation",
                "title": "Separation of model from channel",
                "prompt": "Should the firm developing a frontier model also control the principal channel through which it reaches users?",
                "positions": {
                    "leviathan": {"stance": "Opposes", "summary": "Legislative separation between model layer and channel layer; the antitrust instrument adapted to the structure of AI markets.", "essay": "concentration"},
                    "prometheus": {"stance": "Skeptical of mandate", "summary": "Industry-led interoperability standards reduce switching costs without legislative breakup; lighter touch, comparable effect on contestability.", "essay": "concentration"},
                    "demos": {"stance": "Central commitment", "summary": "Structural separation between developer and channel is the precondition of plurality at every layer of the stack.", "essay": "concentration"},
                    "concord": {"stance": "Coordinated", "summary": "Separation enforced consistently across major jurisdictions, to prevent firms from arbitraging through unbounded markets.", "essay": "concentration"},
                },
            },
            {
                "slug": "civic-compute",
                "title": "Civic and public compute",
                "prompt": "Should the polity build and fund non-commercial AI compute infrastructure at meaningful scale?",
                "positions": {
                    "leviathan": {"stance": "Supportive", "summary": "A useful complement to public regulation; secondary to the licensing and classification apparatus that does the principal work.", "essay": "concentration"},
                    "prometheus": {"stance": "Welcomes", "summary": "Useful for academic research and public-interest applications; not a substitute for the laboratories' work at the frontier.", "essay": "concentration"},
                    "demos": {"stance": "Central commitment", "summary": "Public, plural compute at meaningful scale is the substrate on which civic accountability depends; without it, oversight is rhetorical.", "essay": "concentration"},
                    "concord": {"stance": "International", "summary": "Coordinated public compute among allied jurisdictions, with shared governance, as a long-run institutional goal.", "essay": "concentration"},
                },
            },
        ],
    },
    {
        "title": "Work and displacement",
        "summary": "Instruments addressing the economic dislocations attendant on AI substitution.",
        "levers": [
            {
                "slug": "ai-rents-tax",
                "title": "Taxation of AI rents",
                "prompt": "Should extraordinary returns from frontier AI be taxed to fund displaced workers?",
                "positions": {
                    "leviathan": {"stance": "Central instrument", "summary": "Compute taxation, dedicated revenues from frontier deployment, and progressive taxation of AI-related capital gains, under public authority.", "essay": "job-displacement"},
                    "prometheus": {"stance": "Mixed", "summary": "Firm-funded transition financing as primary instrument; public taxation as backstop where firms cannot or will not internalize.", "essay": "job-displacement"},
                    "demos": {"stance": "Secondary", "summary": "Necessary but insufficient; addresses symptoms, not causes. The structural concentration of AI tools is the upstream lever.", "essay": "job-displacement"},
                    "concord": {"stance": "Coordinated", "summary": "Single-jurisdiction taxation invites arbitrage; coordinated international taxation regime is the durable form.", "essay": "job-displacement"},
                },
            },
            {
                "slug": "worker-tools",
                "title": "Worker access to AI tools",
                "prompt": "How should workers themselves come to wield AI capability, not merely face it deployed against them?",
                "positions": {
                    "leviathan": {"stance": "Indirect", "summary": "Through publicly funded retraining and education; access via citizenship-grade programs rather than direct provision of tools.", "essay": "job-displacement"},
                    "prometheus": {"stance": "Industry-led", "summary": "Through firm-led complementary deployment, internal apprenticeships, and industry-academic partnerships at scale.", "essay": "job-displacement"},
                    "demos": {"stance": "Structurally guaranteed", "summary": "Via open weights, civic compute, and worker rights of access to the systems their employers deploy.", "essay": "job-displacement"},
                    "concord": {"stance": "Internationally coordinated", "summary": "Through portable credentialing, multilateral skill standards, and coordinated infrastructure across jurisdictions.", "essay": "job-displacement"},
                },
            },
        ],
    },
    {
        "title": "International order",
        "summary": "Instruments aimed at the transboundary character of frontier AI.",
        "levers": [
            {
                "slug": "compute-observatory",
                "title": "Multilateral compute observatory",
                "prompt": "Should frontier compute be subject to international transparency, akin to nuclear safeguards?",
                "positions": {
                    "leviathan": {"stance": "Welcomes", "summary": "Useful instrument once domestic licensure exists to make legibility meaningful; the precondition is the domestic apparatus.", "essay": "liberty-security"},
                    "prometheus": {"stance": "Welcomes", "summary": "Valuable substrate for the firms' commitments; matures slower than the frontier, so cannot be the only instrument.", "essay": "liberty-security"},
                    "demos": {"stance": "Plural form only", "summary": "Acceptable in plural form with civic participation; centralized observatory is itself a concentration to be checked.", "essay": "concentration"},
                    "concord": {"stance": "Central pillar", "summary": "Multilateral observatory is the institutional foundation: legibility before agreement, agreement on legibility.", "essay": "liberty-security"},
                },
            },
            {
                "slug": "treaty-floor",
                "title": "Treaty floor on highest-risk capabilities",
                "prompt": "Should states formally commit to forgo the most catastrophic AI capabilities?",
                "positions": {
                    "leviathan": {"stance": "Welcomes, sequenced", "summary": "After domestic enforcement capacity exists; treaty without domestic backbone is a memorandum of intent.", "essay": "liberty-security"},
                    "prometheus": {"stance": "Welcomes, slow", "summary": "Necessary in the long run; cannot be the operative instrument on the timescale today's capabilities are maturing.", "essay": "liberty-security"},
                    "demos": {"stance": "Conditional", "summary": "Acceptable in plural form, narrowly drawn, with civic participation in setting the floor.", "essay": "concentration"},
                    "concord": {"stance": "Central pillar", "summary": "Historically attested instrument; imperfect treaty regimes outperform their absence in catastrophic-risk domains.", "essay": "liberty-security"},
                },
            },
        ],
    },
]

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
                cruxes=CRUXES.get(q["slug"], []),
            ),
            encoding="utf-8",
        )

    # Compare page
    (DIST / "compare").mkdir(exist_ok=True)
    (DIST / "compare" / "index.html").write_text(
        env.get_template("compare.html").render(
            **base_ctx,
            page="compare",
            comparison_groups=COMPARISON_GROUPS,
            questions_by_slug=QUESTIONS_BY_SLUG,
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
