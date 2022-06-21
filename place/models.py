import datetime
import requests

from django.conf import settings
from django.db import models
from geopy import distance


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


def fetch_coordinates(apikey, address):
    if address == '""':
        return None
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def add_distance_to_restaurant(likely_restaurants, *order_coordinates):
    restaurants = []

    for restaurant in likely_restaurants:
        restaurant_coordinates = get_or_create_place_coord(restaurant.address)
        if None in restaurant_coordinates:
            restaurants.append({'name': f'{str(restaurant)} - Ошибка определения координат, '
                                        'проверьте адрес ресторана',
                                'distance': float('inf'),
                                })
            continue
        distance_to_restaurant = distance.distance((order_coordinates), restaurant_coordinates).km
        restaurants.append({'name': str(restaurant), 'distance': round(distance_to_restaurant, 3)})
    return restaurants


def get_or_create_place_coord(address):
        place, created = Place.objects.get_or_create(address=address)
        if not place.lng or not place.lat:
            try:
                place.lng, place.lat = fetch_coordinates(settings.YANDEX_GEOCODER_KEY, address)
            except:
                place.lng, place.lat = None, None
            place.request_date = datetime.date.today()
            place.save()
        return (place.lat, place.lng)
