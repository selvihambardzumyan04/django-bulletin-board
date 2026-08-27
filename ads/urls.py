from django.urls import path

from .views import (
    AdCreateView,
    AdDetailView,
    AdListView,
    CategoryAdsView,
    CategoryListView,
    MyAdsView,
    StatisticsView,
    WishlistView,
    wishlist_add,
    wishlist_remove,
)

app_name = "ads"

urlpatterns = [
    path("", AdListView.as_view(), name="ad-list"),
    path("ads/new/", AdCreateView.as_view(), name="ad-create"),
    path("ads/<int:pk>/", AdDetailView.as_view(), name="ad-detail"),
    path(
        "categories/",
        CategoryListView.as_view(),
        name="category-list",
    ),
    path(
        "categories/<slug:slug>/",
        CategoryAdsView.as_view(),
        name="category-detail",
    ),
    path("my-ads/", MyAdsView.as_view(), name="my-ads"),
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path(
        "statistics/",
        StatisticsView.as_view(),
        name="statistics",
    ),
    path("ads/<int:pk>/wishlist/add/", wishlist_add, name="wishlist-add"),
    path(
        "ads/<int:pk>/wishlist/remove/",
        wishlist_remove,
        name="wishlist-remove",
    ),
]
