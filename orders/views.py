from django.conf import settings
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.generic import View
from django.contrib import messages
from .forms import OrderForm
from .models import Order, OrderItem
from cart.views import CartMixin
from cart.models import Cart
from main.models import ProductSize
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


@method_decorator(login_required(login_url='/users/login'), name='dispatch')
class CheckoutView(CartMixin, View):
    def get(self, request):
        cart = self.get_cart(request)
        logger.debug(f"Checkout view: session_key={request.session.session_key}, cart_id={cart.id}, total_items={cart.total_items}, subtotal={cart.subtotal}")

        if cart.total_items == 0:
            logger.warning("Cart is empty, redirecting to cart page")
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'orders/empty_cart.html', {'message': 'Your cart is empty'})
            return redirect('cart:cart_modal')

        total_price = cart.subtotal
        logger.debug(f"Total price: {total_price}")

        form = OrderForm(user=request.user)
        context = {
            'form': form,
            'cart': cart,
            'cart_items': cart.items.select_related('product', 'product_size__size').order_by('-added_at'),
            'total_price': total_price,
        }

        if request.headers.get('HX-Request'):
            return TemplateResponse(request, 'orders/checkout_content.html', context)
        return render(request, 'orders/checkout.html', context)

    def post(self, request):
        cart = self.get_cart(request)
        logger.debug(f"Checkout POST: session_key={request.session.session_key}, cart_id={cart.id}, total_items={cart.total_items}")

        if cart.total_items == 0:
            logger.warning("Cart is empty, redirecting to cart page")
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'orders/empty_cart.html', {'message': 'Your cart is empty'})
            return redirect('cart:cart_modal')

        total_price = cart.subtotal
        form_data = request.POST.copy()
        if not form_data.get('email'):
            form_data['email'] = request.user.email
        form = OrderForm(form_data, user=request.user)

        if form.is_valid():
            # Создаем заказ
            order = Order.objects.create(
                user=request.user,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                company=form.cleaned_data.get('company', ''),
                address1=form.cleaned_data['address1'],
                address2=form.cleaned_data.get('address2', ''),
                city=form.cleaned_data['city'],
                country=form.cleaned_data['country'],
                province=form.cleaned_data.get('province', ''),
                postal_code=form.cleaned_data['postal_code'],
                phone=form.cleaned_data['phone'],
                special_instructions=form.cleaned_data.get('special_instructions', ''),
                total_price=total_price,
                payment_provider='free',  # или можно вообще убрать это поле
            )

            # Добавляем товары из корзины в заказ
            for item in cart.items.select_related('product', 'product_size'):
                logger.debug(f"Processing cart item: product={item.product.name}, size={item.product_size.size.name if item.product_size else 'N/A'}, quantity={item.quantity}")
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    size=item.product_size,
                    quantity=item.quantity,
                    price=item.product.price or Decimal('0.00')
                )

            # Очищаем корзину
            cart.clear()
            
            # Добавляем сообщение об успехе
            messages.success(request, f'Заказ №{order.id} успешно создан!')

            # Перенаправляем на страницу заказа или на главную
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=200)
                response['HX-Redirect'] = reverse('main:index')
                return response
            return redirect('main:index', order_id=order.id)
            
        else:
            logger.warning(f"Form validation error: {form.errors}")
            context = {
                'form': form,
                'cart': cart,
                'cart_items': cart.items.select_related('product', 'product_size__size').order_by('-added_at'),
                'total_price': total_price,
                'error_message': 'Пожалуйста, исправьте ошибки в форме.',
            }
            if request.headers.get('HX-Request'):
                return TemplateResponse(request, 'orders/checkout_content.html', context)
            return render(request, 'orders/checkout.html', context)


# Добавьте это представление для страницы успешного заказа
@method_decorator(login_required(login_url='/users/login'), name='dispatch')
class OrderSuccessView(View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'orders/empty_cart.html', {'order': order})