# Generated by Django 5.1.1 on 2024-09-18 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_alter_cartitem_quantity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cartitem',
            name='quantity',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
