# Generated by Django 3.2 on 2022-05-04 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0050_order_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='comment',
            field=models.TextField(blank=True, max_length=500, null=True, verbose_name='Комментарий'),
        ),
    ]
