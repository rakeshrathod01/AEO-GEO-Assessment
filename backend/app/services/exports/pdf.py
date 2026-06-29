"""PDF export for a module analysis result.

Applies the platform PDF table rules: font size 11, wrap-text cells (via
Paragraph), no clipped columns, and an industry-benchmark **radar chart** with
the underlying data + cited sources.
"""

from __future__ import annotations

import io

from reportlab.graphics.charts.spider import SpiderChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0A1430")
RED = colors.HexColor("#E4002B")

_styles = getSampleStyleSheet()
_CELL = ParagraphStyle("cell", parent=_styles["Normal"], fontSize=11, leading=13)
_CELL_H = ParagraphStyle("cellH", parent=_CELL, textColor=colors.white, fontName="Helvetica-Bold")
_H1 = ParagraphStyle("h1", parent=_styles["Title"], textColor=NAVY)
_H2 = ParagraphStyle("h2", parent=_styles["Heading2"], textColor=NAVY)
_NOTE = ParagraphStyle("note", parent=_styles["Normal"], fontSize=8, textColor=colors.grey)


def _p(text, style=_CELL) -> Paragraph:
    return Paragraph("" if text is None else str(text), style)


def _rows(items: list[dict], keys: list[str]) -> list[list]:
    return [[it.get(k) for k in keys] for it in items]


def _table(headers: list[str], rows: list[list], widths: list[float]) -> Table:
    data = [[_p(h, _CELL_H) for h in headers]]
    data += [[_p(c) for c in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D1E0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5FA")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _radar(result: dict) -> Drawing | None:
    """Radar of client value vs benchmark for numeric (0..1) findings."""
    pts = []
    for f in result.get("findings", []):
        val, bench = f.get("value"), f.get("benchmark")
        if isinstance(val, int | float) and isinstance(bench, int | float):
            pts.append((f["signal"], min(float(val), 1.0), min(float(bench), 1.0)))
    pts = pts[:8]
    if len(pts) < 3:
        return None  # radar needs at least 3 axes

    d = Drawing(420, 240)
    chart = SpiderChart()
    chart.x, chart.y, chart.width, chart.height = 120, 20, 200, 200
    chart.data = [[p[1] for p in pts], [p[2] for p in pts]]
    chart.labels = [p[0].replace("_", " ") for p in pts]
    chart.strands[0].strokeColor = RED
    chart.strands[0].fillColor = colors.Color(0.894, 0, 0.168, 0.25)
    chart.strands[1].strokeColor = NAVY
    chart.strands[1].fillColor = None
    d.add(chart)
    d.add(String(10, 220, "Benchmark radar (client vs target)", fontSize=9, fillColor=NAVY))
    d.add(String(10, 205, "— client", fontSize=8, fillColor=RED))
    d.add(String(70, 205, "— benchmark", fontSize=8, fillColor=NAVY))
    return d


def build_pdf(result: dict, module_title: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title=f"{module_title} Report",
    )
    story = []

    story.append(_p(f"{module_title} — Assessment", _H1))
    story.append(
        _p(
            f"Scope: {result.get('scope')} &nbsp;|&nbsp; Score: <b>{result.get('score')}/100</b> "
            f"({result.get('status')}) &nbsp;|&nbsp; {result.get('target_url')}",
            _CELL,
        )
    )
    story.append(Spacer(1, 8))

    radar = _radar(result)
    if radar is not None:
        story.append(radar)
        story.append(Spacer(1, 6))

    story.append(_p("Findings", _H2))
    story.append(
        _table(
            ["Signal", "Status", "Value", "Benchmark", "Source"],
            _rows(result.get("findings", []), ["signal", "status", "value", "benchmark", "source"]),
            [110, 50, 55, 55, 150],
        )
    )
    story.append(Spacer(1, 10))

    story.append(_p("Recommendations", _H2))
    story.append(
        _table(
            ["Priority", "Action", "How To", "Effort", "Impact"],
            _rows(
                result.get("recommendations", []),
                ["priority", "action", "how_to", "effort", "impact"],
            ),
            [50, 120, 175, 40, 40],
        )
    )

    delta = result.get("competitor_delta", [])
    if delta:
        story.append(Spacer(1, 10))
        story.append(_p("Competitor delta", _H2))
        story.append(
            _table(
                ["Competitor", "Signal", "Us", "Them", "Gap"],
                _rows(delta, ["competitor", "signal", "us", "them", "gap"]),
                [120, 120, 60, 60, 60],
            )
        )

    sources = sorted({f.get("source") for f in result.get("findings", []) if f.get("source")})
    if sources:
        story.append(Spacer(1, 12))
        story.append(_p("Benchmark sources", _H2))
        for s in sources:
            story.append(_p(f"• {s}", _NOTE))

    doc.build(story)
    return buf.getvalue()


def _leadership_radar(report: dict) -> Drawing | None:
    """Radar of 0..1 readiness rates (client vs benchmark) across modules."""
    findings = []
    seen = set()
    for res in report.get("module_results", []):
        for f in res.get("findings", []):
            val, bench = f.get("value"), f.get("benchmark")
            if (
                isinstance(val, int | float) and isinstance(bench, int | float)
                and 0 <= val <= 1 and 0 < bench <= 1 and f["signal"] not in seen
            ):
                seen.add(f["signal"])
                findings.append(f)
    return _radar({"findings": findings[:8]}) if len(findings) >= 3 else None


def build_leadership_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title="Leadership Summary",
    )
    story = [_p("Leadership Summary — SEO / AEO / GEO", _H1)]
    ls = report.get("layer_scores", {})
    story.append(_p(
        f"Scope: {report.get('scope')} &nbsp;|&nbsp; Overall: "
        f"<b>{report.get('overall_score')}/100</b> ({report.get('status')}) &nbsp;|&nbsp; "
        f"SEO {ls.get('SEO')} · AEO {ls.get('AEO')} · GEO {ls.get('GEO')} &nbsp;|&nbsp; "
        f"{report.get('target_url')}", _CELL))
    story.append(Spacer(1, 6))
    story.append(_p(report.get("executive_summary", ""), _CELL))
    story.append(Spacer(1, 8))

    radar = _leadership_radar(report)
    if radar is not None:
        story.append(radar)
        story.append(Spacer(1, 6))

    story.append(_p("Module scores", _H2))
    story.append(_table(
        ["Module", "Layer", "Score", "Status"],
        _rows(report.get("modules", []), ["title", "layer", "score", "status"]),
        [180, 60, 60, 80],
    ))
    story.append(Spacer(1, 10))

    story.append(_p("Prioritized roadmap (foundational SEO → AEO → GEO)", _H2))
    story.append(_table(
        ["#", "Phase", "Priority", "Action", "How To"],
        [[i["order"], i["phase"], i["priority"], i["action"], i.get("how_to")]
         for i in report.get("roadmap", [])],
        [24, 50, 55, 150, 161],
    ))

    comp = report.get("competitor_summary", [])
    if comp:
        story.append(Spacer(1, 10))
        story.append(_p("Top competitor gaps", _H2))
        story.append(_table(
            ["Competitor", "Signal", "Us", "Them", "Gap"],
            _rows(comp, ["competitor", "signal", "us", "them", "gap"]),
            [120, 140, 50, 50, 50],
        ))

    benchmarks = report.get("benchmarks", [])
    if benchmarks:
        story.append(Spacer(1, 12))
        story.append(_p("Benchmark sources", _H2))
        for b in benchmarks:
            story.append(_p(f"• {b['metric']}: {b.get('source')}", _NOTE))

    doc.build(story)
    return buf.getvalue()
