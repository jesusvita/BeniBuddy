# Generated by Django 5.1.6 on 2025-02-24 06:43

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_alter_tip_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='tip',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
