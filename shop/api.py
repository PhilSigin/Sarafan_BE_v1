from typing import List, Optional, Annotated

from annotated_types import Gt

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch

from ninja import NinjaAPI
from ninja.pagination import paginate
from ninja.responses import Response

from ninja_jwt.routers.obtain import obtain_pair_router
from ninja_jwt.authentication import JWTAuth

from shop.models import Category, Product, Cart, CartItem
from shop.schemas import CategorySchema, CategoryFlatSchema, CategoryAncestorListSchema, ProductSchema


shop_api = NinjaAPI(openapi_extra={'tags': [
    {'name': 'Auth', 'description': 'Авторизация и токены (by django-ninja-jwt)'},
    {'name': 'Products', 'description': 'Показ товаров'},
    {'name': 'Categories', 'description': 'Многоуровневые категории, MPTT'},
    {'name': 'Cart', 'description': 'Показ и изменение товаров в корзине'},
    {'name': 'Test', 'description': 'Парочка тестовых функций для проверки авторизации'},]})


# ЧАСТЬ, ОТВЕЧАЮЩАЯ ЗА ТОКЕНЫ

shop_api.add_router('/token', tags=['Auth'], router=obtain_pair_router)


""" КОРЗИНА """

# Показать корзину
@shop_api.get("/cart/", auth=JWTAuth(), summary="Отображение содержимого корзины", tags=["Cart"])
def get_cart(request):
    user = request.auth

    # Check if the user has a cart, if not create one
    cart, created = Cart.objects.get_or_create(user=user)

    # Prepare the cart's contents
    cart_items = [
        {   "id": item.product.id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "price_per_item": item.product.price,
            "total_price_for_item": item.quantity * item.product.price,
        }
        for item in cart.items.all()
    ]

    # Calculate the cart's total price
    total_price = cart.total_price

    # Response with cart details
    return {
        "total_items": cart.total_items,
        "total_price": total_price,
        "items": cart_items,
    }


# Очистить корзину
@shop_api.post("cart/clear/", auth=JWTAuth(), summary="Очистка корзины", tags=["Cart"])
def clear_cart(request):
    user = request.auth
    cart, created = Cart.objects.get_or_create(user=user)
    if created is False:
        cart.items.all().delete()
    return {"success": True, "message": "Корзина очищена"}


# Удалить продукт из корзины
@shop_api.post("cart/remove", auth=JWTAuth(), summary="Удаление продукта из корзины", tags=["Cart"])
def remove_from_cart(request, product_id: int):
    user = request.auth

    try:
        product = Product.objects.get(id=product_id)
    except ObjectDoesNotExist:
        return {"success": False, "message": "Такого продукта не существует"}

    cart, created = Cart.objects.get_or_create(user=user)

    if created is True:
        return {"success": False, "message": "Корзина пуста, такого продукта нет в корзине"}

    cart_item = cart.items.filter(product_id=product_id).first()
    if not cart_item:
        return {"success": False, "message": "Такого продукта нет в корзине"}

    cart_item.delete()
    return {"success": True, "message": "Продукт удален из корзины"}


# Добавить X продуктов в корзину
@shop_api.post("cart/add", auth=JWTAuth(), summary="Добавление x продуктов в корзину", tags=["Cart"])
def add_to_cart(request, product_id: int, quantity: Optional[Annotated[int, Gt(0)]] = 1):
    user = request.auth

    try:
        product = Product.objects.get(id=product_id)
    except ObjectDoesNotExist:
        # return 400, "Такого продукта нет"
        return Response({"error": "Такого продукта нет"}, status=400)

    cart, created = Cart.objects.get_or_create(user=user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    cart_item.quantity += quantity
    cart_item.save()
    return {"success": True, "message": f"В корзину добавлено: '{cart_item.product.name}', {quantity} шт., итого: {cart_item.quantity} шт."}


# Изменить количество товара в корзине
@shop_api.post("cart/update", auth=JWTAuth(), summary="Изменение количества товара в корзине (или удаление)",  tags=["Cart"])
def update_cart_item(request, product_id: int, quantity: Annotated[int, Gt(-1)]):

    user = request.auth

    try:
        product = Product.objects.get(id=product_id)
    except ObjectDoesNotExist:
        return {"success": False, "message": "Такого продукта не существует"}

    cart = Cart.objects.filter(user=user).first()
    if not cart:
        return {"success": False, "message": "Такого продукта нет в корзине"}

    cart_item = cart.items.filter(product=product).first()
    if not cart_item:
        return {"success": False, "message": "Такого продукта нет в корзине"}

    if quantity == 0:
        cart_item.delete()
        return {"success": True, "message": f"Продукт '{product.name}' удален из корзины, так как количество стало 0"}

    cart_item.quantity = quantity
    cart_item.save()
    return {"success": True, "message": f"Количество товара '{product.name}' обновлено до {cart_item.quantity} шт."}


""" ПРОДУКТЫ """


# ПОКАЗ ВСЕХ ПРОДУКТОВ
# localhost:8000/api/products?limit=2&offset=0
@shop_api.get("products", response=List[ProductSchema],
              summary="Показ всех продуктов",
              description="""<strong>Эндпоинт вывода продуктов с пагинацией. </strong>
              Каждый продукт в выводе должен иметь поля: наименование, slug, категория, подкатегория, 
              цена, список изображений. Не выполнен показ отдельных продуктов.""",
              tags=["Products"])
@paginate
def get_products(request):
    products = Product.objects.prefetch_related(Prefetch('category', queryset=Category.objects.all())).all()

    for product in products:
        ancestors = product.category.get_ancestors(include_self=True)
        # MPTT - Convert ancestors to a list of CategoryAncestorSchema objects
        product.categories = [
            CategoryAncestorListSchema(
                id=a.id, cat_name=a.cat_name, cat_slug=a.cat_slug, cat_img=a.cat_img, parent=a.parent_id)
            for a in ancestors
        ]

    return products


def build_category_tree(categories):
    def build_tree(category):
        # Create a dictionary with the basic category fields
        category_data = {
            'id': category.id,
            'cat_name': category.cat_name,
            'cat_slug': category.cat_slug,
            'cat_img': category.cat_img,
            'children': []  # Prepare a place for the children
        }
        # Recursively add children to the current category
        for child in category.get_children():
            category_data['children'].append(build_tree(child))
        return category_data

    # Find top-level categories and recursively build the tree for each
    return [build_tree(cat) for cat in categories if cat.is_root_node()]


""" КАТЕГОРИИ """


# localhost:8000/api/categories?limit=2&offset=0
@shop_api.get("categories", summary="Категории в древовидном виде",
              response=List[CategorySchema], tags=["Categories"])
@paginate
def get_categories(request):
    categories = Category.objects.all()  # Get all categories
    nested_categories = build_category_tree(categories)  # Build the nested structure
    return nested_categories


# http://localhost:8000/api/categories/  - not paginated, without items.... count, ALSO - FLAT Structure.
@shop_api.get("categories/", summary="Категории в плоском виде",
              response=list[CategoryFlatSchema], tags=["Categories"])
def get_categories_flat(request):
    return Category.objects.all()


""" ТЕСТОВОЕ """

@shop_api.get("/protected_data", auth=JWTAuth(),
              summary="Проверка на доступность информации по токену", tags=["Test"])
def protected_data(request):
    user = request.auth
    return {"message": "This data is protected", "username": user.email}



@shop_api.get("/protected_data_test", auth=JWTAuth(),
              summary="Проверка токена", tags=["Test"])
def protected_data_test(request):
    return {"message": "Token is recognized!"}




