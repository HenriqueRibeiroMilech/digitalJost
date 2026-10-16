"""Apresentação da lista de presença em PDF, sem acesso a Flask ou banco."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle


_LOGO = Path(__file__).resolve().parent / "assets" / "jost_logo.jpg"
_BLUE = colors.HexColor("#003B71")
_INK = colors.HexColor("#172B4D")
_MUTED = colors.HexColor("#52647B")


def _text(value):
    # Dados do evento/diretório são texto, nunca markup ou caminhos de recursos.
    value = str(value).strip() if value is not None else ""
    return escape(value or "Não informado").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _date(value):
    return value.strftime("%d/%m/%Y %H:%M") if value else "Não informado"


def build_attendance_pdf(event, attendance_list, entries, *, generated_at):
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=86, bottomMargin=42,
        title="Lista de presença", author="Digital JOST", pageCompression=1,
    )
    body = ParagraphStyle("AttendanceBody", fontName="Helvetica", fontSize=9, leading=13,
                          textColor=_INK, spaceAfter=6, splitLongWords=True)
    title = ParagraphStyle("AttendanceTitle", parent=body, fontName="Helvetica-Bold", fontSize=18, leading=23, spaceAfter=10)
    heading = ParagraphStyle("AttendanceHeading", parent=body, fontName="Helvetica-Bold", textColor=_BLUE,
                             spaceBefore=10, spaceAfter=6, keepWithNext=True)
    cell = ParagraphStyle("AttendanceCell", parent=body, fontSize=8.5, leading=11, spaceAfter=0)
    header_cell = ParagraphStyle("AttendanceHeaderCell", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    registration_cell = ParagraphStyle("AttendanceRegistration", parent=cell, fontName="Courier")
    logo = ImageReader(str(_LOGO))

    def decorate_page(canvas, doc):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(_BLUE)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(36, height - 40, "LISTA DE PRESENÇA")
        canvas.drawImage(logo, width - 141, height - 58, width=105, height=38,
                         preserveAspectRatio=True, anchor="ne", mask="auto")
        canvas.setStrokeColor(_BLUE)
        canvas.setLineWidth(1)
        canvas.line(36, height - 69, width - 36, height - 69)
        canvas.setFillColor(_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(36, 24, f"Digital JOST · Emitido em {_date(generated_at)}")
        canvas.drawRightString(width - 36, 24, f"Página {doc.page}")
        canvas.restoreState()

    story = [Paragraph(_text(event["name"]), title), Paragraph(f"<b>Lista:</b> {_text(attendance_list['name'])}", body)]
    for label, value in (
        ("Tipo de evento", event["event_type_name"]),
        ("Instrutor", event["instructor"]),
        ("Início", _date(event["starts_at"])),
        ("Fim", _date(event["ends_at"])),
    ):
        story.append(Paragraph(f"<b>{label}:</b> {_text(value)}", body))
    for label, field in (("Descrição", "description"), ("Conteúdo programático", "syllabus")):
        story.extend([Paragraph(label, heading), Paragraph(_text(event[field]), body)])
    story.extend([Spacer(1, 8), Paragraph(f"Participantes registrados: {len(entries)}", heading)])

    rows = [[Paragraph(label, header_cell) for label in ("Empresa", "Matrícula", "Nome", "Setor")]]
    for entry in entries:
        rows.append([
            Paragraph(_text(entry["company"]), cell),
            Paragraph(_text(entry["registration"][-8:]), registration_cell),
            Paragraph(_text(entry["name"]), cell),
            Paragraph(_text(entry["department"]), cell),
        ])
    if not entries:
        rows.append([Paragraph("Nenhuma presença registrada nesta lista.", cell), "", "", ""])
    # O Frame do SimpleDocTemplate reserva 6 pontos de padding em cada lado.
    width = document.width - 12
    table = LongTable(rows, colWidths=[width * ratio for ratio in (0.22, 0.14, 0.38, 0.26)],
                      repeatRows=1, hAlign="LEFT", splitByRow=1, splitInRow=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), _BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F9")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DCE3ED")),
    ]
    if not entries:
        commands.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(commands))
    story.append(table)
    document.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    output.seek(0)
    return output
