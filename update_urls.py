import os

with open('d:/ERP/backend/api/urls.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("path('admin/tenant-logo/', admin_views.TenantLogoView.as_view(), name='tenant-logo'),", "path('admin/tenant-logo/', admin_views.TenantLogoView.as_view(), name='tenant-logo'),\n    path('admin/seed-plans/', admin_views.SeedPlansView.as_view(), name='admin-seed-plans'),")

with open('d:/ERP/backend/api/urls.py', 'w', encoding='utf-8') as f:
    f.write(content)
