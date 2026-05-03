"""
report_pdf.py — Beautiful PDF report generator for Deep Research results.
Uses a full canvas-based approach for precise layout control.
"""

import io
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, HRFlowable, PageBreak,
    ListFlowable, ListItem, KeepTogether,
)
from reportlab.pdfgen import canvas as pdfcanvas

# ─── Design Tokens ────────────────────────────────────────────────────────────
W, H = A4  # 595.27 x 841.89 pts

# Colors
C_BG_DARK    = colors.HexColor("#0D1117")   # page background dark
C_BG_CARD    = colors.HexColor("#161B22")   # card / section bg
C_ACCENT     = colors.HexColor("#2F81F7")   # primary blue
C_ACCENT2    = colors.HexColor("#A371F7")   # purple accent
C_ACCENT3    = colors.HexColor("#3FB950")   # green
C_BORDER     = colors.HexColor("#30363D")
C_TEXT       = colors.HexColor("#E6EDF3")   # main text
C_TEXT_MUTED = colors.HexColor("#8B949E")   # muted text
C_WHITE      = colors.white
C_GOLD       = colors.HexColor("#E3B341")

# Margins
ML = 1.8 * cm
MR = 1.8 * cm
MT = 2.8 * cm   # top (leaves room for header)
MB = 2.2 * cm   # bottom (leaves room for footer)

HEADER_H = 1.5 * cm
FOOTER_H = 1.0 * cm


# ─── Page Drawing ─────────────────────────────────────────────────────────────

class ReportCanvas(pdfcanvas.Canvas):
    """Custom canvas: draws dark background before content, header+footer after."""

    def __init__(self, *args, question="", **kwargs):
        super().__init__(*args, **kwargs)
        self._question = question
        self._saved_page_states = []
        # Paint background immediately so page 1 content renders on dark bg
        self._paint_background()

    def _paint_background(self):
        self.saveState()
        self.setFillColor(C_BG_DARK)
        self.rect(0, 0, W, H, fill=1, stroke=0)
        self.restoreState()

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
        # Paint dark background at start of each new page before content
        self._paint_background()

    def save(self):
        total = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            # Draw header+footer on top of already-rendered content
            self._draw_page(i + 1, total)
            super().showPage()
        super().save()

    def _draw_page(self, page_num: int, total_pages: int):
        self.saveState()

        # ── Header ───────────────────────────────────────────────────────────
        # Dark bar
        self.setFillColor(C_BG_CARD)
        self.rect(0, H - HEADER_H, W, HEADER_H, fill=1, stroke=0)
        # Blue accent line under header
        self.setFillColor(C_ACCENT)
        self.rect(0, H - HEADER_H - 2, W, 2, fill=1, stroke=0)
        # Left dot + brand
        self.setFillColor(C_ACCENT)
        self.circle(ML, H - HEADER_H / 2, 3, fill=1, stroke=0)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(C_TEXT)
        self.drawString(ML + 10, H - HEADER_H / 2 - 3.5, "AGENTIC AI  ·  DEEP RESEARCH REPORT")
        # Right: truncated question
        self.setFont("Helvetica", 7.5)
        self.setFillColor(C_TEXT_MUTED)
        q = self._question[:72] + "…" if len(self._question) > 72 else self._question
        self.drawRightString(W - ML, H - HEADER_H / 2 - 3.5, q)

        # ── Footer ───────────────────────────────────────────────────────────
        self.setFillColor(C_BG_CARD)
        self.rect(0, 0, W, FOOTER_H, fill=1, stroke=0)
        # Blue accent line above footer
        self.setFillColor(C_ACCENT)
        self.rect(0, FOOTER_H, W, 1.5, fill=1, stroke=0)
        # Date left
        self.setFont("Helvetica", 7)
        self.setFillColor(C_TEXT_MUTED)
        date_str = datetime.now().strftime("%d %B %Y · %H:%M")
        self.drawString(ML, FOOTER_H / 2 - 3, f"Generated · {date_str}")
        # Page number right
        self.drawRightString(W - ML, FOOTER_H / 2 - 3, f"Page {page_num} of {total_pages}")

        self.restoreState()


def _canvas_maker(question: str):
    def maker(*args, **kwargs):
        return ReportCanvas(*args, question=question, **kwargs)
    return maker


# ─── Styles ───────────────────────────────────────────────────────────────────

def _styles():
    S = {}

    S["h1"] = ParagraphStyle("h1",
        fontName="Helvetica-Bold", fontSize=17, leading=22,
        textColor=C_ACCENT, spaceBefore=20, spaceAfter=6,
        borderPad=0,
    )
    S["h2"] = ParagraphStyle("h2",
        fontName="Helvetica-Bold", fontSize=13, leading=17,
        textColor=C_ACCENT2, spaceBefore=14, spaceAfter=4,
    )
    S["h3"] = ParagraphStyle("h3",
        fontName="Helvetica-Bold", fontSize=11, leading=15,
        textColor=C_TEXT, spaceBefore=10, spaceAfter=3,
    )
    S["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=10, leading=16,
        textColor=C_TEXT, alignment=TA_JUSTIFY,
        spaceBefore=4, spaceAfter=4,
    )
    S["bullet_text"] = ParagraphStyle("bullet_text",
        fontName="Helvetica", fontSize=10, leading=15,
        textColor=C_TEXT, spaceBefore=2, spaceAfter=2,
        leftIndent=0,
    )
    S["source_url"] = ParagraphStyle("source_url",
        fontName="Helvetica", fontSize=8, leading=12,
        textColor=C_ACCENT, spaceBefore=1, spaceAfter=1,
        leftIndent=10,
    )
    S["label"] = ParagraphStyle("label",
        fontName="Helvetica-Bold", fontSize=7.5, leading=10,
        textColor=C_TEXT_MUTED, spaceBefore=14, spaceAfter=4,
        wordWrap=None,
    )
    S["chip"] = ParagraphStyle("chip",
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=C_TEXT_MUTED, spaceBefore=2, spaceAfter=2,
        leftIndent=8,
    )
    # Cover styles
    S["cover_eyebrow"] = ParagraphStyle("cover_eyebrow",
        fontName="Helvetica-Bold", fontSize=8, leading=10,
        textColor=C_ACCENT, alignment=TA_CENTER, spaceAfter=10,
        charSpace=2,
    )
    S["cover_title"] = ParagraphStyle("cover_title",
        fontName="Helvetica-Bold", fontSize=30, leading=36,
        textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=14,
    )
    S["cover_sub"] = ParagraphStyle("cover_sub",
        fontName="Helvetica", fontSize=12, leading=18,
        textColor=C_TEXT_MUTED, alignment=TA_CENTER, spaceAfter=6,
    )
    S["cover_meta"] = ParagraphStyle("cover_meta",
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=C_TEXT_MUTED, alignment=TA_CENTER, spaceAfter=3,
    )
    S["cover_stat"] = ParagraphStyle("cover_stat",
        fontName="Helvetica-Bold", fontSize=11, leading=15,
        textColor=C_ACCENT3, alignment=TA_CENTER, spaceAfter=3,
    )
    return S


# ─── Inline markdown → ReportLab XML ─────────────────────────────────────────

def _inline(text: str) -> str:
    """Convert **bold**, *italic* → reportlab XML. Escape stray < >."""
    # Escape bare ampersands first
    text = text.replace("&", "&amp;")
    # Escape < and > that aren't part of existing tags
    text = re.sub(r"<(?!/?(?:b|i|u|br|super|sub)\b)", "&lt;", text)
    text = re.sub(r"(?<!>)>(?!\s*<)", "&gt;", text)  # basic
    # Bold then italic
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text)
    return text


# ─── Markdown → Flowables ─────────────────────────────────────────────────────

def _parse_markdown(md: str, S: dict) -> list:
    story = []
    lines = md.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # blank
        if not line.strip():
            story.append(Spacer(1, 5))
            i += 1
            continue

        # H1: ##
        if line.startswith("## "):
            text = _inline(line[3:].strip())
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=1,
                                     color=C_BORDER, spaceAfter=4))
            story.append(Paragraph(text, S["h1"]))
            i += 1
            continue

        # H2: ###
        if line.startswith("### "):
            text = _inline(line[4:].strip())
            story.append(Paragraph(text, S["h2"]))
            i += 1
            continue

        # H3: ####
        if line.startswith("#### "):
            text = _inline(line[5:].strip())
            story.append(Paragraph(text, S["h3"]))
            i += 1
            continue

        # H1: #
        if line.startswith("# "):
            text = _inline(line[2:].strip())
            story.append(Paragraph(text, S["h1"]))
            i += 1
            continue

        # HR
        if line.strip() in ("---", "***", "___"):
            story.append(HRFlowable(width="100%", thickness=0.5,
                                     color=C_BORDER, spaceBefore=6, spaceAfter=6))
            i += 1
            continue

        # Bullet list — collect consecutive items
        if re.match(r"^[-*•]\s", line):
            items = []
            while i < len(lines) and re.match(r"^[-*•]\s", lines[i].rstrip()):
                text = _inline(lines[i].rstrip()[2:].strip())
                items.append(
                    ListItem(
                        Paragraph(text, S["bullet_text"]),
                        bulletColor=C_ACCENT,
                        leftIndent=14,
                        bulletOffsetY=-1,
                    )
                )
                i += 1
            story.append(
                ListFlowable(items,
                    bulletType="bullet",
                    bulletColor=C_ACCENT,
                    bulletFontSize=8,
                    leftIndent=10,
                    spaceBefore=4,
                    spaceAfter=4,
                )
            )
            continue

        # Numbered list
        if re.match(r"^\d+\.\s", line):
            items = []
            idx = 1
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].rstrip()):
                text = _inline(re.sub(r"^\d+\.\s", "", lines[i].rstrip()).strip())
                items.append(
                    ListItem(
                        Paragraph(text, S["bullet_text"]),
                        leftIndent=14,
                        value=idx,
                    )
                )
                i += 1
                idx += 1
            story.append(
                ListFlowable(items,
                    bulletType="1",
                    leftIndent=10,
                    spaceBefore=4,
                    spaceAfter=4,
                )
            )
            continue

        # Normal paragraph — accumulate lines until a blank or heading
        para_lines = []
        while i < len(lines):
            l = lines[i].rstrip()
            if not l.strip():
                break
            if re.match(r"^#{1,4}\s|^[-*•]\s|^\d+\.\s|^---$", l):
                break
            para_lines.append(_inline(l))
            i += 1

        text = " ".join(para_lines).strip()
        if text:
            story.append(Paragraph(text, S["body"]))

    return story


# ─── Cover Page (pure canvas) ─────────────────────────────────────────────────

def _draw_cover(c, question, queries, research_results, sources, date_str):
    c.saveState()

    # Full dark background
    c.setFillColor(C_BG_DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Top accent strip
    c.setFillColor(C_ACCENT)
    c.rect(0, H - 0.6 * cm, W, 0.6 * cm, fill=1, stroke=0)

    # Bottom accent strip
    c.setFillColor(C_ACCENT)
    c.rect(0, 0, W, 0.6 * cm, fill=1, stroke=0)

    # Diagonal decorative element (top-right corner)
    c.setFillColor(colors.HexColor("#1C2128"))
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0)

    # Large circle watermark (decorative, semi-transparent)
    c.setFillColor(colors.HexColor("#1C2128"))
    c.circle(W - 2 * cm, H - 5 * cm, 5 * cm, fill=1, stroke=0)
    c.setFillColor(C_BG_DARK)
    c.circle(W - 2 * cm, H - 5 * cm, 4.5 * cm, fill=1, stroke=0)

    # Eyebrow label
    eyebrow_y = H - 3.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_ACCENT)
    label = "DEEP RESEARCH REPORT"
    label_w = c.stringWidth(label, "Helvetica-Bold", 8)
    lx = (W - label_w) / 2
    c.drawString(lx, eyebrow_y, label)

    # Accent line under eyebrow
    c.setStrokeColor(C_ACCENT)
    c.setLineWidth(1)
    c.line(lx - 20, eyebrow_y - 4, lx + label_w + 20, eyebrow_y - 4)

    # Title
    title_y = eyebrow_y - 1.8 * cm
    # Word-wrap title manually for large font
    words = question.split()
    lines_out = []
    cur = ""
    max_w = W - 3.5 * cm
    for w in words:
        test = (cur + " " + w).strip()
        if c.stringWidth(test, "Helvetica-Bold", 26) <= max_w:
            cur = test
        else:
            lines_out.append(cur)
            cur = w
    if cur:
        lines_out.append(cur)
    lines_out = lines_out[:4]   # max 4 lines

    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(C_WHITE)
    for j, tl in enumerate(lines_out):
        tw = c.stringWidth(tl, "Helvetica-Bold", 26)
        c.drawString((W - tw) / 2, title_y - j * 32, tl)

    # Divider below title
    div_y = title_y - len(lines_out) * 32 - 16
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(0.8)
    c.line(ML, div_y, W - MR, div_y)

    # Meta info row
    meta_y = div_y - 0.7 * cm
    c.setFont("Helvetica", 9)
    c.setFillColor(C_TEXT_MUTED)
    c.drawCentredString(W / 2, meta_y, f"Generated on {date_str}  ·  Gemini + Tavily + Web Scraping")

    # Stats row
    stats_y = meta_y - 0.8 * cm
    total_pages = sum(len(r.get("scraped_pages", [])) for r in (research_results or []))
    stats = f"{len(queries)} sub-searches  ·  {total_pages} pages scraped  ·  {len(sources)} sources"
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(C_ACCENT3)
    sw = c.stringWidth(stats, "Helvetica-Bold", 10)
    c.drawString((W - sw) / 2, stats_y, stats)

    # Research angles section
    if queries:
        box_y = stats_y - 1.2 * cm
        box_h = min(len(queries), 6) * 0.65 * cm + 1.0 * cm
        box_x = ML

        # Card background
        c.setFillColor(C_BG_CARD)
        c.setStrokeColor(C_BORDER)
        c.setLineWidth(0.5)
        c.roundRect(box_x, box_y - box_h, W - ML - MR, box_h, 6, fill=1, stroke=1)

        # Left accent bar
        c.setFillColor(C_ACCENT2)
        c.rect(box_x, box_y - box_h, 3, box_h, fill=1, stroke=0)

        # Label
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(C_TEXT_MUTED)
        c.drawString(box_x + 12, box_y - 0.5 * cm, "RESEARCH ANGLES COVERED")

        # Queries list
        c.setFont("Helvetica", 9)
        c.setFillColor(C_TEXT)
        for qi, q in enumerate(queries[:6]):
            qy = box_y - 0.85 * cm - qi * 0.62 * cm
            # Bullet dot
            c.setFillColor(C_ACCENT)
            c.circle(box_x + 18, qy + 3, 2.5, fill=1, stroke=0)
            # Text (truncate if too long)
            q_display = q if len(q) <= 88 else q[:85] + "…"
            c.setFillColor(C_TEXT)
            c.drawString(box_x + 26, qy, q_display)

    c.restoreState()


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_pdf(
    question:         str,
    report_markdown:  str,
    research_queries: list,
    sources:          list,
    research_results: list = None,
) -> bytes:
    """Generate a polished PDF report. Returns raw bytes."""

    buf       = io.BytesIO()
    S         = _styles()
    date_str  = datetime.now().strftime("%d %B %Y")
    res_list  = research_results or []

    # ── Build story (everything after the cover) ──────────────────────────────
    story = _parse_markdown(report_markdown, S)
    story.append(Spacer(1, 1 * cm))

    # ── Doc setup ─────────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=ML,
        rightMargin=MR,
        topMargin=MT,
        bottomMargin=MB,
        title=f"Research Report: {question[:80]}",
        author="Agentic AI System",
    )

    frame = Frame(ML, MB, W - ML - MR, H - MT - MB, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    # ── Two-pass build: cover on page 1 via canvas callback ───────────────────
    cover_drawn = [False]

    def on_page(canvas_obj, doc_obj):
        if not cover_drawn[0]:
            # Page 1 = cover, drawn entirely by us; suppress the frame content
            # (PageBreak at start of story ensures page 2 is first real content)
            cover_drawn[0] = True

    # Use custom canvas for header/footer on all pages
    canvas_cls = _canvas_maker(question)

    doc.build(
        story,
        canvasmaker=canvas_cls,
    )

    # ── Now prepend the cover page ────────────────────────────────────────────
    # We generate the cover separately and merge it in front
    cover_buf = io.BytesIO()
    c = pdfcanvas.Canvas(cover_buf, pagesize=A4)
    _draw_cover(c, question, research_queries, res_list, sources, date_str)
    c.showPage()
    c.save()
    cover_buf.seek(0)

    # Merge cover + report using pypdf
    from pypdf import PdfWriter, PdfReader
    writer = PdfWriter()
    writer.append(PdfReader(cover_buf))
    buf.seek(0)
    writer.append(PdfReader(buf))

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()