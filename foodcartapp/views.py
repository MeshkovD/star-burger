from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Product
from .models import Order


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


@api_view(['GET'])
def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return Response(dumped_products)


@api_view(['POST'])
def register_order_api(request):
    order_raw = request.data

    try:
        products = order_raw['products']
    except:
        content = {'products': "Required field"}
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    if products is None:
        content = {'products': "This field cannot be empty"}
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)
    elif isinstance(products, list) and len(products) == 0:
        content = {'products': "This list cannot be empty"}
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)
    elif isinstance(products, str):
        content = {'products': "Expected list with values, but received 'str'"}
        return Response(content, status=status.HTTP_406_NOT_ACCEPTABLE)

    order = Order.objects.create(
        firstname=order_raw['firstname'],
        lastname=order_raw['lastname'],
        phonenumber=order_raw['phonenumber'],
        address=order_raw['address'],
    )
    for product in products:
        order.add_product(product['product'], product['quantity'])
    return JsonResponse({})
