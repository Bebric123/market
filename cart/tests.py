from django.test import TestCase, Client
from django.urls import reverse
from main.models import Product, ProductSize, Size
from cart.models import CartItem
from main.models import Category


class CartTests(TestCase):

    def setUp(self):
        self.client = Client()

        # категория
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category"
        )

        # размер
        self.size = Size.objects.create(name="M")

        # продукт (с категорией!)
        self.product = Product.objects.create(
            name="Test Product",
            slug="test-product",
            price=100,
            category=self.category   # ✅ ВАЖНО
        )

        # размер продукта
        self.product_size = ProductSize.objects.create(
            product=self.product,
            size=self.size,
            stock=10
        )

    # ✅ Добавление товара
    def test_add_to_cart(self):
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {
                'quantity': 2,
                'size_id': self.product_size.id
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 1)

        item = CartItem.objects.first()
        self.assertEqual(item.quantity, 2)

    # ❌ Добавление больше stock
    def test_add_to_cart_exceeds_stock(self):
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {
                'quantity': 50,
                'size_id': self.product_size.id
            }
        )

        self.assertEqual(response.status_code, 400)

    # 🔁 Повторное добавление
    def test_add_existing_item(self):
        url = reverse('cart:add_to_cart', args=[self.product.slug])

        self.client.post(url, {'quantity': 2, 'size_id': self.product_size.id})
        self.client.post(url, {'quantity': 3, 'size_id': self.product_size.id})

        item = CartItem.objects.first()
        self.assertEqual(item.quantity, 5)

    # 🔄 Обновление количества
    def test_update_cart_item(self):
        self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {'quantity': 2, 'size_id': self.product_size.id}
        )

        item = CartItem.objects.first()

        response = self.client.post(
            reverse('cart:update_item', args=[item.id]),
            {'quantity': 5}
        )

        self.assertEqual(response.status_code, 200)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    # 🗑 Удаление через quantity = 0
    def test_update_cart_item_delete(self):
        self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {'quantity': 2, 'size_id': self.product_size.id}
        )

        item = CartItem.objects.first()

        self.client.post(
            reverse('cart:update_item', args=[item.id]),
            {'quantity': 0}
        )

        self.assertEqual(CartItem.objects.count(), 0)

    # ❌ Удаление товара
    def test_remove_cart_item(self):
        self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {'quantity': 1, 'size_id': self.product_size.id}
        )

        item = CartItem.objects.first()

        response = self.client.post(
            reverse('cart:remove_item', args=[item.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 0)

    # 🧹 Очистка корзины
    def test_clear_cart(self):
        self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {'quantity': 2, 'size_id': self.product_size.id}
        )

        response = self.client.post(reverse('cart:clear_cart'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.count(), 0)

    # 🔢 Проверка количества и суммы
    def test_cart_count(self):
        self.client.post(
            reverse('cart:add_to_cart', args=[self.product.slug]),
            {'quantity': 3, 'size_id': self.product_size.id}
        )

        response = self.client.get(reverse('cart:cart_count'))

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data['total_items'], 3)
        self.assertEqual(data['subtotal'], 300.0)