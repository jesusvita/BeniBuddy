# Generated by Django 5.1.6 on 2025-02-24 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_tip_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tip',
            name='date',
            field=models.DateTimeField(),
        ),
    ]
