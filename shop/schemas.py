from ninja import ModelSchema, Schema
from shop.models import Category, Product
from typing import List, Optional


class CategoryFlatSchema(ModelSchema):
    """ FLAT Category, used in API directly """
    class Meta:
        model = Category
        fields = ('id', 'cat_name', 'cat_slug', 'cat_img')


class CategorySchema(Schema):
    """ TREE Category, used in API directly (Paginated one) """
    id: int
    cat_name: str
    cat_slug: str
    cat_img: str
    children: List['CategorySchema'] = []  # Recursive relationship


class CategoryAncestorListSchema(Schema):
    """ SHOWN AS A LIST IN PRODUCTS LIST """
    id: int
    cat_name: str
    cat_slug: str
    cat_img: str
    parent: Optional[int]


class ProductSchema(Schema):
    """ The only used ProductSchema at the moment """
    id: int
    name: str
    slug: str
    price: int
    image: str
    image_large: str
    image_small: str

    categories: List['CategoryAncestorListSchema'] | None = None

    """
    # Leftovers from Ninja ModelSchema #
    class Meta:
        model = Product
        fields = ('id', 'name', 'slug', 'price', 'image', 'image_large', 'image_small', 'category', 'categories')
    """
