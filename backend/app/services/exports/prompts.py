"""Prompt Targets export (Excel + PDF), grouped by intent bucket."""

from __future__ import annotations

import io

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Spacer

from app.services.exports.excel import _write_sheet
from app.services.exports.pdf import _H1, _H2, _p, _table


def build_prompts_excel(rows: list[dict], project_name: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Prompt Targets"
    _write_sheet(
        ws,
        ["Intent bucket", "Prompt", "Source"],
        [[r["intent_bucket"], r["text"], r["source"]] for r in rows],
        [22, 80, 14],
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_prompts_pdf(rows: list[dict], project_name: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm, title="Prompt Targets",
    )
    story = [_p(f"Prompt Targets — {project_name}", _H1), Spacer(1, 8)]
    by_bucket: dict[str, list[dict]] = {}
    for r in rows:
        by_bucket.setdefault(r["intent_bucket"], []).append(r)
    for bucket, items in by_bucket.items():
        story.append(_p(f"{bucket.title()} ({len(items)})", _H2))
        story.append(_table(["Prompt", "Source"], [[i["text"], i["source"]] for i in items],
                            [380, 80]))
        story.append(Spacer(1, 10))
    doc.build(story)
    return buf.getvalue()
