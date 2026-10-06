"""Exportación del formato preventivo concluido con identidad Vital Health."""

import base64
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


VERDE = colors.HexColor("#078F58")
VERDE_OSCURO = colors.HexColor("#075C3B")
VERDE_CLARO = colors.HexColor("#EAF7F0")
BORDE = colors.HexColor("#CFE2D8")


def _firma(valor):
    if not valor or "," not in valor:
        return Paragraph("Firma no disponible", ParagraphStyle("sin-firma", fontSize=7, textColor=colors.grey))
    try:
        contenido = base64.b64decode(valor.split(",", 1)[1])
        return Image(BytesIO(contenido), width=55 * mm, height=18 * mm)
    except (ValueError, TypeError):
        return Paragraph("Firma no disponible", ParagraphStyle("sin-firma-2", fontSize=7, textColor=colors.grey))


def crear_pdf_formato_mantenimiento(ejecucion, secciones, materiales, logo_path):
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=13*mm, leftMargin=13*mm,
                            topMargin=12*mm, bottomMargin=14*mm,
                            title=f"Mantenimiento {ejecucion['codigo']} - Semana {ejecucion['semana']}",
                            author="Vital Health")
    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo-mto", parent=styles["Title"], fontName="Helvetica-Bold",
                            fontSize=15, leading=18, textColor=VERDE_OSCURO, alignment=0)
    normal = ParagraphStyle("normal-mto", parent=styles["BodyText"], fontSize=7.4,
                            leading=9.2, textColor=colors.HexColor("#26382F"))
    pequeno = ParagraphStyle("small-mto", parent=normal, fontSize=6.6, leading=8)
    logo = Image(str(Path(logo_path)), width=29*mm, height=18*mm) if Path(logo_path).exists() else Paragraph("<b>VITAL HEALTH</b>", titulo)
    cabecera = Table([[logo, Paragraph(
        f"<b>Mantenimiento preventivo</b><br/><font size='9'>{escape(str(ejecucion['codigo']))} · {escape(str(ejecucion['equipo']))}</font>", titulo),
        Paragraph(f"<b>Semana {ejecucion['semana']} · {ejecucion['anio']}</b><br/>{escape(str(ejecucion['id_activo']))}<br/>{escape(str(ejecucion['departamento']))}", pequeno)]],
        colWidths=[35*mm, 103*mm, 43*mm])
    cabecera.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (-1,0), (-1,0), "RIGHT")]))
    def fecha_hora(valor):
        if not valor:
            return "-"
        if hasattr(valor, "hour") and valor.hour == 0 and valor.minute == 0:
            return f"{valor:%d/%m/%Y} · Hora no registrada"
        return f"{valor:%d/%m/%Y %H:%M}" if hasattr(valor, "hour") else str(valor)

    datos = [
        ["Fecha de realización", str(ejecucion.get("fecha_realizacion") or "-"), "Procedimiento", str(ejecucion.get("procedimiento") or "-")],
        ["Técnico", str(ejecucion.get("tecnico_nombre") or ejecucion.get("tecnico") or "-"), "Estado", "Completo y firmado"],
        ["Inicio", fecha_hora(ejecucion.get("iniciado_en")), "Finalización", fecha_hora(ejecucion.get("finalizado_en"))],
    ]
    resumen = Table([[Paragraph(f"<b>{escape(str(c))}</b>" if i % 2 == 0 else escape(str(c)), pequeno) for i,c in enumerate(row)] for row in datos], colWidths=[31*mm,59*mm,31*mm,60*mm])
    resumen.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), VERDE_CLARO), ("GRID", (0,0), (-1,-1), .45, BORDE), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("PADDING", (0,0), (-1,-1), 5)]))
    story = [cabecera, Spacer(1,4*mm), resumen, Spacer(1,5*mm)]
    respuestas = ejecucion.get("respuestas_json") or {}
    for nombre, actividades in secciones:
        filas = [[Paragraph(f"<b>{escape(nombre)}</b>", normal), "Resultado"]]
        for clave, texto in actividades:
            valor = respuestas.get(clave) or "Sin respuesta"
            etiqueta = {"REALIZADO":"Realizado", "CAMBIO":"C Cambio", "NO_APLICA":"N/A"}.get(valor, valor)
            filas.append([Paragraph(escape(texto), pequeno), Paragraph(f"<b>{escape(etiqueta)}</b>", pequeno)])
        tabla = Table(filas, colWidths=[145*mm,36*mm], repeatRows=1)
        tabla.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), VERDE), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, BORDE), ("VALIGN", (0,0), (-1,-1), "TOP"), ("PADDING", (0,0), (-1,-1), 4)]))
        story += [tabla, Spacer(1,3*mm)]
    usados = ejecucion.get("materiales_json") or []
    material_texto = ", ".join(usados) if usados else "Sin material registrado"
    extras = Table([[Paragraph("<b>Material utilizado</b>", normal), Paragraph(escape(material_texto), normal)],
                    [Paragraph("<b>Observaciones</b>", normal), Paragraph(escape(ejecucion.get("observaciones") or "Sin observaciones"), normal)]], colWidths=[38*mm,143*mm])
    extras.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .4, BORDE), ("BACKGROUND", (0,0), (0,-1), VERDE_CLARO), ("VALIGN", (0,0), (-1,-1), "TOP"), ("PADDING", (0,0), (-1,-1), 6)]))
    firmas = Table([[_firma(ejecucion.get("firma_tecnico")), _firma(ejecucion.get("firma_supervisor"))],
                    [Paragraph("<b>Responsable de mantenimiento</b>", pequeno), Paragraph("<b>Supervisor</b>", pequeno)]], colWidths=[90.5*mm,90.5*mm])
    firmas.setStyle(TableStyle([("ALIGN", (0,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "BOTTOM"), ("LINEABOVE", (0,1), (-1,1), .5, colors.HexColor("#607168")), ("TOPPADDING", (0,1), (-1,1), 4)]))
    story += [KeepTogether([extras, Spacer(1,6*mm), firmas])]
    def pie(canvas, document):
        canvas.saveState(); canvas.setFont("Helvetica", 7); canvas.setFillColor(colors.HexColor("#607168")); canvas.drawString(13*mm, 7*mm, "Vital Health · Sistema de mantenimiento preventivo"); canvas.drawRightString(197*mm, 7*mm, f"Página {document.page}"); canvas.restoreState()
    doc.build(story, onFirstPage=pie, onLaterPages=pie)
    output.seek(0)
    return output

