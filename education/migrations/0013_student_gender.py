# Generated manually for adding gender field to Student model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0012_alter_reportcard_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='gender',
            field=models.CharField(blank=True, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], max_length=10, null=True),
        ),
    ]

