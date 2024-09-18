from django import forms
from django.contrib import admin
from django.utils.html import mark_safe

from mptt.forms import TreeNodeChoiceField
from django_mptt_admin.admin import DjangoMpttAdmin

from .models import Category, Product


""" PRODUCTS """


class ProductAdminForm(forms.ModelForm):
    # MPTT Feature: Use TreeNodeChoiceField to display the category hierarchy
    category = TreeNodeChoiceField(queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = ['category', 'name', 'slug', 'image', 'price']

    # Форма для админки, чтобы slug заполнялся автоматически по имени
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # убираем чтобы можно было исправлять slugs
        # self.fields['slug'].widget.attrs['readonly'] = True


class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'slug', 'price', 'image_preview')  # Порядок отображения в списке админки

    # Автоматическая генерация slug на основе имени
    prepopulated_fields = {'slug': ('name',)}

    # Отображение превьюшки в детальном виде и в списке
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'slug', 'image', 'image_preview', 'price')
        }),
    )

    # Делаем поле превью изображения только для чтения
    readonly_fields = ['image_preview']

    # Метод для показа превьюшки
    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="100" height="100" style="object-fit: cover;" />')
        return "Нет изображения"

    image_preview.short_description = 'Превью изображения'  # Настройка названия колонки в списке


admin.site.register(Product, ProductAdmin)


""" CATEGORIES """


class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['cat_name', 'cat_slug', 'cat_img', 'parent']

class CategoryAdmin(DjangoMpttAdmin):
    form = CategoryAdminForm
    list_display = ('cat_name', 'cat_slug', 'image_preview')  # GRID VIEW!

    # Автоматическая генерация slug на основе имени
    prepopulated_fields = {'cat_slug': ('cat_name',)}

    # Отображение превьюшки в детальном виде и в списке
    fieldsets = (
        (None, {
            'fields': ('cat_name', 'cat_slug', 'cat_img', 'image_preview', 'parent')  # Include image preview
        }),
    )

    # Делаем поле превью изображения только для чтения
    readonly_fields = ['image_preview']

    # Метод для показа превьюшки
    def image_preview(self, obj):
        if obj.cat_img:
            return mark_safe(f'<img src="{obj.cat_img.url}" width="100" height="100" style="object-fit: cover;" />')
        return "Нет изображения"

    image_preview.short_description = ''  # Убрано, чтобы не пестрить надписями ## Изображение


admin.site.register(Category, CategoryAdmin)
