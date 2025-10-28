# Generated manually

from django.db import migrations, models
from django.utils import timezone


def set_timestamps(apps, schema_editor):
    Student = apps.get_model('education', 'Student')
    for student in Student.objects.filter(created_at__isnull=True):
        student.created_at = timezone.now()
        student.updated_at = timezone.now()
        student.save(update_fields=['created_at', 'updated_at'])


def reverse_timestamps(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0010_alter_student_options_student_address_and_more'),
    ]

    operations = [
        migrations.RunPython(set_timestamps, reverse_timestamps),
        migrations.AlterField(
            model_name='student',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='student',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
