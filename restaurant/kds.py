"""Kitchen display helpers: every new order becomes a ticket the kitchen can work through."""
from restaurant.models import KDSTicket


def create_kds_ticket(order):
    items = [{'name': i.menu_item.name, 'quantity': i.quantity} for i in order.items.select_related('menu_item')]
    if not items:
        return None
    label = order.table.number if order.table_id else order.get_order_type_display()
    return KDSTicket.objects.create(
        tenant=order.tenant, order=order, table_number=str(label), items=items, status='queued')
