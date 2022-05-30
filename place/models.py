from django.db import models


class Place(models.Model):
    address = models.CharField(
        'Адрес',
        max_length=200,
        unique=True,
        db_index=True,
    )
    lng = models.DecimalField(
        max_digits=17,
        decimal_places=15,
        verbose_name='Широта',
        blank=True,
        null=True,
    )
    lat = models.DecimalField(
        max_digits=17,
        decimal_places=15,
        verbose_name='Долгота',
        blank=True,
        null=True,
    )
    request_date = models.DateField(
        'Дата запроса',
        db_index=True,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.address

    class Meta:
        ordering = ['address']
        verbose_name = "Место"
        verbose_name_plural = "Места"
