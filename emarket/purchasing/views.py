from django.urls import reverse_lazy
from django.views.generic import DeleteView, ListView, CreateView
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from products.models.models import Phone
from products.models.utils import decrease_phones_count
from users.views import BaseAccountView
from users.mixins import UserLoginRequiredMixin
from .notifications import purchase_notification, product_is_over_notification
from .models import ShoppingBasket
from .filters import *
from . import *

__all__ = ["ShoppingBasketView", "DeleteProductFromBucketView", "BuyProductView", "AddProductToBasketView"]


class ShoppingBasketView(UserLoginRequiredMixin, BaseAccountView, ListView):
    model = ShoppingBasket
    template_name = "purchasing/basket.html"
    context_object_name = "products"
    section = "basket"

    def get_context_data(self, **kwargs):
        current_context = super().get_context_data(**kwargs)

        current_context.update({"is_self_account": True})

        return current_context

    def get_queryset(self):
        user = self.request.user
        return self.model.objects.filter(user=user)


class DeleteProductFromBucketView(UserLoginRequiredMixin, DeleteView):
    model = ShoppingBasket
    success_url = reverse_lazy("basket")

    def get_object(self, queryset=None):
        return self.model.objects.get(pk=self.kwargs.get("pk"), user=self.request.user)


class AddProductToBasketView(UserLoginRequiredMixin, CreateView):
    model = ShoppingBasket
    success_url = reverse_lazy("basket")
    fields = []

    def form_invalid(self, form):
        return HttpResponseRedirect(self.success_url)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.product = Phone.objects.get(pk=self.kwargs.get("productid"))

        if form.instance.product.author.id == self.request.user.id:
            return self.form_invalid(form=form)

        return super().form_valid(form=form)


class BuyProductView(UserLoginRequiredMixin, DeleteView):
    model = ShoppingBasket
    success_url = reverse_lazy("basket")
    _user_data: User
    _product_data: Phone

    def post(self, request, *args, **kwargs):
        self._user_data = self.request.user
        self._product_data = Phone.objects.get(pk=self.model.objects.get(pk=self.kwargs.get("pk")).product.id)

        return super().post(*args, request=request, **kwargs)

    def get_object(self, queryset=None):
        return self.model.objects.get(user=self._user_data, product=self._product_data)

    def form_valid(self, form):
        if not int(self._product_data.products_count):
            return self._get_product_count_null_redirect()

        purchase_notification.notify_about_purchase(purchaser=self.request.user,
                                                    owner=self._product_data.author,
                                                    product=self._product_data)

        if int(self._product_data.products_count) == 1:
            decrease_phones_count(phone=self._product_data)
            product_is_over_notification.notify_product_is_over(recipient=self._product_data.author,
                                                                product=self._product_data)

            return super().form_valid(form=form)

        decrease_phones_count(phone=self._product_data)

        return super().form_valid(form=form)

    @staticmethod
    def _get_product_count_null_redirect() -> HttpResponseRedirect:
        return HttpResponseRedirect(redirect_to=reverse_lazy("product-not-exist"))
