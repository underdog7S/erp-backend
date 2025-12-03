from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0032_ticketcategory_ticketpriority'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='public_settings_unlocked',
            field=models.BooleanField(
                default=False,
                help_text='Allow tenant to edit public settings even on the Free plan',
            ),
        ),
        migrations.AddField(
            model_name='tenant',
            name='upi_display_name',
            field=models.CharField(
                blank=True,
                help_text='Name shown with UPI QR codes and links',
                max_length=120,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='tenant',
            name='upi_id',
            field=models.CharField(
                blank=True,
                help_text='Primary UPI ID / virtual payment address',
                max_length=120,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='tenant',
            name='upi_notes',
            field=models.CharField(
                blank=True,
                help_text='Optional instructions that appear near the UPI QR code',
                max_length=180,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='tenant',
            name='upi_payments_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Expose UPI payment instructions inside the portal',
            ),
        ),
    ]

