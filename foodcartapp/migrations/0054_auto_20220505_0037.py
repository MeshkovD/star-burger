# Generated by Django 3.2 on 2022-05-04 17:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0053_auto_20220505_0035'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='call_date',
        ),
        migrations.RemoveField(
            model_name='order',
            name='creation_date',
        ),
        migrations.RemoveField(
            model_name='order',
            name='delivery_date',
        ),
    ]
