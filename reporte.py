"""Genera un reporte de contactos a partir del JSON exportado."""

import json
from datetime import datetime
from xml.sax.saxutils import escape

from agenda import destino_atomico


def generar_pdf(ruta_json, destino):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    contactos = json.loads(ruta_json.read_text(encoding="utf-8"))
    estilos = getSampleStyleSheet()
    estilos["Title"].textColor = colors.HexColor("#182848")
    estilos["Title"].alignment = 0
    celda = ParagraphStyle("Celda", fontName="Helvetica", fontSize=9, leading=12)
    cabecera = ParagraphStyle(
        "Cabecera", parent=celda, fontName="Helvetica-Bold", textColor=colors.white
    )
    filas = [[Paragraph(campo, cabecera) for campo in ("ID", "Nombre", "Teléfono", "Correo", "Ciudad")]]
    hay_escapes = False
    for contacto in contactos:
        fila = []
        for campo in ("id", "nombre", "telefono", "correo", "ciudad"):
            texto = str(contacto[campo])
            imprimible = texto.encode("cp1252", errors="backslashreplace").decode("cp1252")
            hay_escapes |= imprimible != texto
            fila.append(Paragraph(escape(imprimible), celda))
        filas.append(fila)

    fecha = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    contenido = [
        Paragraph("Agenda de contactos", estilos["Title"]),
        Paragraph(f"Generado el {fecha} · {len(contactos)} contactos", estilos["Normal"]),
        Spacer(1, 18),
    ]
    if contactos:
        tabla = LongTable(filas, colWidths=[54, 113, 73, 157, 119], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#253B64")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF3F9")]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#CBD6E5")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        contenido.append(tabla)
    else:
        contenido.append(Paragraph("La agenda está vacía.", estilos["Normal"]))
    if hay_escapes:
        contenido += [
            Spacer(1, 10),
            Paragraph("Los caracteres fuera de la fuente se muestran mediante su código Unicode.",
                      estilos["Normal"]),
        ]

    def pie(canvas, documento):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#526481"))
        canvas.drawString(48, 30, "Laboratorio 2  /  Agenda de contactos")
        canvas.drawRightString(564, 30, str(documento.page))

    with destino_atomico(destino) as temporal:
        documento = SimpleDocTemplate(
            str(temporal), pagesize=letter, leftMargin=42, rightMargin=42,
            topMargin=44, bottomMargin=54, title="Agenda de contactos"
        )
        documento.build(contenido, onFirstPage=pie, onLaterPages=pie)
