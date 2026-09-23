def get_or_create_contact(tenant, phone=None, email=None, name=None):
    """Find an existing Contact by phone or email within this tenant, or
    create a minimal lead record for a first-time inbound sender.

    Without this, inbound SMS/WhatsApp/email threads never get a Contact
    linked - they show up as "Unknown Sender" forever, and the reply
    endpoints can't find a phone/email to send back to since they read
    thread.contact.phone / thread.contact.email, not the raw webhook
    payload.
    """
    from api.models.crm import Contact

    contact = None
    if phone:
        contact = Contact.objects.filter(tenant=tenant, phone=phone).first()
    if not contact and email:
        contact = Contact.objects.filter(tenant=tenant, email=email).first()
    if contact:
        return contact

    first_name = (name or '').strip() or (phone or email or 'Unknown')
    return Contact.objects.create(
        tenant=tenant,
        first_name=first_name[:100],
        phone=phone,
        email=email,
        contact_type='lead',
        lifecycle_stage='lead',
    )
