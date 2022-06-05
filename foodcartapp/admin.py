from django import forms
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme

from star_burger import settings
from .models import Product
from .models import ProductCategory
from .models import Restaurant
from .models import RestaurantMenuItem
from .models import Order
from .models import OrderItem


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = [
        'name',
        'address',
        'contact_phone',
    ]
    list_display = [
        'name',
        'address',
        'contact_phone',
    ]
    inlines = [
        RestaurantMenuItemInline
    ]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'get_image_list_preview',
        'name',
        'category',
        'price',
    ]
    list_display_links = [
        'name',
    ]
    list_filter = [
        'category',
    ]
    search_fields = [
        # FIXME SQLite can not convert letter case for cyrillic words properly, so search will be buggy.
        # Migration to PostgreSQL is necessary
        'name',
        'category__name',
    ]

    inlines = [
        RestaurantMenuItemInline
    ]
    fieldsets = (
        ('Общее', {
            'fields': [
                'name',
                'category',
                'image',
                'get_image_preview',
                'price',
            ]
        }),
        ('Подробно', {
            'fields': [
                'special_status',
                'description',
            ],
            'classes': [
                'wide'
            ],
        }),
    )

    readonly_fields = [
        'get_image_preview',
    ]

    class Media:
        css = {
            "all": (
                static("admin/foodcartapp.css")
            )
        }

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html('<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url)
    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html('<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>', edit_url=edit_url, src=obj.image.url)
    get_image_list_preview.short_description = 'превью'


@admin.register(ProductCategory)
class ProductAdmin(admin.ModelAdmin):
    pass


class OrderAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.id:
            restaurants_with_distance = Order.objects.get_suitable_restaurants()[self.instance.id]
            suitable_restaurants = Restaurant.objects.filter(name__in=[x.split(',')[0] for x in restaurants_with_distance])
            self.fields['restaurant'].queryset = suitable_restaurants


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    form = OrderAdminForm

    inlines = [
        OrderItemInline
    ]
    fields = ['firstname',
              'lastname',
              'phonenumber',
              'address',
              'status',
              'payment_method',
              'comment',
              'registration_date',
              'call_date',
              'delivery_date',
              'restaurant',
              ]

    readonly_fields = ['registration_date']

    def response_change(self, request, obj):
        res = super().response_change(request, obj)
        if request.GET.get('next'):
            if url_has_allowed_host_and_scheme(request.GET['next'], settings.ALLOWED_HOSTS):
                return HttpResponseRedirect(request.GET['next'])
        else:
            return res

    def save_model(self, request, obj, form, change):
        if 'restaurant' in form.changed_data:
            if obj.status == obj.RAW:
                obj.status = obj.DURING
        super().save_model(request, obj, form, change)

