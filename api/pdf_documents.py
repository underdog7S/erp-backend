"""Builds the customer bills from saved records. Every figure comes from what was stored when the sale was made."""
from decimal import Decimal
from math import ceil

from api.utils.invoice_pdf import money, render_invoice

ZERO = Decimal('0')


def _dt(value, fmt='%d %b %Y, %I:%M %p'):
    from django.utils import timezone
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime(fmt)


def _rate(rate):
    rate = Decimal(str(rate or 0))
    return f'{rate.normalize():f}%' if rate else '-'


def _gst(obj, note=''):
    return {'cgst': getattr(obj, 'cgst_amount', ZERO), 'sgst': getattr(obj, 'sgst_amount', ZERO), 'rate_note': note}


def _customer_lines(customer):
    if not customer:
        return ['Walk-in customer']
    return [customer.name, ('Phone: ' + customer.phone) if customer.phone and customer.phone != '-' else '',
            getattr(customer, 'address', '') or '']


def pharmacy_invoice(sale):
    rows, has_hsn = [], False
    for i, it in enumerate(sale.items.select_related('medicine_batch__medicine'), 1):
        batch = it.medicine_batch
        med = batch.medicine
        name = med.name + (f' {med.strength}' if med.strength else '')
        has_hsn = has_hsn or bool(it.hsn_code)
        rows.append([str(i), f'{name}\nBatch {batch.batch_number}, exp {batch.expiry_date:%b %Y}', it.hsn_code or '-', str(it.quantity),
                     money(it.unit_price), _rate(it.gst_rate), money(it.total_price)])
    columns = [('#', 8, 'L'), ('Medicine', 62, 'L'), ('HSN', 16, 'L'), ('Qty', 12, 'R'), ('MRP / rate', 26, 'R'), ('GST', 14, 'R'), ('Amount', 26, 'R')]
    inclusive = sale.tax_amount and sale.subtotal == sale.total_amount
    totals = [('Subtotal', money(sale.subtotal), False)]
    if sale.tax_amount:
        totals.append(('GST ' + ('(included)' if inclusive else ''), money(sale.tax_amount), False))
    if sale.discount_amount:
        totals.append(('Discount', '-' + money(sale.discount_amount), False))
    totals.append(('Total', money(sale.total_amount), True))
    return render_invoice(
        sale.tenant, title='Tax invoice' if sale.tax_amount else 'Invoice', number=sale.invoice_number, date_text=_dt(sale.sale_date),
        bill_to=_customer_lines(sale.customer),
        meta=[('Payment', f'{sale.payment_method.title()} ({sale.payment_status.title()})'),
              ('Prescription', f'Dr {sale.prescription.doctor_name}' if sale.prescription_id else ''),
              ('Served by', (sale.sold_by.user.get_full_name() or sale.sold_by.user.username) if sale.sold_by_id else '')],
        columns=columns, rows=rows, totals=totals, gst=_gst(sale, 'prices include GST' if inclusive else ''),
        notes=['Medicines once sold cannot be returned unless unopened and within the return period. Keep this bill for any exchange.'],
        footer='Get well soon.')


def retail_invoice(sale):
    rows = []
    for i, it in enumerate(sale.items.select_related('product'), 1):
        rows.append([str(i), it.product.name + (f'\nSKU {it.product.sku}' if it.product.sku else ''), it.hsn_code or '-', str(it.quantity),
                     money(it.unit_price), _rate(it.gst_rate), money(it.total_price)])
    columns = [('#', 8, 'L'), ('Item', 62, 'L'), ('HSN', 16, 'L'), ('Qty', 12, 'R'), ('Rate', 26, 'R'), ('GST', 14, 'R'), ('Amount', 26, 'R')]
    inclusive = sale.tax_amount and sale.subtotal == sale.total_amount
    totals = [('Subtotal', money(sale.subtotal), False)]
    if sale.tax_amount:
        totals.append(('GST ' + ('(included)' if inclusive else ''), money(sale.tax_amount), False))
    if sale.discount_amount:
        totals.append(('Discount', '-' + money(sale.discount_amount), False))
    totals.append(('Total', money(sale.total_amount), True))
    return render_invoice(
        sale.tenant, title='Tax invoice' if sale.tax_amount else 'Invoice', number=sale.invoice_number, date_text=_dt(sale.sale_date),
        bill_to=_customer_lines(sale.customer),
        meta=[('Payment', f'{sale.payment_method.title()} ({sale.payment_status.title()})'), ('Store', sale.warehouse.name if sale.warehouse_id else ''),
              ('Served by', (sale.sold_by.user.get_full_name() or sale.sold_by.user.username) if sale.sold_by_id else '')],
        columns=columns, rows=rows, totals=totals, gst=_gst(sale, 'prices include GST' if inclusive else ''), footer='Thank you for shopping with us.')


def restaurant_bill(order):
    rows = []
    for i, it in enumerate(order.items.select_related('menu_item'), 1):
        rows.append([str(i), it.menu_item.name, str(it.quantity), money(it.price), _rate(it.gst_rate), money(it.line_total())])
    columns = [('#', 8, 'L'), ('Item', 76, 'L'), ('Qty', 14, 'R'), ('Price', 26, 'R'), ('GST', 16, 'R'), ('Amount', 26, 'R')]
    items_total = sum((i.line_total() for i in order.items.all()), ZERO)
    totals = [('Items total', money(items_total), False)]
    if order.tax_amount:
        added = order.total_amount - items_total
        totals.append(('GST' + (' (added)' if added > 0 else ' (included)'), money(order.tax_amount), False))
    totals.append(('Total', money(order.total_amount), True))
    where = f'Table {order.table.number}' if order.table_id else order.get_order_type_display()
    return render_invoice(
        order.tenant, title='Bill', number=f'RST-{order.id:06d}', date_text=_dt(order.created_at),
        bill_to=[order.customer_name or 'Guest', ('Phone: ' + order.customer_phone) if order.customer_phone else '', order.delivery_address or ''],
        meta=[('Order', where), ('Status', order.get_status_display())],
        columns=columns, rows=rows, totals=totals, gst=_gst(order),
        notes=[f'Note: {order.notes}'] if order.notes else None, footer='Thank you for dining with us.')


def salon_bill(appt):
    duration = int((appt.end_time - appt.start_time).total_seconds() // 60) if appt.end_time and appt.start_time else 0
    rows = [['1', f'{appt.service.name}\nwith {appt.stylist}' + (f' ({duration} min)' if duration else ''), money(appt.price), _rate(appt.gst_rate), money(appt.price)]]
    columns = [('#', 8, 'L'), ('Service', 88, 'L'), ('Price', 28, 'R'), ('GST', 18, 'R'), ('Amount', 28, 'R')]
    total = appt.total_amount or appt.price
    added = total - appt.price
    totals = [('Service charge', money(appt.price), False)]
    if appt.tax_amount:
        totals.append(('GST' + (' (added)' if added > 0 else ' (included)'), money(appt.tax_amount), False))
    totals.append(('Total', money(total), True))
    return render_invoice(
        appt.tenant, title='Invoice', number=f'SAL-{appt.id:06d}', date_text=_dt(appt.start_time),
        bill_to=[appt.customer_name, ('Phone: ' + appt.customer_phone) if appt.customer_phone else ''],
        meta=[('Appointment', _dt(appt.start_time)), ('Status', appt.get_status_display()),
              ('Payment', f'{(appt.payment_method or "").title()} ({(appt.payment_status or "").title()})' if appt.payment_status else '')],
        columns=columns, rows=rows, totals=totals, gst=_gst(appt), footer='Thank you for visiting us.')


def hotel_folio(booking):
    from hotel.models import RoomServiceOrder
    rt = booking.room.room_type
    nights = max(1, ceil((booking.check_out - booking.check_in).total_seconds() / 86400))
    room_charge = rt.base_rate * nights
    rows = [['1', f'Room {booking.room.room_number} ({rt.name})\n{nights} night(s) at {money(rt.base_rate)}', _rate(booking.gst_rate), money(room_charge)]]
    extras = ZERO
    for o in RoomServiceOrder.objects.filter(tenant=booking.tenant, room=booking.room, ordered_at__gte=booking.check_in, ordered_at__lte=booking.check_out):
        line = ', '.join(f"{i.get('quantity', 1)} x {i.get('name', '')}" for i in (o.items or []))
        rows.append([str(len(rows) + 1), f'Room service: {line}', '-', money(o.total_amount)])
        extras += o.total_amount
    columns = [('#', 8, 'L'), ('Description', 110, 'L'), ('GST', 18, 'R'), ('Amount', 34, 'R')]
    totals = [('Room charges', money(room_charge), False)]
    if extras:
        totals.append(('Room service', money(extras), False))
    if booking.tax_amount:
        totals.append(('GST on room' + (' (added)' if booking.total_amount > room_charge else ' (included)'), money(booking.tax_amount), False))
    totals.append(('Total', money(booking.total_amount + extras), True))
    guest = booking.guest
    return render_invoice(
        booking.tenant, title='Guest folio', number=f'HTL-{booking.id:06d}', date_text=_dt(booking.check_out),
        bill_to=[f'{guest.first_name} {guest.last_name}'.strip(), ('Phone: ' + guest.phone) if guest.phone else ''],
        meta=[('Room', f'{booking.room.room_number} ({rt.name})'), ('Check-in', _dt(booking.check_in)), ('Check-out', _dt(booking.check_out)),
              ('Status', booking.get_status_display())],
        columns=columns, rows=rows, totals=totals, gst=_gst(booking), footer='Thank you for staying with us.')


def _school_identity(tenant):
    """The tenant's own address/phone, falling back to the admin's profile (where schools entered them before)."""
    from types import SimpleNamespace
    from api.models.user import UserProfile
    address, phone = tenant.address, tenant.phone
    if not (address and phone):
        admin = UserProfile.objects.filter(tenant=tenant, role__name__in=['admin', 'principal']).exclude(address__isnull=True).exclude(address='').first() \
            or UserProfile.objects.filter(tenant=tenant, role__name='admin').first()
        if admin:
            address = address or admin.address or ''
            phone = phone or admin.phone or ''
    return SimpleNamespace(name=tenant.name, address=address, phone=phone, gstin=tenant.gstin)


def fee_receipt(payment):
    from django.db.models import Sum
    from education.models import FeePayment
    fs = payment.fee_structure
    student = payment.student
    total_fee = fs.amount if fs else payment.amount_paid
    earlier = FeePayment.objects.filter(tenant=payment.tenant, student=student, fee_structure=fs, id__lte=payment.id) if fs else FeePayment.objects.filter(pk=payment.pk)
    agg = earlier.aggregate(paid=Sum('amount_paid'), disc=Sum('discount_amount'))
    paid_to_date, discounts = agg['paid'] or ZERO, agg['disc'] or ZERO
    balance = max(ZERO, total_fee - paid_to_date - discounts)
    fee_name = fs.get_fee_type_display() if fs else 'Fee'
    rows = [['1', f'{fee_name}' + (f'\nInstalment: {payment.installment}' if payment.installment_id else ''), money(payment.amount_paid)]]
    totals = [('Total fee', money(total_fee), False)]
    if payment.discount_amount:
        totals.append(('Discount', '-' + money(payment.discount_amount), False))
    totals += [('Paid till date', money(paid_to_date), False), ('Balance due', money(balance), False), ('Amount received', money(payment.amount_paid), True)]
    klass = student.assigned_class.name if student.assigned_class_id else ''
    return render_invoice(
        _school_identity(payment.tenant), title='Fee receipt', number=payment.receipt_number or f'FEE-{payment.id:06d}',
        date_text=payment.payment_date.strftime('%d %b %Y'),
        bill_to=[student.name, f'Roll no: {student.upper_id}' if student.upper_id else '', f'Class: {klass}' if klass else '',
                 f'Parent: {student.parent_name}' if student.parent_name else '', f'Phone: {student.parent_phone}' if student.parent_phone else ''],
        meta=[('Academic year', str(payment.academic_year) if payment.academic_year else ''), ('Paid by', payment.get_payment_method_display() if hasattr(payment, 'get_payment_method_display') else payment.payment_method),
              ('Received by', (payment.collected_by.user.get_full_name() or payment.collected_by.user.username) if payment.collected_by_id else '')],
        columns=[('#', 8, 'L'), ('Description', 132, 'L'), ('Amount', 38, 'R')], rows=rows, totals=totals,
        notes=[f'Note: {payment.notes}'] if payment.notes else None, footer='Thank you for your payment.', bill_label='STUDENT')


# ---------------------------------------------------------------- order documents
def _party(obj):
    return [obj.name, getattr(obj, 'address', '') or '', ('Phone: ' + obj.phone) if getattr(obj, 'phone', '') and obj.phone != '-' else '',
            ('GSTIN: ' + obj.gst_number) if getattr(obj, 'gst_number', '') else '']


def _qty(value):
    value = Decimal(str(value))
    return f'{value:,.0f}' if value == value.to_integral() else f'{value:,.2f}'


def manufacturing_sales_order(so):
    rows = []
    for i, it in enumerate(so.items.select_related('finished_good'), 1):
        rows.append([str(i), it.finished_good.name, it.hsn_code or '-', _qty(it.quantity), money(it.unit_price), _rate(it.gst_rate), money(it.total_price)])
    columns = [('#', 8, 'L'), ('Item', 62, 'L'), ('HSN', 16, 'L'), ('Qty', 14, 'R'), ('Rate', 26, 'R'), ('GST', 14, 'R'), ('Amount', 26, 'R')]
    totals = [('Subtotal', money(so.subtotal), False)]
    if so.discount_amount:
        totals.append(('Discount', '-' + money(so.discount_amount), False))
    if so.tax_amount:
        totals.append(('GST (added)', money(so.tax_amount), False))
    totals.append(('Total', money(so.total_amount), True))
    gst = {'cgst': so.cgst_amount, 'sgst': so.sgst_amount, 'igst': so.igst_amount}
    return render_invoice(
        so.tenant, title='Tax invoice' if so.tax_amount else 'Sales order', number=so.so_number, date_text=so.order_date.strftime('%d %b %Y'),
        bill_to=_party(so.customer),
        meta=[('Status', so.get_status_display()), ('Payment', so.get_payment_status_display()),
              ('Terms', so.customer.payment_terms), ('Dispatch from', so.warehouse.name)],
        columns=columns, rows=rows, totals=totals, gst=gst, footer='Thank you for your business.')


def _purchase_order(po, party, rows, columns, meta, extra_note=None):
    totals = []
    if getattr(po, 'subtotal', 0):
        totals.append(('Subtotal', money(po.subtotal), False))
    if getattr(po, 'tax_amount', 0):
        totals.append(('GST', money(po.tax_amount), False))
    totals.append(('Total', money(po.total_amount), True))
    return render_invoice(
        po.tenant, title='Purchase order', number=po.po_number, date_text=po.order_date.strftime('%d %b %Y'), bill_to=party, meta=meta,
        columns=columns, rows=rows, totals=totals, bill_label='SUPPLIER',
        notes=['Please confirm receipt of this order and the delivery date.'] + ([extra_note] if extra_note else []),
        footer='Authorised signature: ____________________')


def manufacturing_purchase_order(po):
    rows = [[str(i), it.raw_material.name, _qty(it.quantity), money(it.unit_cost), money(it.total_cost)]
            for i, it in enumerate(po.items.select_related('raw_material'), 1)]
    columns = [('#', 8, 'L'), ('Material', 90, 'L'), ('Qty', 20, 'R'), ('Unit cost', 28, 'R'), ('Amount', 30, 'R')]
    meta = [('Expected delivery', po.expected_delivery.strftime('%d %b %Y') if po.expected_delivery else ''), ('Status', po.get_status_display()),
            ('Terms', po.supplier.payment_terms)]
    return _purchase_order(po, _party(po.supplier), rows, columns, meta)


def retail_purchase_order(po):
    rows = [[str(i), it.product.name + (f'\nSKU {it.product.sku}' if it.product.sku else ''), str(it.quantity), money(it.unit_cost), money(it.total_cost)]
            for i, it in enumerate(po.items.select_related('product'), 1)]
    columns = [('#', 8, 'L'), ('Product', 90, 'L'), ('Qty', 20, 'R'), ('Unit cost', 28, 'R'), ('Amount', 30, 'R')]
    meta = [('Expected delivery', po.expected_delivery.strftime('%d %b %Y')), ('Status', po.get_status_display()), ('Terms', po.supplier.payment_terms)]
    return _purchase_order(po, _party(po.supplier), rows, columns, meta)


def pharmacy_purchase_order(po):
    rows = [[str(i), it.medicine.name + (f' {it.medicine.strength}' if it.medicine.strength else ''), str(it.quantity), money(it.unit_cost), money(it.total_cost)]
            for i, it in enumerate(po.items.select_related('medicine'), 1)]
    columns = [('#', 8, 'L'), ('Medicine', 90, 'L'), ('Qty', 20, 'R'), ('Unit cost', 28, 'R'), ('Amount', 30, 'R')]
    meta = [('Expected delivery', po.expected_delivery.strftime('%d %b %Y')), ('Status', po.get_status_display())]
    return _purchase_order(po, _party(po.supplier), rows, columns, meta, 'Medicines must be supplied with batch number and expiry printed on each pack.')


def retail_quotation(q):
    rows = [[str(i), it.product.name + (f'\n{it.notes}' if it.notes else ''), str(it.quantity), money(it.unit_price), money(it.total_price)]
            for i, it in enumerate(q.items.select_related('product'), 1)]
    columns = [('#', 8, 'L'), ('Item', 88, 'L'), ('Qty', 20, 'R'), ('Rate', 30, 'R'), ('Amount', 30, 'R')]
    totals = [('Subtotal', money(q.subtotal), False)]
    if q.discount_amount:
        totals.append(('Discount', '-' + money(q.discount_amount), False))
    if q.tax_amount:
        totals.append(('GST', money(q.tax_amount), False))
    totals.append(('Total', money(q.total_amount), True))
    return render_invoice(
        q.tenant, title='Quotation', number=q.quotation_number, date_text=q.quotation_date.strftime('%d %b %Y'), bill_to=_party(q.customer),
        meta=[('Valid until', q.valid_until.strftime('%d %b %Y')), ('Status', q.get_status_display())], columns=columns, rows=rows, totals=totals,
        notes=[q.notes] if q.notes else None, footer='To accept this quotation, please confirm by phone or reply to us.', bill_label='PREPARED FOR')
