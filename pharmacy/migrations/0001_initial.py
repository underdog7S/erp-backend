# Generated manually for Pharmacy ERP module

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0001_initial'),  # Assuming api module exists
    ]

    operations = [
        migrations.CreateModel(
            name='MedicineCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('contact_person', models.CharField(max_length=100)),
                ('phone', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField()),
                ('gst_number', models.CharField(blank=True, max_length=20)),
                ('payment_terms', models.CharField(default='Net 30', max_length=100)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Medicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('generic_name', models.CharField(blank=True, max_length=200)),
                ('manufacturer', models.CharField(max_length=200)),
                ('strength', models.CharField(blank=True, max_length=50)),
                ('dosage_form', models.CharField(choices=[('TABLET', 'Tablet'), ('CAPSULE', 'Capsule'), ('SYRUP', 'Syrup'), ('INJECTION', 'Injection'), ('CREAM', 'Cream'), ('OINTMENT', 'Ointment'), ('DROPS', 'Drops'), ('INHALER', 'Inhaler'), ('OTHER', 'Other')], max_length=50)),
                ('prescription_required', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True)),
                ('side_effects', models.TextField(blank=True)),
                ('storage_conditions', models.CharField(blank=True, max_length=200)),
                ('expiry_alert_days', models.IntegerField(default=30)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pharmacy.medicinecategory')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('allergies', models.TextField(blank=True)),
                ('medical_history', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='MedicineBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_number', models.CharField(max_length=50)),
                ('manufacturing_date', models.DateField()),
                ('expiry_date', models.DateField()),
                ('cost_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('selling_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('mrp', models.DecimalField(decimal_places=2, max_digits=10)),
                ('quantity_received', models.IntegerField()),
                ('quantity_available', models.IntegerField()),
                ('location', models.CharField(blank=True, max_length=100)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='batches', to='pharmacy.medicine')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.supplier')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
            options={
                'unique_together': {('medicine', 'batch_number', 'tenant')},
            },
        ),
        migrations.CreateModel(
            name='Prescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doctor_name', models.CharField(max_length=200)),
                ('prescription_date', models.DateField()),
                ('diagnosis', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prescriptions', to='pharmacy.customer')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='PrescriptionItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dosage', models.CharField(max_length=100)),
                ('frequency', models.CharField(max_length=100)),
                ('duration', models.CharField(max_length=100)),
                ('quantity', models.IntegerField()),
                ('notes', models.TextField(blank=True)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.medicine')),
                ('prescription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='pharmacy.prescription')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(max_length=50, unique=True)),
                ('sale_date', models.DateTimeField(auto_now_add=True)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('UPI', 'UPI'), ('CHEQUE', 'Cheque'), ('INSURANCE', 'Insurance')], default='CASH', max_length=50)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('PARTIAL', 'Partial')], default='PAID', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.customer')),
                ('prescription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pharmacy.prescription')),
                ('sold_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('medicine_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.medicinebatch')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='pharmacy.sale')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='PurchaseOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('po_number', models.CharField(max_length=50, unique=True)),
                ('order_date', models.DateField()),
                ('expected_delivery', models.DateField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ORDERED', 'Ordered'), ('RECEIVED', 'Received'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('notes', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.supplier')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='PurchaseOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('unit_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_cost', models.DecimalField(decimal_places=2, max_digits=10)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.medicine')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='pharmacy.purchaseorder')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='StockAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adjustment_type', models.CharField(choices=[('ADD', 'Add'), ('REMOVE', 'Remove'), ('DAMAGED', 'Damaged'), ('EXPIRED', 'Expired'), ('THEFT', 'Theft')], max_length=20)),
                ('quantity', models.IntegerField()),
                ('reason', models.TextField()),
                ('adjustment_date', models.DateTimeField(auto_now_add=True)),
                ('medicine_batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pharmacy.medicinebatch')),
                ('adjusted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='StaffAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('check_in_time', models.DateTimeField(blank=True, null=True)),
                ('check_out_time', models.DateTimeField(blank=True, null=True)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
            options={
                'unique_together': {('staff', 'date', 'tenant')},
            },
        ),
    ] 