from django.urls import reverse

from ads.factories import AdFactory, CategoryFactory, WishlistItemFactory
from ads.models import Ad, Category

from .base import MediaTestCase


class CategoryListViewTests(MediaTestCase):
    def test_active_categories_are_listed(self):
        shown = CategoryFactory(name="Bikes")
        CategoryFactory(
            name="Retired", slug="retired", status=Category.Status.HIDDEN
        )
        response = self.client.get(reverse("ads:category-list"))
        self.assertEqual(list(response.context["categories"]), [shown])

    def test_categories_are_ordered_by_name(self):
        b = CategoryFactory(name="Bikes")
        a = CategoryFactory(name="Antiques")
        response = self.client.get(reverse("ads:category-list"))
        self.assertEqual(list(response.context["categories"]), [a, b])

    def test_ad_count_only_counts_visible_ads(self):
        category = CategoryFactory(name="Bikes")
        AdFactory(category=category, status=Ad.Status.ACTIVE)
        AdFactory(category=category, status=Ad.Status.ACTIVE)
        AdFactory(category=category, status=Ad.Status.DEACTIVATED)
        AdFactory(category=category, status=Ad.Status.BLOCKED)
        AdFactory(category=CategoryFactory(name="Other"))
        removed = AdFactory(category=category)
        removed.delete()
        response = self.client.get(reverse("ads:category-list"))
        counts = {
            c.slug: c.ad_count for c in response.context["categories"]
        }
        self.assertEqual(counts["bikes"], 2)
        self.assertEqual(counts["other"], 1)

    def test_empty_state(self):
        response = self.client.get(reverse("ads:category-list"))
        self.assertContains(response, "No categories yet.")


class CategoryAdsViewTests(MediaTestCase):
    def setUp(self):
        self.category = CategoryFactory(name="Bikes")
        self.other = CategoryFactory(name="Other")

    def url(self, category=None):
        category = category or self.category
        return reverse("ads:category-detail", args=[category.slug])

    def test_only_ads_from_this_category_are_listed(self):
        mine = AdFactory(category=self.category)
        AdFactory(category=self.other)
        response = self.client.get(self.url())
        self.assertEqual(list(response.context["ads"]), [mine])

    def test_only_active_ads_are_listed(self):
        active = AdFactory(category=self.category, status=Ad.Status.ACTIVE)
        AdFactory(category=self.category, status=Ad.Status.DEACTIVATED)
        AdFactory(category=self.category, status=Ad.Status.BLOCKED)
        response = self.client.get(self.url())
        self.assertEqual(list(response.context["ads"]), [active])

    def test_removed_ads_are_excluded(self):
        kept = AdFactory(category=self.category)
        gone = AdFactory(category=self.category)
        gone.delete()
        response = self.client.get(self.url())
        self.assertEqual(list(response.context["ads"]), [kept])

    def test_hidden_category_returns_404(self):
        hidden = CategoryFactory(
            name="Retired", slug="retired", status=Category.Status.HIDDEN
        )
        self.assertEqual(self.client.get(self.url(hidden)).status_code, 404)

    def test_unknown_category_returns_404(self):
        response = self.client.get(
            reverse("ads:category-detail", args=["nope"])
        )
        self.assertEqual(response.status_code, 404)

    def test_wishlist_counter_is_shown(self):
        ad = AdFactory(category=self.category)
        WishlistItemFactory(ad=ad)
        WishlistItemFactory(ad=ad)
        response = self.client.get(self.url())
        self.assertEqual(response.context["ads"][0].wishlist_count, 2)
        self.assertContains(response, "In 2 wishlists")

    def test_counter_ignores_other_categories(self):
        mine = AdFactory(category=self.category)
        elsewhere = AdFactory(category=self.other)
        WishlistItemFactory(ad=elsewhere)
        response = self.client.get(self.url())
        self.assertEqual(response.context["ads"][0].wishlist_count, 0)
        self.assertEqual(list(response.context["ads"]), [mine])

    def test_ads_are_ordered_newest_first(self):
        first = AdFactory(category=self.category)
        second = AdFactory(category=self.category)
        response = self.client.get(self.url())
        self.assertEqual(list(response.context["ads"]), [second, first])

    def test_pagination_shows_six_per_page(self):
        AdFactory.create_batch(8, category=self.category)
        response = self.client.get(self.url())
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["ads"]), 6)

    def test_empty_state(self):
        response = self.client.get(self.url())
        self.assertContains(response, "No active ads in this category yet.")

    def test_page_is_public(self):
        AdFactory(category=self.category)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bikes")


class HiddenCategoryTests(MediaTestCase):
    def setUp(self):
        self.category = CategoryFactory(name="Bikes")

    def test_hiding_a_category_does_not_hide_existing_ads(self):
        ad = AdFactory(category=self.category)
        self.category.status = Category.Status.HIDDEN
        self.category.save()
        response = self.client.get(reverse("ads:ad-list"))
        self.assertIn(ad, response.context["ads"])

    def test_hidden_category_is_not_linked_from_the_ad_list(self):
        AdFactory(category=self.category)
        self.category.status = Category.Status.HIDDEN
        self.category.save()
        response = self.client.get(reverse("ads:ad-list"))
        self.assertNotContains(
            response,
            reverse("ads:category-detail", args=[self.category.slug]),
        )
