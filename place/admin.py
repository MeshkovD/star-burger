from django.contrib import admin

from place.models import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    fields = [
        'address',
        'lng',
        'lat',
        'request_date',
    ]
