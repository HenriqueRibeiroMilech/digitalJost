"""Apresentação da lista de presença em Excel, sem acesso a Flask ou banco."""

from datetime import timezone
from io import BytesIO
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill


def _write_cell(sheet, row, column, value):
    if value is None:
        value = "Não informado"
    if isinstance(value, str):
        value = ILLEGAL_CHARACTERS_RE.sub("", value).strip() or "Não informado"
    cell = sheet.cell(row=row, column=column, value=value)
    if isinstance(value, str):
        # Campos do evento/diretório são texto literal, inclusive quando começam com '='.
        cell.data_type = "s"
    cell.alignment = Alignment(vertical="top", wrap_text=True)
    return cell


def build_attendance_excel(event, attendance_list, entries, *, generated_at):
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Evento"
    summary.append(["Campo", "Informação"])
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 100
    for row, (label, value) in enumerate((
        ("Evento", event["name"]),
        ("Lista", attendance_list["name"]),
        ("Tipo de evento", event["event_type_name"]),
        ("Instrutor", event["instructor"]),
        ("Início", event["starts_at"]),
        ("Fim", event["ends_at"]),
        ("Descrição", event["description"]),
        ("Conteúdo programático", event["syllabus"]),
        ("Participantes registrados", len(entries)),
        ("Emitido em", generated_at),
    ), start=2):
        _write_cell(summary, row, 1, label).font = Font(bold=True)
        cell = _write_cell(summary, row, 2, value)
        if label in ("Início", "Fim", "Emitido em"):
            cell.number_format = "dd/mm/yyyy hh:mm"
        if isinstance(cell.value, str):
            lines = sum(max(1, (len(line) + 89) // 90) for line in cell.value.split("\n"))
            summary.row_dimensions[row].height = min(409, max(30, lines * 15))

    participants = workbook.create_sheet("Participantes")
    participants.append(["Empresa", "Matrícula", "Nome", "Setor", "Leitura (Brasília)"])
    for column, width in (("A", 30), ("B", 16), ("C", 50), ("D", 35), ("E", 25)):
        participants.column_dimensions[column].width = width
    attendance_timezone = ZoneInfo("America/Sao_Paulo")
    for row, entry in enumerate(entries, start=2):
        for column, value in enumerate((
            entry["company"], entry["registration"][-8:], entry["name"], entry["department"],
        ), start=1):
            _write_cell(participants, row, column, value)
        # Matrícula permanece texto, preservando os oito dígitos e zeros iniciais.
        participants.cell(row=row, column=2).number_format = "@"
        recorded_at = entry["created_at"]
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        # Excel não suporta fuso; descarta frações para exibir os mesmos segundos da tela.
        recorded_at = recorded_at.astimezone(attendance_timezone).replace(tzinfo=None, microsecond=0)
        _write_cell(participants, row, 5, recorded_at).number_format = "dd/mm/yyyy hh:mm:ss"
    participants.auto_filter.ref = f"A1:E{participants.max_row}"

    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(fill_type="solid", fgColor="003B71")
        sheet.row_dimensions[1].height = 24

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
