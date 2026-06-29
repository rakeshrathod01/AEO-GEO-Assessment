"""AEO/GEO pitch deck generator (python-pptx).

Builds a 25-30 slide, client-ready deck from a LeadershipReport following a
storytelling arc: Context -> Current state -> Gaps vs competitors -> SEO/AEO/GEO
opportunity -> Roadmap -> eClerx value -> CTA.

Design rules:
  * eClerx navy/red brand on every slide.
  * Client logo fetched from the web (injectable; degrades gracefully).
  * Exactly one "Key Takeaway" callout per content slide.
  * Charts over walls of text — bullets are short and few.
"""

from __future__ import annotations

import io

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

NAVY = RGBColor(0x0A, 0x14, 0x30)
NAVY_LIGHT = RGBColor(0x1B, 0x30, 0x66)
RED = RGBColor(0xE4, 0x00, 0x2B)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SLATE = RGBColor(0x33, 0x3D, 0x52)
LIGHT = RGBColor(0xF2, 0xF5, 0xFA)

EMU_W, EMU_H = Inches(13.333), Inches(7.5)


def _default_fetch_logo(domain: str) -> bytes | None:
    import httpx

    for url in (
        f"https://logo.clearbit.com/{domain}",
        f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
    ):
        try:
            r = httpx.get(url, timeout=10, follow_redirects=True)
            if r.status_code == 200 and r.content and len(r.content) > 200:
                return r.content
        except Exception:  # noqa: BLE001
            continue
    return None


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width = EMU_W
        self.prs.slide_height = EMU_H
        self._blank = self.prs.slide_layouts[6]

    # --- low-level helpers ---------------------------------------------------
    def _slide(self, bg: RGBColor = WHITE):
        s = self.prs.slides.add_slide(self._blank)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = bg
        return s

    def _box(self, slide, x, y, w, h, fill=None, line=None):
        shp = slide.shapes.add_shape(1, x, y, w, h)  # 1 = rectangle
        shp.fill.solid() if fill else shp.fill.background()
        if fill:
            shp.fill.fore_color.rgb = fill
        if line:
            shp.line.color.rgb = line
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
        return shp

    def _text(self, slide, x, y, w, h, text, *, size=18, color=SLATE, bold=False,
              align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = "Calibri"
        return tb

    def _bullets(self, slide, x, y, w, h, items, *, size=16, color=SLATE):
        tb = slide.shapes.add_textbox(x, y, w, h)
        tf = tb.text_frame
        tf.word_wrap = True
        for i, item in enumerate(items):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.space_after = Pt(8)
            dot = p.add_run()
            dot.text = "▪ "
            dot.font.color.rgb = RED
            dot.font.size = Pt(size)
            run = p.add_run()
            run.text = item
            run.font.size = Pt(size)
            run.font.color.rgb = color
            run.font.name = "Calibri"
        return tb

    def _header(self, slide, title, eyebrow=None):
        self._box(slide, 0, 0, EMU_W, Inches(1.15), fill=NAVY)
        self._box(slide, Inches(0.6), Inches(1.02), Inches(1.4), Pt(4), fill=RED)
        if eyebrow:
            self._text(slide, Inches(0.6), Inches(0.18), Inches(11), Inches(0.3),
                       eyebrow.upper(), size=11, color=RED, bold=True)
        self._text(slide, Inches(0.6), Inches(0.42), Inches(12.1), Inches(0.6),
                   title, size=26, color=WHITE, bold=True)

    def _takeaway(self, slide, text):
        top = Inches(6.35)
        self._box(slide, 0, top, EMU_W, Inches(1.15), fill=LIGHT)
        self._box(slide, 0, top, Inches(0.12), Inches(1.15), fill=RED)
        self._text(slide, Inches(0.6), top + Inches(0.12), Inches(3), Inches(0.3),
                   "KEY TAKEAWAY", size=11, color=RED, bold=True)
        self._text(slide, Inches(0.6), top + Inches(0.40), Inches(12.1), Inches(0.7),
                   text, size=15, color=NAVY, bold=True)

    # --- slide types ---------------------------------------------------------
    def title_slide(self, client_name, subtitle, logo: bytes | None):
        s = self._slide(NAVY)
        self._box(s, 0, Inches(3.5), EMU_W, Pt(5), fill=RED)
        if logo:
            try:
                s.shapes.add_picture(io.BytesIO(logo), Inches(0.6), Inches(0.6),
                                     height=Inches(0.9))
            except Exception:  # noqa: BLE001 - unsupported image -> skip
                pass
        self._text(s, Inches(0.6), Inches(2.3), Inches(12), Inches(1.1),
                   f"{client_name}: SEO / AEO / GEO Assessment", size=40, color=WHITE, bold=True)
        self._text(s, Inches(0.6), Inches(3.7), Inches(12), Inches(0.6),
                   subtitle, size=18, color=RGBColor(0xC9, 0xD1, 0xE0))
        self._text(s, Inches(0.6), Inches(6.7), Inches(12), Inches(0.4),
                   "Prepared by eClerx", size=14, color=RED, bold=True)
        return s

    def section_divider(self, number, title):
        s = self._slide(NAVY)
        self._text(s, Inches(0.6), Inches(2.6), Inches(2), Inches(1.2),
                   number, size=72, color=RED, bold=True)
        self._text(s, Inches(0.6), Inches(3.9), Inches(12), Inches(1.0),
                   title, size=34, color=WHITE, bold=True)
        return s

    def content_slide(self, title, bullets, takeaway, eyebrow=None):
        s = self._slide(WHITE)
        self._header(s, title, eyebrow)
        self._bullets(s, Inches(0.6), Inches(1.5), Inches(12), Inches(4.5), bullets)
        self._takeaway(s, takeaway)
        return s

    def chart_slide(self, title, chart_type, categories, series, takeaway,
                    eyebrow=None, bullets=None):
        s = self._slide(WHITE)
        self._header(s, title, eyebrow)
        data = CategoryChartData()
        data.categories = categories
        for name, vals in series.items():
            data.add_series(name, vals)
        cw = Inches(7.5) if bullets else Inches(12.1)
        gf = s.shapes.add_chart(chart_type, Inches(0.6), Inches(1.5), cw, Inches(4.6), data)
        chart = gf.chart
        chart.has_title = False
        if len(series) > 1:
            chart.has_legend = True
            chart.legend.position = XL_LEGEND_POSITION.BOTTOM
            chart.legend.include_in_layout = False
        else:
            chart.has_legend = False
        # Brand the first two series.
        palette = [RED, NAVY_LIGHT]
        for i, plot_series in enumerate(chart.series):
            try:
                plot_series.format.fill.solid()
                plot_series.format.fill.fore_color.rgb = palette[i % len(palette)]
            except Exception:  # noqa: BLE001
                pass
        if bullets:
            self._bullets(s, Inches(8.4), Inches(1.6), Inches(4.3), Inches(4.4), bullets, size=14)
        self._takeaway(s, takeaway)
        return s

    def render(self) -> bytes:
        buf = io.BytesIO()
        self.prs.save(buf)
        return buf.getvalue()


# --- report helpers ----------------------------------------------------------
def _by_module(report: dict) -> dict[str, dict]:
    return {r.get("module"): r for r in report.get("module_results", [])}


def _findings(res: dict | None, signal_prefix: str = "") -> list[dict]:
    if not res:
        return []
    return [f for f in res.get("findings", []) if f["signal"].startswith(signal_prefix)]


def _top_recs(res: dict | None, n=3) -> list[str]:
    if not res:
        return []
    return [r["action"] for r in res.get("recommendations", [])[:n]]


def _pct(v) -> str:
    try:
        return f"{round(float(v) * 100)}%" if 0 <= float(v) <= 1 else str(v)
    except (TypeError, ValueError):
        return str(v)


def _module_snapshot(deck: Deck, report: dict, key: str, title: str):
    res = _by_module(report).get(key)
    score = res.get("score") if res else None
    bullets = _top_recs(res, 3) or ["Healthy — no critical issues detected."]
    status = (res or {}).get("status", "n/a")
    takeaway = (
        f"{title} scores {score}/100 ({status}). "
        + (f"Priority fix: {bullets[0]}" if bullets else "On track.")
    )
    deck.content_slide(title, bullets, takeaway, eyebrow="Current state")


# --- main builder ------------------------------------------------------------
def build_pitch_deck(report: dict, project: dict, fetch_logo=None) -> bytes:
    client = project.get("name") or "Client"
    domain = project.get("domain") or ""
    fetch = fetch_logo if fetch_logo is not None else _default_fetch_logo
    logo = None
    if domain and fetch:
        try:
            logo = fetch(domain)
        except Exception:  # noqa: BLE001
            logo = None

    deck = Deck()
    by_mod = _by_module(report)
    ls = report.get("layer_scores", {})
    overall = report.get("overall_score", 0)
    scope = report.get("scope", "site")

    # 1. Title
    deck.title_slide(client, f"AI-era search readiness — {scope} scope", logo)

    # 2. Executive summary
    deck.content_slide(
        "Executive summary",
        [report.get("executive_summary", "")[:400] or "Assessment summary."],
        f"Overall readiness: {overall}/100. The roadmap sequences foundational SEO, "
        f"then AEO, then GEO.",
        eyebrow="Overview",
    )

    # 3. Section: Context
    deck.section_divider("01", "Context: search is becoming answer & generative")
    deck.content_slide(
        "The shift from links to answers",
        ["SEO wins the classic ranked list of links.",
         "AEO wins answer surfaces — AI Overviews, PAA, voice, knowledge panels.",
         "GEO wins citations inside AI assistants (ChatGPT, Gemini, Claude, Perplexity)."],
        "Visibility now spans three layers — winning requires SEO, AEO and GEO together.",
        eyebrow="Context",
    )
    deck.content_slide(
        "How we assessed",
        ["Crawled the top business-critical pages + matched competitor pages.",
         "Scored 8 modules against cited industry benchmarks.",
         "Queried live AI assistants + captured SERP AI Overviews for GEO."],
        "Every score is benchmarked and sourced — defensible, not opinion.",
        eyebrow="Method",
    )

    # 4. Section: Current state
    deck.section_divider("02", "Current state")
    deck.chart_slide(
        "Readiness scorecard", XL_CHART_TYPE.COLUMN_CLUSTERED,
        ["Overall", "SEO", "AEO", "GEO"],
        {"Score": [overall, ls.get("SEO") or 0, ls.get("AEO") or 0, ls.get("GEO") or 0]},
        f"SEO {ls.get('SEO')}, AEO {ls.get('AEO')}, GEO {ls.get('GEO')} — "
        f"foundational layers lead, generative trails.",
        eyebrow="Current state",
    )
    mods = report.get("modules", [])
    if mods:
        deck.chart_slide(
            "Module scorecard", XL_CHART_TYPE.BAR_CLUSTERED,
            [m["title"] for m in mods], {"Score": [m["score"] for m in mods]},
            "Lowest-scoring modules anchor the roadmap's first moves.",
            eyebrow="Current state",
        )

    # Per-module snapshots (5 SEO + AEO + GEO).
    for key, title in [
        ("technical_seo", "Technical SEO"), ("on_page", "On-Page SEO"),
        ("internal_linking", "Internal Linking"), ("backlinks", "Backlinks"),
        ("keyword_universe", "Keyword Universe"), ("aeo_audit", "AEO readiness"),
        ("geo_audit", "GEO visibility"),
    ]:
        if key in by_mod:
            _module_snapshot(deck, report, key, title)

    # 5. Section: Gaps vs competitors
    deck.section_divider("03", "Gaps vs competitors")
    comp = report.get("competitor_summary", [])
    if comp:
        top = comp[:6]
        deck.chart_slide(
            "Where competitors lead", XL_CHART_TYPE.BAR_CLUSTERED,
            [f"{d['competitor']}: {d['signal']}"[:28] for d in top],
            {"Us": [_num(d["us"]) for d in top], "Them": [_num(d["them"]) for d in top]},
            "Closing these specific gaps is the fastest route to parity.",
            eyebrow="Competitive",
        )
    else:
        deck.content_slide(
            "Competitive position",
            ["Competitor comparison runs on comparable pages per module."],
            "Competitor deltas pinpoint exactly where to focus.", eyebrow="Competitive")

    # 6. Section: Opportunity (SEO/AEO/GEO)
    deck.section_divider("04", "The SEO / AEO / GEO opportunity")
    _opportunity_slide(deck, by_mod, "SEO opportunity",
                       ["technical_seo", "on_page", "internal_linking", "backlinks",
                        "keyword_universe"], "Foundational SEO")
    _opportunity_slide(deck, by_mod, "AEO opportunity", ["aeo_audit"], "Answer engines")
    _opportunity_slide(deck, by_mod, "GEO opportunity", ["geo_audit"], "Generative engines")

    # AEO + GEO charts.
    aeo = by_mod.get("aeo_audit")
    if aeo:
        af = [f for f in aeo.get("findings", []) if isinstance(f.get("value"), int | float)][:6]
        if af:
            deck.chart_slide(
                "AEO readiness by surface", XL_CHART_TYPE.BAR_CLUSTERED,
                [f["signal"].replace("_readiness", "").replace("_", " ")[:22] for f in af],
                {"Readiness": [round(float(f["value"]) * 100) for f in af]},
                "Concise answers + schema unlock AI Overviews, PAA and voice.",
                eyebrow="AEO")
    geo = by_mod.get("geo_audit")
    if geo:
        gf = [f for f in geo.get("findings", []) if f["signal"].endswith("_citation_rate")][:6]
        if gf:
            deck.chart_slide(
                "GEO citation rate by assistant", XL_CHART_TYPE.COLUMN_CLUSTERED,
                [f["signal"].replace("_citation_rate", "") for f in gf],
                {"Citation rate %": [round(float(f["value"]) * 100) for f in gf]},
                "Citable, well-structured content lifts share across assistants.",
                eyebrow="GEO")

    # 7. Section: Roadmap
    deck.section_divider("05", "The roadmap")
    roadmap = report.get("roadmap", [])
    deck.content_slide(
        "Sequenced for compounding impact",
        ["Phase 1 — Foundational SEO: fix crawl/index, on-page, links.",
         "Phase 2 — AEO: structure answers + schema for answer surfaces.",
         "Phase 3 — GEO: earn citations across AI assistants."],
        "Foundations first: SEO fixes make AEO and GEO gains durable.",
        eyebrow="Roadmap",
    )
    for phase, label in [("SEO", "Phase 1 — Foundational SEO"),
                         ("AEO", "Phase 2 — AEO"), ("GEO", "Phase 3 — GEO")]:
        items = [i for i in roadmap if i.get("phase") == phase][:5]
        bullets = [f"[{i['priority'].upper()}] {i['action']}" for i in items] or [
            "No critical actions — maintain and monitor."]
        deck.content_slide(
            label, bullets,
            f"{label.split('—')[1].strip()}: {len(items)} prioritized moves, "
            "highest-impact first.", eyebrow="Roadmap")

    # 8. Section: eClerx value + CTA
    deck.section_divider("06", "Why eClerx")
    deck.content_slide(
        "Why eClerx",
        ["20+ years delivering measurable digital outcomes for enterprise brands.",
         "One team across SEO, AEO and GEO — execution, not just audit.",
         "Benchmarked, sourced, board-ready reporting."],
        "eClerx turns this assessment into shipped, measurable gains.",
        eyebrow="Value",
    )
    deck.content_slide(
        "Engagement model",
        ["Sprint 0: foundational SEO fixes + instrumentation.",
         "Sprints 1-3: AEO content + schema rollout.",
         "Ongoing: GEO monitoring across assistants + iteration."],
        "A staged engagement de-risks delivery and shows early wins.",
        eyebrow="Value",
    )
    s = deck._slide(NAVY)
    deck._box(s, 0, Inches(3.4), EMU_W, Pt(5), fill=RED)
    deck._text(s, Inches(0.6), Inches(2.4), Inches(12), Inches(1.0),
               "Let's win the AI-era search race together.", size=34, color=WHITE, bold=True)
    deck._text(s, Inches(0.6), Inches(3.7), Inches(12), Inches(0.6),
               "Next step: a working session to lock Phase 1 scope.", size=18,
               color=RGBColor(0xC9, 0xD1, 0xE0))
    deck._text(s, Inches(0.6), Inches(6.6), Inches(12), Inches(0.5),
               "eClerx · digital@eclerx.com", size=14, color=RED, bold=True)

    return deck.render()


def _num(v) -> float:
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return 0.0


def _opportunity_slide(deck: Deck, by_mod: dict, title: str, keys: list[str], eyebrow: str):
    recs: list[str] = []
    for k in keys:
        recs.extend(_top_recs(by_mod.get(k), 2))
    recs = recs[:4] or ["Maintain current strengths and monitor."]
    deck.content_slide(
        title, recs,
        f"{title}: focus on the highest-impact, lowest-effort moves first.",
        eyebrow=eyebrow,
    )
