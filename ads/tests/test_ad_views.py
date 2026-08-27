from django.urls import reverse

from ads.factories import (
    AdFactory,
    CategoryFactory,
    UserFactory,
    WishlistItemFactory,
)
from ads.models import Ad

from .base import MediaTestCase, make_image


class AdListViewTests(MediaTestCase):
    def test_only_active_ads_are_listed(self):
        active = AdFactory(status=Ad.Status.ACTIVE)
        AdFactory(status=Ad.Status.DEACTIVATED)
        AdFactory(status=Ad.Status.BLOCKED)
        response = self.client.get(reverse("ads:ad-list"))
        self.assertEqual(list(response.context["ads"]), [active])

    def test_wishlist_count_is_shown(self):
        ad = AdFactory()
        WishlistItemFactory(ad=ad)
        WishlistItemFactory(ad=ad)
        response = self.client.get(reverse("ads:ad-list"))
        self.assertEqual(response.context["ads"][0].wishlist_count, 2)
        self.assertContains(response, "In 2 wishlists")

    def test_wishlist_count_is_zero_for_unwanted_ads(self):
        AdFactory()
        response = self.client.get(reverse("ads:ad-list"))
        self.assertEqual(response.context["ads"][0].wishlist_count, 0)
        self.assertContains(response, "In 0 wishlists")

    def test_wishlist_count_ignores_other_ads(self):
        wanted = AdFactory()
        other = AdFactory()
        WishlistItemFactory(ad=wanted)
        response = self.client.get(reverse("ads:ad-list"))
        counts = {
            ad.pk: ad.wishlist_count for ad in response.context["ads"]
        }
        self.assertEqual(counts[wanted.pk], 1)
        self.assertEqual(counts[other.pk], 0)

    def test_list_is_ordered_newest_first(self):
        first = AdFactory()
        second = AdFactory()
        response = self.client.get(reverse("ads:ad-list"))
        self.assertEqual(list(response.context["ads"]), [second, first])

    def test_pagination_shows_six_per_page(self):
        AdFactory.create_batch(8)
        response = self.client.get(reverse("ads:ad-list"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["ads"]), 6)

    def test_second_page_holds_the_rest(self):
        AdFactory.create_batch(8)
        response = self.client.get(reverse("ads:ad-list"), {"page": 2})
        self.assertEqual(len(response.context["ads"]), 2)


class AdDetailViewTests(MediaTestCase):
    def test_detail_page_shows_the_full_text(self):
        ad = AdFactory(text="A very long description " * 20)
        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ad.title)
        self.assertNotContains(response, "…")

    def test_deactivated_ad_returns_404(self):
        ad = AdFactory(status=Ad.Status.DEACTIVATED)
        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertEqual(response.status_code, 404)

    def test_blocked_ad_returns_404(self):
        ad = AdFactory(status=Ad.Status.BLOCKED)
        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertEqual(response.status_code, 404)

    def test_unknown_ad_returns_404(self):
        response = self.client.get(reverse("ads:ad-detail", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_in_wishlist_flag(self):
        user = UserFactory()
        ad = AdFactory()
        self.login(user)

        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertFalse(response.context["in_wishlist"])

        WishlistItemFactory(user=user, ad=ad)
        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertTrue(response.context["in_wishlist"])


class AdCreateViewTests(MediaTestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("ads:ad-create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_logged_in_user_can_create_an_ad(self):
        user = UserFactory()
        category = CategoryFactory()
        self.login(user)
        response = self.client.post(
            reverse("ads:ad-create"),
            {
                "title": "Guitar",
                "text": "Acoustic, good condition.",
                "category": category.pk,
                "phone_number": "+37455667788",
                "price": "300.00",
                "type": Ad.Type.PRIVATE,
                "status": Ad.Status.ACTIVE,
                "image": make_image(),
            },
        )
        self.assertRedirects(response, reverse("ads:ad-list"))
        ad = Ad.available_objects.get(title="Guitar")
        self.assertEqual(ad.owner, user)
        self.assertEqual(ad.category, category)


class MyAdsViewTests(MediaTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.login(self.user)

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("ads:my-ads"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_only_the_current_user_posts_are_listed(self):
        mine = AdFactory(owner=self.user)
        AdFactory()
        response = self.client.get(reverse("ads:my-ads"))
        self.assertEqual(list(response.context["ads"]), [mine])

    def test_every_status_is_listed(self):
        active = AdFactory(owner=self.user, status=Ad.Status.ACTIVE)
        off = AdFactory(owner=self.user, status=Ad.Status.DEACTIVATED)
        blocked = AdFactory(owner=self.user, status=Ad.Status.BLOCKED)
        response = self.client.get(reverse("ads:my-ads"))
        self.assertEqual(
            set(response.context["ads"]), {active, off, blocked}
        )

    def test_statuses_are_shown(self):
        AdFactory(owner=self.user, status=Ad.Status.ACTIVE)
        AdFactory(owner=self.user, status=Ad.Status.DEACTIVATED)
        AdFactory(owner=self.user, status=Ad.Status.BLOCKED)
        response = self.client.get(reverse("ads:my-ads"))
        self.assertContains(response, "Active")
        self.assertContains(response, "Deactivated")
        self.assertContains(response, "Blocked")

    def test_removed_posts_are_excluded(self):
        kept = AdFactory(owner=self.user)
        gone = AdFactory(owner=self.user)
        gone.delete()
        response = self.client.get(reverse("ads:my-ads"))
        self.assertEqual(list(response.context["ads"]), [kept])

    def test_posts_are_ordered_newest_first(self):
        first = AdFactory(owner=self.user)
        second = AdFactory(owner=self.user)
        response = self.client.get(reverse("ads:my-ads"))
        self.assertEqual(list(response.context["ads"]), [second, first])

    def test_pagination_shows_six_per_page(self):
        AdFactory.create_batch(8, owner=self.user)
        response = self.client.get(reverse("ads:my-ads"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["ads"]), 6)

    def test_empty_state(self):
        response = self.client.get(reverse("ads:my-ads"))
        self.assertContains(response, "You have not posted anything yet.")

    def test_only_active_posts_link_to_the_detail_page(self):
        active = AdFactory(owner=self.user, status=Ad.Status.ACTIVE)
        blocked = AdFactory(owner=self.user, status=Ad.Status.BLOCKED)
        response = self.client.get(reverse("ads:my-ads"))
        self.assertContains(
            response, reverse("ads:ad-detail", args=[active.pk])
        )
        self.assertNotContains(
            response, reverse("ads:ad-detail", args=[blocked.pk])
        )
