# Generated by Django 3.2 on 2022-05-04 17:47

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0054_auto_20220505_0037'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='call_date',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Дата звонка'),
        ),
        migrations.AddField(
            model_name='order',
            name='creation_date',
            field=models.DateTimeField(auto_now_add=True, db_index=True, default=datetime.datetime(2022, 5, 5, 0, 47, 47, 992225), verbose_name='Дата создания'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_date',
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Дата доставки'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('RW', 'Необработ.'), ('PR', 'Обработ.')], db_index=True, default='RW', max_length=2, verbose_name='Статус'),
        ),
    ]
