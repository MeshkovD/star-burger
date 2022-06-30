from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import F, Sum, OuterRef, Subquery
from phonenumber_field.modelfields import PhoneNumberField

from place.models import get_or_create_place_coord, Place, add_distance_to_restaurants


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
    def get_suitable_restaurants(self, order, all_restaurants):
        order_products_ids = [item.product.id for item in order.items.all()]

        suitable_restaurants_ids = []
        for restaurant in all_restaurants:
            restaurant_products_ids = [item.product.id for item in restaurant.menu_items.all()]

            if set(order_products_ids).issubset(restaurant_products_ids):
                suitable_restaurants_ids.append(restaurant.id)
        suitable_restaurants = all_restaurants.filter(id__in=suitable_restaurants_ids)
        return suitable_restaurants

    def add_restaurants_info(self, orders):
        all_restaurants = Restaurant.objects.prefetch_related('menu_items__product')
        for order in orders:
            suitable_restaurants = self.get_suitable_restaurants(order, all_restaurants)
            restaurants_with_distance = add_distance_to_restaurants(suitable_restaurants, order)
            order.suitable_restaurants = restaurants_with_distance
        return orders

    def get_prepared_orders_list(self):
        unprocessed_orders = Order.objects.exclude(status=Order.PROCESSED).prefetch_related('items')
        sorted_orders = unprocessed_orders.order_by('-status')

        places = Place.objects.filter(address=OuterRef('address'))
        annotated_orders = sorted_orders.annotate(
            order_cost=Sum(
                F('items__quantity') * F('items__price')
            ),
            lat=Subquery(places.values('lat')),
            lng=Subquery(places.values('lng'))
        )

        orders_with_restaurants = self.add_restaurants_info(annotated_orders)
        return orders_with_restaurants


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
    cook_in = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        related_name='cook_in',
        verbose_name='Приготовить в',
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
