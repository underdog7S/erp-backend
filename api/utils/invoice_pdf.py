"""One layout for every customer-facing bill (pharmacy, retail, restaurant, salon, hotel).

The business name, address, phone and GST number come from the tenant, amounts use the rupee sign, and
GST is shown as CGST + SGST when the bill carries tax.
"""
import os
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
_registered = False
INK = colors.HexColor('#1f2933')
MUTED = colors.HexColor('#5b6670')
LINE = colors.HexColor('#cfd6dd')
HEAD_BG = colors.HexColor('#eef1f4')


def register_fonts():
    """DejaVu Sans has the rupee sign; the built-in PDF fonts draw it as a black square."""
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont('Body', os.path.join(_FONT_DIR, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('Body-Bold', os.path.join(_FONT_DIR, 'DejaVuSans-Bold.ttf')))
        pdfmetrics.registerFontFamily('Body', normal='Body', bold='Body-Bold', italic='Body', boldItalic='Body-Bold')
        _registered = True


def money(value):
    return '₹{:,.2f}'.format(Decimal(str(value or 0)))


def _p(text, size=9, bold=False, color=INK, align=0, leading=None):
    style = ParagraphStyle('x', fontName='Body-Bold' if bold else 'Body', fontSize=size, textColor=color, alignment=align,
                           leading=leading or size + 3)
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)


def render_invoice(tenant, *, title, number, date_text, bill_to, meta, columns, rows, totals, gst=None, notes=None, footer=None):
    """Build the PDF and return its bytes.

    bill_to  list of lines for the customer block
    meta     list of (label, value) shown to the right of the customer block
    columns  [(heading, width_in_mm, align)] with align 'L' or 'R'
    rows     list of row lists (strings)
    totals   list of (label, amount_text, bold) shown under the table
    gst      optional dict {cgst, sgst, igst, rate_note}; printed as a tax summary
    """
    register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=f'{title} {number}', author=tenant.name)
    story = []

    # ---- header: business on the left, document title on the right
    biz = [_p(tenant.name, 16, True)]
    for line in filter(None, [getattr(tenant, 'address', ''), ('Phone: ' + tenant.phone) if getattr(tenant, 'phone', '') else '',
                              ('GSTIN: ' + tenant.gstin) if getattr(tenant, 'gstin', '') else '']):
        biz.append(_p(line, 8.5, color=MUTED))
    head = Table([[biz, [_p(title.upper(), 15, True, align=2), _p(f'No. {number}', 9.5, align=2), _p(date_text, 9, color=MUTED, align=2)]]],
                 colWidths=[105 * mm, 71 * mm])
    head.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, 0), 1, INK), ('BOTTOMPADDING', (0, 0), (-1, 0), 8)]))
    story += [head, Spacer(1, 6 * mm)]

    # ---- customer and details
    left = [_p('BILLED TO', 7.5, True, MUTED)] + [_p(l, 9.5) for l in bill_to if l]
    right = [_p('DETAILS', 7.5, True, MUTED)] + [_p(f'{k}: {v}', 9) for k, v in meta if v not in (None, '')]
    info = Table([[left, right]], colWidths=[88 * mm, 88 * mm])
    info.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    story += [info, Spacer(1, 6 * mm)]

    # ---- line items
    head_row = [_p(h, 8, True, align=2 if a == 'R' else 0) for h, _, a in columns]
    body = [[_p(cell, 8.8, align=2 if columns[i][2] == 'R' else 0) for i, cell in enumerate(r)] for r in rows]
    table = Table([head_row] + body, colWidths=[w * mm for _, w, _ in columns], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HEAD_BG), ('LINEBELOW', (0, 0), (-1, 0), 0.8, INK),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, LINE), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]))
    story += [table, Spacer(1, 4 * mm)]

    # ---- totals (right aligned) and GST summary
    tot_rows = [[_p(label, 9.5, bold), _p(amount, 9.5, bold, align=2)] for label, amount, bold in totals]
    tot = Table(tot_rows, colWidths=[36 * mm, 34 * mm], hAlign='RIGHT')
    tot.setStyle(TableStyle([('LINEABOVE', (0, -1), (-1, -1), 0.8, INK), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]))
    story.append(tot)
    if gst and (gst.get('cgst') or gst.get('sgst') or gst.get('igst')):
        story.append(Spacer(1, 4 * mm))
        parts = []
        if gst.get('igst'):
            parts.append(f"IGST {money(gst['igst'])}")
        else:
            parts += [f"CGST {money(gst.get('cgst'))}", f"SGST {money(gst.get('sgst'))}"]
        note = gst.get('rate_note', '')
        story.append(_p('GST summary: ' + '   '.join(parts) + (f'   ({note})' if note else ''), 8.5, color=MUTED))

    for n in (notes or []):
        story += [Spacer(1, 3 * mm), _p(n, 8.5, color=MUTED)]
    story += [Spacer(1, 10 * mm), _p(footer or 'Thank you for your business.', 9, align=1),
              _p('This is a computer generated document.', 7.5, color=MUTED, align=1)]
    doc.build(story)
    return buf.getvalue()
