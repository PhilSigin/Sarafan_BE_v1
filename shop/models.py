import os
from PIL import Image

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from mptt.models import MPTTModel, TreeForeignKey

from django.utils.text import slugify  # кажется, не нужно так как это надо делать в админке


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")

    def __str__(self):
        return f"Корзина пользователя {self.user.username}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.quantity * item.product.price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"


class Category(MPTTModel):

    class Meta:
        verbose_name = 'Категория товаров'
        verbose_name_plural = 'Категории товаров'

    cat_name = models.CharField(max_length=100, verbose_name="Категория")
    cat_slug = models.SlugField(max_length=100, unique=True, blank=False, null=False, verbose_name="Slug")
    cat_img = models.ImageField(upload_to='categories/', blank=False, null=False,
                                verbose_name="Изображение категории")
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    def __str__(self):
        return self.cat_name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", verbose_name="Категория")
    name = models.CharField(max_length=100, verbose_name="Наименование")
    slug = models.SlugField(max_length=100, unique=True, blank=False, null=False, verbose_name="Slug")
    image = models.ImageField(upload_to='products/', null=True, blank=True,
                              verbose_name="Изображение продукта")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image_large = models.ImageField(upload_to='products/', editable=False, null=True, blank=True)
    image_small = models.ImageField(upload_to='products/', editable=False, null=True, blank=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def save(self, *args, **kwargs):
        # Автоматическая генерация slug из имени, если slug не указан
        # Точно ли нужен? Дублируется часть того, что есть в админке
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# Флаг для предотвращения бесконечной рекурсии
processing_thumbnails = False


def create_thumbnails(instance, filename, size):
    img = Image.open(instance.image.path)
    img = img.convert('RGB')
    img.thumbnail(size)

    # Генерация имени файлов с превью
    thumbnail_name, ext = os.path.splitext(filename)
    thumbnail_name = f"{thumbnail_name}_{size[0]}x{size[1]}{ext}"

    # Корректный путь для сохранения файла
    thumbnail_name_base = os.path.basename(thumbnail_name)
    thumbnail_path = os.path.join(os.path.dirname(instance.image.path), thumbnail_name_base)

    img.save(thumbnail_path)

    return thumbnail_name_base


@receiver(post_save, sender=Product)
def generate_thumbnails(sender, instance, **kwargs):
    global processing_thumbnails

    # Проверяем флаг, чтобы избежать рекурсии
    if processing_thumbnails:
        return

    if instance.image:
        try:
            processing_thumbnails = True  # Устанавливаем флаг перед началом обработки

            # Создание больших и малых миниатюр
            large_image = create_thumbnails(instance, instance.image.name, (1000, 1000))
            small_image = create_thumbnails(instance, instance.image.name, (320, 320))

            # Обновление путей к миниатюрам
            instance.image_large = os.path.join('products/', large_image)
            instance.image_small = os.path.join('products/', small_image)

            # Сохраняем объект с обновленными полями для миниатюр
            instance.save()

        finally:
            processing_thumbnails = False  # Сбрасываем флаг после завершения обработки
