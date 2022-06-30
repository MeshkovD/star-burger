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
        return None, None
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None, None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lon, lat


def add_distance_to_restaurants(suitable_restaurants, order):
    if not any((order.lat, order.lng)):
        order.lat, order.lng = get_or_create_place_coord(order.address)

    restaurants = []

    for restaurant in suitable_restaurants:
        restaurant_coordinates = get_or_create_place_coord(restaurant.address)
        if not any(restaurant_coordinates) or not any((order.lat, order.lng)):
            restaurants.append({'name': f'{str(restaurant)} - Ошибка определения координат, ',
                                    'distance': float('inf'),
                                    })
            continue
        distance_to_restaurant = distance.distance((order.lat, order.lng), restaurant_coordinates).km
        restaurants.append({'name': str(restaurant), 'distance': round(distance_to_restaurant, 3)})
    sorted_restaurants = sorted(
        restaurants,
        key=lambda restaurant: restaurant["distance"],
        reverse=False
    )
    return [f'{restaurant["name"]}, {restaurant["distance"] if restaurant["distance"] !=float("inf") else "-" } км.'
            for restaurant in sorted_restaurants]


def get_or_create_place_coord(address):
        place, created = Place.objects.get_or_create(address=address)
        if not any([place.lng, place.lat]):
            place.lng, place.lat = fetch_coordinates(settings.YANDEX_GEOCODER_KEY, address)
            place.request_date = datetime.date.today()
            place.save()
        return (place.lat, place.lng)
