from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
)

from .forms import AdForm
from .statistics import post_statistics
from .models import Ad, Category, WishlistItem


def active_ads():
    return (
        Ad.available_objects.filter(status=Ad.Status.ACTIVE)
        .select_related("owner", "category")
        .annotate(wishlist_count=Count("wishlisted_by"))
        .order_by("-created")
    )


class WishlistIdsMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context["wishlist_ids"] = set(
                WishlistItem.objects.filter(user=user).values_list(
                    "ad_id", flat=True
                )
            )
        else:
            context["wishlist_ids"] = set()
        return context


class AdListView(WishlistIdsMixin, ListView):
    template_name = "ads/ad_list.html"
    context_object_name = "ads"
    paginate_by = 6

    def get_queryset(self):
        return active_ads()


class CategoryListView(ListView):
    template_name = "ads/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return (
            Category.objects.filter(status=Category.Status.ACTIVE)
            .annotate(
                ad_count=Count(
                    "ads",
                    filter=Q(
                        ads__status=Ad.Status.ACTIVE,
                        ads__is_removed=False,
                    ),
                )
            )
            .order_by("name")
        )


class CategoryAdsView(WishlistIdsMixin, ListView):
    template_name = "ads/category_detail.html"
    context_object_name = "ads"
    paginate_by = 6

    @cached_property
    def category(self):
        return get_object_or_404(
            Category,
            slug=self.kwargs["slug"],
            status=Category.Status.ACTIVE,
        )

    def get_queryset(self):
        return active_ads().filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category"] = self.category
        return context


class AdDetailView(DetailView):
    model = Ad
    template_name = "ads/ad_detail.html"
    context_object_name = "ad"

    def get_queryset(self):
        return (
            Ad.available_objects.filter(status=Ad.Status.ACTIVE)
            .select_related("owner", "category")
            .annotate(wishlist_count=Count("wishlisted_by"))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["in_wishlist"] = (
            self.request.user.is_authenticated
            and WishlistItem.objects.filter(
                user=self.request.user, ad=self.object
            ).exists()
        )
        return context


class AdCreateView(LoginRequiredMixin, CreateView):
    model = Ad
    form_class = AdForm
    template_name = "ads/ad_form.html"
    success_url = reverse_lazy("ads:ad-list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MyAdsView(LoginRequiredMixin, ListView):
    template_name = "ads/my_ads.html"
    context_object_name = "ads"
    paginate_by = 6

    def get_queryset(self):
        return (
            Ad.available_objects.filter(owner=self.request.user)
            .select_related("category")
            .annotate(wishlist_count=Count("wishlisted_by"))
            .order_by("-created")
        )


class WishlistView(LoginRequiredMixin, ListView):
    template_name = "ads/wishlist.html"
    context_object_name = "items"
    paginate_by = 6

    def get_queryset(self):
        return (
            WishlistItem.objects.filter(
                user=self.request.user,
                ad__status=Ad.Status.ACTIVE,
                ad__is_removed=False,
            )
            .select_related("ad", "ad__owner", "ad__category")
            .annotate(wishlist_count=Count("ad__wishlisted_by"))
            .order_by("-added")
        )


class StatisticsView(UserPassesTestMixin, TemplateView):
    template_name = "ads/statistics.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stats"] = post_statistics()
        return context


@login_required
@require_POST
def wishlist_add(request, pk):
    ad = get_object_or_404(
        Ad.available_objects, pk=pk, status=Ad.Status.ACTIVE
    )
    _, created = WishlistItem.objects.get_or_create(
        user=request.user, ad=ad
    )
    if created:
        messages.success(request, f'"{ad.title}" added to your wishlist.')
    else:
        messages.error(request, f'"{ad.title}" is already in your wishlist.')
    return redirect("ads:ad-list")


@login_required
@require_POST
def wishlist_remove(request, pk):
    deleted, _ = WishlistItem.objects.filter(
        user=request.user, ad_id=pk
    ).delete()
    if deleted:
        messages.success(request, "Removed from your wishlist.")
    else:
        messages.error(request, "This post is not in your wishlist.")
    return redirect("ads:wishlist")
