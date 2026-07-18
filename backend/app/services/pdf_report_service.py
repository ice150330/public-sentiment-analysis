"""PDF report generation for sentiment analytics."""

from __future__ import annotations

import io
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "PSAChinese"


def _register_font() -> str:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return FONT_NAME

    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    ]
    for font_path in candidates:
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
                return FONT_NAME
            except Exception:
                continue

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PSATitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=10,
        ),
        "heading": ParagraphStyle(
            "PSAHeading",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "PSABody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9,
            leading=14,
            textColor=colors.HexColor("#334155"),
        ),
        "small": ParagraphStyle(
            "PSASmall",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        ),
        "table": ParagraphStyle(
            "PSATable",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#334155"),
        ),
    }


def _p(value: Any, style: ParagraphStyle) -> Any:
    text = "" if value is None else str(value)
    if "\n" not in text and len(text) <= 18:
        return text
    return Paragraph(escape(text), style)


def _format_percent(value: float | None) -> str:
    return f"{(value or 0) * 100:.1f}%"


def _sentiment_name(label: str | None) -> str:
    return {
        "positive": "正面",
        "negative": "负面",
        "neutral": "中性",
    }.get(label or "", label or "未知")


def _distribution_chart(distribution: list[dict[str, Any]], font_name: str) -> Drawing:
    drawing = Drawing(480, 180)
    if not distribution:
        drawing.add(String(205, 82, "暂无情感数据", fontName=font_name, fontSize=12, fillColor=colors.HexColor("#64748b")))
        return drawing

    labels = [_sentiment_name(item.get("label")) for item in distribution]
    values = [int(item.get("count") or 0) for item in distribution]
    max_value = max(values) if values else 1

    chart = VerticalBarChart()
    chart.x = 42
    chart.y = 34
    chart.height = 112
    chart.width = 388
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontName = font_name
    chart.categoryAxis.labels.fontSize = 8
    chart.valueAxis.labels.fontName = font_name
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(1, int(max_value * 1.25) + 1)
    chart.valueAxis.valueStep = max(1, int(chart.valueAxis.valueMax / 4))
    chart.bars[0].fillColor = colors.HexColor("#2563eb")
    chart.barSpacing = 6
    drawing.add(chart)
    drawing.add(String(42, 156, "情感分布", fontName=font_name, fontSize=10, fillColor=colors.HexColor("#1f2937")))
    return drawing


def _summary_table(summary: dict[str, Any], style: ParagraphStyle, font_name: str) -> Table:
    cards = [
        ("样本总数", summary.get("total", 0)),
        ("平均置信度", _format_percent(summary.get("avg_confidence", 0))),
        ("负面占比", _format_percent(summary.get("negative_ratio", 0))),
        ("低置信样本", summary.get("low_confidence", 0)),
    ]
    table = Table(
        [[_p(label, style) for label, _ in cards], [_p(value, style) for _, value in cards]],
        colWidths=[42 * mm] * 4,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _data_table(
    headers: list[str],
    rows: list[list[Any]],
    style: ParagraphStyle,
    widths: list[float],
    font_name: str,
) -> Table:
    data = [[_p(header, style) for header in headers]]
    data.extend([[_p(value, style) for value in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dbe3ef")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_sentiment_report_pdf(report: dict[str, Any]) -> bytes:
    """Build a sentiment analytics PDF and return its bytes."""
    font_name = _register_font()
    styles = _styles(font_name)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
        title="公众情绪情感分析报告",
        author="PublicSentimentAnalysis",
    )

    filters = report.get("filters", {})
    generated_at = report.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    filter_line = " | ".join(
        [
            f"平台: {filters.get('platform') or '全部'}",
            f"开始: {filters.get('start_time') or '不限'}",
            f"结束: {filters.get('end_time') or '不限'}",
        ]
    )

    story = [
        Paragraph("公众情绪情感分析报告", styles["title"]),
        Paragraph(f"生成时间: {generated_at}", styles["small"]),
        Paragraph(filter_line, styles["small"]),
        Spacer(1, 8),
        _summary_table(report.get("summary", {}), styles["table"], font_name),
        Spacer(1, 10),
        Paragraph("情感分布图", styles["heading"]),
        _distribution_chart(report.get("distribution", []), font_name),
        Paragraph("平台分布", styles["heading"]),
        _data_table(
            ["平台", "样本数", "平均置信度", "负面样本"],
            report.get("platform_rows", []),
            styles["table"],
            [46 * mm, 30 * mm, 40 * mm, 30 * mm],
            font_name,
        ),
        Paragraph("高热度样本", styles["heading"]),
        _data_table(
            ["话题", "平台", "情感", "置信度", "热度"],
            report.get("topic_rows", []),
            styles["table"],
            [70 * mm, 26 * mm, 24 * mm, 28 * mm, 24 * mm],
            font_name,
        ),
    ]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.drawString(16 * mm, 8 * mm, "PublicSentimentAnalysis")
        canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
