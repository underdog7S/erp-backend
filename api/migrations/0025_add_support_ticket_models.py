# Generated migration for Support Ticket models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_add_custom_service_request'),
        ('education', '0015_feeinstallment_academic_year_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SupportTicket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_number', models.CharField(max_length=20, unique=True)),
                ('subject', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('category', models.CharField(choices=[('TECHNICAL', 'Technical Issue'), ('BILLING', 'Billing & Payment'), ('FEATURE', 'Feature Request'), ('ACCOUNT', 'Account Management'), ('GENERAL', 'General Inquiry'), ('BUG', 'Bug Report')], max_length=20)),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent')], default='MEDIUM', max_length=20)),
                ('status', models.CharField(choices=[('OPEN', 'Open'), ('IN_PROGRESS', 'In Progress'), ('WAITING_CUSTOMER', 'Waiting for Customer'), ('RESOLVED', 'Resolved'), ('CLOSED', 'Closed')], default='OPEN', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('response_time', models.DurationField(blank=True, null=True)),
                ('resolution_time', models.DurationField(blank=True, null=True)),
                ('tawk_conversation_id', models.CharField(blank=True, max_length=100)),
                ('tawk_visitor_id', models.CharField(blank=True, max_length=100)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_tickets', to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to='api.tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='support_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TicketResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('is_internal', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('attachment', models.FileField(blank=True, null=True, upload_to='ticket_attachments/')),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='responses', to='api.supportticket')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ticket_responses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='TicketSLA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('TECHNICAL', 'Technical Issue'), ('BILLING', 'Billing & Payment'), ('FEATURE', 'Feature Request'), ('ACCOUNT', 'Account Management'), ('GENERAL', 'General Inquiry'), ('BUG', 'Bug Report')], max_length=20)),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent')], max_length=20)),
                ('first_response_hours', models.IntegerField()),
                ('resolution_hours', models.IntegerField()),
                ('escalation_hours', models.IntegerField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('escalation_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ticket_slas', to='api.tenant')),
            ],
            options={
                'unique_together': {('tenant', 'category', 'priority')},
            },
        ),
        migrations.CreateModel(
            name='TawkToIntegration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_id', models.CharField(max_length=100)),
                ('widget_id', models.CharField(max_length=100)),
                ('auto_create_tickets', models.BooleanField(default=True)),
                ('ticket_category', models.CharField(choices=[('TECHNICAL', 'Technical Issue'), ('BILLING', 'Billing & Payment'), ('FEATURE', 'Feature Request'), ('ACCOUNT', 'Account Management'), ('GENERAL', 'General Inquiry'), ('BUG', 'Bug Report')], default='GENERAL', max_length=20)),
                ('welcome_message', models.TextField(blank=True)),
                ('offline_message', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('assign_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tawk_integration', to='api.tenant')),
            ],
            options={
                'unique_together': {('tenant',)},
            },
        ),
        migrations.AddIndex(
            model_name='supportticket',
            index=models.Index(fields=['tenant', 'status'], name='api_support_tenant__idx'),
        ),
        migrations.AddIndex(
            model_name='supportticket',
            index=models.Index(fields=['priority', 'status'], name='api_support_priorit_idx'),
        ),
        migrations.AddIndex(
            model_name='supportticket',
            index=models.Index(fields=['assigned_to', 'status'], name='api_support_assigne_idx'),
        ),
    ]

