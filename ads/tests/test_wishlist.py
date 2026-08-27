from django.db import IntegrityError
from django.urls import reverse

from ads.factories import AdFactory, UserFactory, WishlistItemFactory
from ads.models import Ad, WishlistItem

from .base import MediaTestCase


class WishlistTests(MediaTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.ad = AdFactory()
        self.login(self.user)

    def test_user_can_add_an_ad(self):
        response = self.client.post(
            reverse("ads:wishlist-add", args=[self.ad.pk]), follow=True
        )
        self.assertEqual(
            WishlistItem.objects.filter(user=self.user).count(), 1
        )
        self.assertContains(response, "added to your wishlist")

    def test_adding_the_same_ad_twice_shows_an_error(self):
        self.client.post(reverse("ads:wishlist-add", args=[self.ad.pk]))
        response = self.client.post(
            reverse("ads:wishlist-add", args=[self.ad.pk]), follow=True
        )
        self.assertEqual(
            WishlistItem.objects.filter(user=self.user).count(), 1
        )
        self.assertContains(response, "already in your wishlist")

    def test_database_refuses_duplicate_rows(self):
        WishlistItemFactory(user=self.user, ad=self.ad)
        with self.assertRaises(IntegrityError):
            WishlistItem.objects.create(user=self.user, ad=self.ad)

    def test_user_can_remove_an_ad(self):
        WishlistItemFactory(user=self.user, ad=self.ad)
        response = self.client.post(
            reverse("ads:wishlist-remove", args=[self.ad.pk]), follow=True
        )
        self.assertEqual(
            WishlistItem.objects.filter(user=self.user).count(), 0
        )
        self.assertContains(response, "Removed from your wishlist")

    def test_removing_an_ad_that_is_not_saved_shows_an_error(self):
        response = self.client.post(
            reverse("ads:wishlist-remove", args=[self.ad.pk]), follow=True
        )
        self.assertContains(response, "not in your wishlist")

    def test_wishlist_only_shows_the_current_user_items(self):
        mine = WishlistItemFactory(user=self.user)
        WishlistItemFactory()  # someone else's
        response = self.client.get(reverse("ads:wishlist"))
        self.assertEqual(list(response.context["items"]), [mine])

    def test_wishlist_only_shows_active_ads(self):
        active = WishlistItemFactory(user=self.user)
        WishlistItemFactory(
            user=self.user, ad=AdFactory(status=Ad.Status.DEACTIVATED)
        )
        WishlistItemFactory(
            user=self.user, ad=AdFactory(status=Ad.Status.BLOCKED)
        )
        response = self.client.get(reverse("ads:wishlist"))
        self.assertEqual(list(response.context["items"]), [active])

    def test_wishlist_shows_the_count_for_each_ad(self):
        WishlistItemFactory(user=self.user, ad=self.ad)
        WishlistItemFactory(ad=self.ad)
        response = self.client.get(reverse("ads:wishlist"))
        self.assertEqual(response.context["items"][0].wishlist_count, 2)
        self.assertContains(response, "In 2 wishlists")

    def test_wishlist_is_ordered_newest_first(self):
        first = WishlistItemFactory(user=self.user)
        second = WishlistItemFactory(user=self.user)
        response = self.client.get(reverse("ads:wishlist"))
        self.assertEqual(
            list(response.context["items"]), [second, first]
        )

    def test_blocked_ad_cannot_be_added(self):
        blocked = AdFactory(status=Ad.Status.BLOCKED)
        response = self.client.post(
            reverse("ads:wishlist-add", args=[blocked.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_deactivated_ad_cannot_be_added(self):
        hidden = AdFactory(status=Ad.Status.DEACTIVATED)
        response = self.client.post(
            reverse("ads:wishlist-add", args=[hidden.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_blocked_ad_can_still_be_removed(self):
        WishlistItemFactory(user=self.user, ad=self.ad)
        self.ad.status = Ad.Status.BLOCKED
        self.ad.save()
        self.client.post(
            reverse("ads:wishlist-remove", args=[self.ad.pk])
        )
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_anonymous_user_cannot_open_the_wishlist(self):
        self.client.logout()
        response = self.client.get(reverse("ads:wishlist"))
        self.assertEqual(response.status_code, 302)

    def test_unknown_ad_cannot_be_added(self):
        response = self.client.post(
            reverse("ads:wishlist-add", args=[9999])
        )
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_cannot_add(self):
        self.client.logout()
        response = self.client.post(
            reverse("ads:wishlist-add", args=[self.ad.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_removing_requires_post(self):
        response = self.client.get(
            reverse("ads:wishlist-remove", args=[self.ad.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_get_request_is_not_allowed(self):
        response = self.client.get(
            reverse("ads:wishlist-add", args=[self.ad.pk])
        )
        self.assertEqual(response.status_code, 405)


class SoftDeletedWishlistTests(MediaTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.ad = AdFactory()
        self.login(self.user)

    def test_removed_ad_drops_out_of_the_wishlist(self):
        kept = WishlistItemFactory(user=self.user)
        WishlistItemFactory(user=self.user, ad=self.ad)
        self.ad.delete()
        response = self.client.get(reverse("ads:wishlist"))
        self.assertEqual(list(response.context["items"]), [kept])

    def test_removed_ad_cannot_be_added(self):
        self.ad.delete()
        response = self.client.post(
            reverse("ads:wishlist-add", args=[self.ad.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(WishlistItem.objects.count(), 0)

    def test_removed_ad_can_still_be_removed_from_the_wishlist(self):
        WishlistItemFactory(user=self.user, ad=self.ad)
        self.ad.delete()
        self.client.post(
            reverse("ads:wishlist-remove", args=[self.ad.pk])
        )
        self.assertEqual(WishlistItem.objects.count(), 0)


class WishlistCounterEverywhereTests(MediaTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.ad = AdFactory(owner=self.user)
        WishlistItemFactory(ad=self.ad)
        WishlistItemFactory(ad=self.ad)
        self.login(self.user)

    def test_counter_on_ad_list(self):
        response = self.client.get(reverse("ads:ad-list"))
        self.assertContains(response, "In 2 wishlists")

    def test_counter_on_category_page(self):
        response = self.client.get(
            reverse("ads:category-detail", args=[self.ad.category.slug])
        )
        self.assertContains(response, "In 2 wishlists")

    def test_counter_on_my_posts(self):
        response = self.client.get(reverse("ads:my-ads"))
        self.assertContains(response, "In 2 wishlists")

    def test_counter_on_ad_detail(self):
        response = self.client.get(
            reverse("ads:ad-detail", args=[self.ad.pk])
        )
        self.assertEqual(response.context["ad"].wishlist_count, 2)
        self.assertContains(response, "2 times")

    def test_counter_on_wishlist(self):
        WishlistItemFactory(user=self.user, ad=self.ad)
        response = self.client.get(reverse("ads:wishlist"))
        self.assertContains(response, "In 3 wishlists")
