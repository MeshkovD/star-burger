import datetime

from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import F, Sum
from django.db.models.signals import pre_save
from django.dispatch import receiver
from geopy import distance
from phonenumber_field.modelfields import PhoneNumberField

from place.models import Place
from place.models import fetch_coordinates
from star_burger import settings


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects.filter(availability=True).values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class ExtendedQuerySet(models.QuerySet):
    def _add_distance_to_restaurant(self, likely_restaurants, *order_coordinates):
        restaurants = []

        for restaurant in likely_restaurants:
            restaurant_coordinates = self._get_or_create_place_coord(restaurant.address)
            if None in restaurant_coordinates:
                restaurants.append({'name': f'{str(restaurant)} - Ошибка определения координат, '
                                                              'проверьте адрес ресторана',
                                    'distance': float('inf'),
                                    })
                continue
            distance_to_restaurant = distance.distance((order_coordinates), restaurant_coordinates).km
            restaurants.append({'name': str(restaurant), 'distance': round(distance_to_restaurant, 3)})
        return restaurants

    def _get_or_create_place_coord(self, address):
        place, created = Place.objects.get_or_create(address=address)
        if not place.lng or not place.lat:
            try:
                place.lng, place.lat = fetch_coordinates(settings.YANDEX_GEOCODER_KEY, address)
            except:
                place.lng, place.lat = None, None
            place.request_date = datetime.date.today()
            place.save()
        return place.lat, place.lng

    def get_suitable_restaurants(self):
        suitable_restaurants = {}
        raw_orders = Order.objects.exclude(status=Order.PROCESSED).prefetch_related('items__product')
        all_restaurants = Restaurant.objects.all()
        for order in raw_orders:
            delivery_coordinates = self._get_or_create_place_coord(order.address)
            if None in delivery_coordinates:
                suitable_restaurants[order.id] = ["Не удалось установить координаты доставки, "
                                                  "проверьте адрес заказа."]
                continue

            likely_restaurants = all_restaurants
            for item in order.items.all():
                likely_restaurants = likely_restaurants.filter(
                    menu_items__product=item.product,
                    menu_items__availability=True,
                )
            restaurants_with_distance = self._add_distance_to_restaurant(likely_restaurants, delivery_coordinates)
            sorted_restaurants = sorted(
                restaurants_with_distance,
                key=lambda restaurant: restaurant["distance"],
                reverse=False
            )
            suitable_restaurants[order.id] = [f'{restaurant["name"]}, {restaurant["distance"]} км.'
                                              for restaurant in sorted_restaurants]
        return suitable_restaurants

    def annotate_orders_cost(self):
        return Order.objects.annotate(
            order_cost=Sum(
                F('items__quantity') * F('items__price')
            )
        )

    def get_prepared_orders_list(self):
        unprocessed_orders = Order.objects.exclude(status=Order.PROCESSED)
        annotated_orders = unprocessed_orders.annotate(
            order_cost=Sum(
                F('items__quantity') * F('items__price')
            )
        )
        sorted_orders = annotated_orders.order_by('-status')
        return sorted_orders


class Order(models.Model):
    RAW = 'RW'
    DURING = 'DR'
    PROCESSED = 'PR'
    STATUS_CHOICES = [
        (RAW, 'Необработ.'),
        (DURING, 'Готовится'),
        (PROCESSED, 'Обработ.'),
    ]
    CASH = 'CS'
    ELECTRONIC = 'EL'
    PAYMENT_METHOD_CHOICES = [
        (CASH, 'Налич.'),
        (ELECTRONIC, 'Элект.'),
    ]

    firstname = models.CharField(
        'Имя',
        max_length=100,
    )
    lastname = models.CharField(
        'Фамилия',
        max_length=100,
        db_index=True,
    )
    phonenumber = PhoneNumberField(
        'Телефон',
        db_index=True,
    )
    address = models.CharField(
        'Адрес',
        max_length=100,
    )
    status = models.CharField(
        'Статус',
        max_length=2,
        choices=STATUS_CHOICES,
        default=RAW,
        db_index=True
    )
    comment = models.TextField(
        'Комментарий',
        blank=True,
    )

    registration_date = models.DateTimeField(
        'Зарегистрировано в',
        auto_now_add=True,
        db_index=True,
    )
    call_date = models.DateTimeField(
        'Звонок в',
        blank=True,
        null=True,
        db_index=True,
    )
    delivery_date = models.DateTimeField(
        'Доставлено в',
        blank=True,
        null=True,
        db_index=True,
    )
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=2,
        choices=PAYMENT_METHOD_CHOICES,
        db_index=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        related_name='restaurant',
        verbose_name='Ресторан',
        blank=True,
        null=True,
    )

    objects = ExtendedQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'Заказ #{self.id}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        verbose_name="заказ",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items',
        verbose_name='продукт',
    )
    quantity = models.IntegerField(
        'количество',
        validators=[MinValueValidator(1)],
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'позиция заказа'
        verbose_name_plural = 'позиции заказа'

    def __str__(self):
        return f"{self.product.name}"

@receiver(pre_save, sender=Order)
def my_callback(sender, instance, *args, **kwargs):
    if instance.restaurant and instance.status != instance.PROCESSED:
        instance.status = instance.DURING
