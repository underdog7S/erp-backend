# Generated manually for Retail/Wholesale ERP module

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0001_initial'),  # Assuming api module exists
    ]

    operations = [
        migrations.CreateModel(
            name='ProductCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('parent_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='retail.productcategory')),
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
                ('credit_limit', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Warehouse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('address', models.TextField()),
                ('contact_person', models.CharField(max_length=100)),
                ('phone', models.CharField(max_length=20)),
                ('is_primary', models.BooleanField(default=False)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('sku', models.CharField(max_length=50, unique=True)),
                ('brand', models.CharField(blank=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('unit_of_measure', models.CharField(choices=[('PCS', 'Pieces'), ('KG', 'Kilograms'), ('LTR', 'Liters'), ('MTR', 'Meters'), ('BOX', 'Box'), ('PACK', 'Pack'), ('OTHER', 'Other')], default='PCS', max_length=20)),
                ('cost_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('selling_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('mrp', models.DecimalField(decimal_places=2, max_digits=10)),
                ('reorder_level', models.IntegerField(default=10)),
                ('max_stock_level', models.IntegerField(default=100)),
                ('is_active', models.BooleanField(default=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='retail.productcategory')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Inventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_on_hand', models.IntegerField(default=0)),
                ('quantity_reserved', models.IntegerField(default=0)),
                ('quantity_available', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory', to='retail.product')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.warehouse')),
            ],
            options={
                'unique_together': {('product', 'warehouse', 'tenant')},
            },
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.TextField(blank=True)),
                ('customer_type', models.CharField(choices=[('RETAIL', 'Retail'), ('WHOLESALE', 'Wholesale'), ('DISTRIBUTOR', 'Distributor')], default='RETAIL', max_length=20)),
                ('credit_limit', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('payment_terms', models.CharField(default='Cash', max_length=100)),
                ('gst_number', models.CharField(blank=True, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
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
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('ORDERED', 'Ordered'), ('PARTIAL_RECEIVED', 'Partially Received'), ('RECEIVED', 'Received'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('notes', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('supplier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.supplier')),
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
                ('received_quantity', models.IntegerField(default=0)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.product')),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='retail.purchaseorder')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='GoodsReceipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gr_number', models.CharField(max_length=50, unique=True)),
                ('receipt_date', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('purchase_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.purchaseorder')),
                ('received_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.warehouse')),
            ],
        ),
        migrations.CreateModel(
            name='GoodsReceiptItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity_received', models.IntegerField()),
                ('quality_check', models.CharField(choices=[('PASSED', 'Passed'), ('FAILED', 'Failed'), ('PENDING', 'Pending')], default='PENDING', max_length=20)),
                ('goods_receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='retail.goodsreceipt')),
                ('purchase_order_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.purchaseorderitem')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice_number', models.CharField(max_length=50, unique=True)),
                ('sale_date', models.DateTimeField(auto_now_add=True)),
                ('subtotal', models.DecimalField(decimal_places=2, max_digits=12)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('payment_method', models.CharField(choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('UPI', 'UPI'), ('CHEQUE', 'Cheque'), ('CREDIT', 'Credit')], default='CASH', max_length=50)),
                ('payment_status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('PARTIAL', 'Partial')], default='PAID', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.customer')),
                ('sold_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.warehouse')),
            ],
        ),
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.product')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='retail.sale')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='StockTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transfer_number', models.CharField(max_length=50, unique=True)),
                ('transfer_date', models.DateField()),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('IN_TRANSIT', 'In Transit'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('from_warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers_from', to='retail.warehouse')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
                ('to_warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transfers_to', to='retail.warehouse')),
                ('transferred_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='StockTransferItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.product')),
                ('stock_transfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='retail.stocktransfer')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='StockAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adjustment_number', models.CharField(max_length=50, unique=True)),
                ('adjustment_type', models.CharField(choices=[('ADD', 'Add'), ('REMOVE', 'Remove'), ('DAMAGED', 'Damaged'), ('THEFT', 'Theft'), ('LOSS', 'Loss')], max_length=20)),
                ('reason', models.TextField()),
                ('adjustment_date', models.DateTimeField(auto_now_add=True)),
                ('adjusted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.userprofile')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tenant')),
                ('warehouse', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.warehouse')),
            ],
        ),
        migrations.CreateModel(
            name='StockAdjustmentItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField()),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='retail.product')),
                ('stock_adjustment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='retail.stockadjustment')),
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