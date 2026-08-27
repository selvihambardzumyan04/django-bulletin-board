import io
import random
import shutil
import tempfile

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .admin import AdAdmin
from .factories import (
    DEFAULT_PASSWORD,
    AdFactory,
    UserFactory,
    WishlistItemFactory,
)
from .forms import AdForm
from .models import Ad, WishlistItem

TEMP_MEDIA = tempfile.mkdtemp()


def make_image(name="test.jpg", size=(50, 50), noisy=False):
    """Build a real in-memory image file for upload tests."""
    image = Image.new("RGB", size, "blue")
    if noisy:
        pixels = size[0] * size[1]
        image.putdata(
            [(random.randint(0, 255),) * 3 for _ in range(pixels)]
        )
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=100)
    return SimpleUploadedFile(
        name, buffer.getvalue(), content_type="image/jpeg"
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdModelTests(TestCase):
    def test_str_is_the_title(self):
        ad = AdFactory(title="Bike for sale")
        self.assertEqual(str(ad), "Bike for sale")

    def test_ads_are_ordered_newest_first(self):
        first = AdFactory()
        second = AdFactory()
        self.assertEqual(
            list(Ad.available_objects.all()), [second, first]
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdFormTests(TestCase):
    def valid_data(self, **overrides):
        data = {
            "title": "A good desk",
            "text": "Barely used.",
            "phone_number": "+37455667788",
            "price": "120.00",
            "type": Ad.Type.PRIVATE,
            "status": Ad.Status.ACTIVE,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = AdForm(data=self.valid_data(), files={"image": make_image()})
        self.assertTrue(form.is_valid(), form.errors)

    def test_title_longer_than_100_is_rejected(self):
        form = AdForm(
            data=self.valid_data(title="x" * 101),
            files={"image": make_image()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_invalid_phone_number_is_rejected(self):
        form = AdForm(
            data=self.valid_data(phone_number="not-a-phone"),
            files={"image": make_image()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_image_larger_than_1mb_is_rejected(self):
        big = make_image(size=(1800, 1800), noisy=True)
        self.assertGreater(big.size, 1024 * 1024)
        form = AdForm(data=self.valid_data(), files={"image": big})
        self.assertFalse(form.is_valid())
        self.assertIn("Image must be 1MB or smaller.", form.errors["image"])

    def test_blocked_is_not_offered_as_a_status(self):
        choices = dict(AdForm().fields["status"].choices)
        self.assertNotIn(Ad.Status.BLOCKED, choices)
        self.assertIn(Ad.Status.ACTIVE, choices)
        self.assertIn(Ad.Status.DEACTIVATED, choices)

    def test_owner_cannot_block_their_own_ad(self):
        form = AdForm(
            data=self.valid_data(status=Ad.Status.BLOCKED),
            files={"image": make_image()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdListViewTests(TestCase):
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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdDetailViewTests(TestCase):
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
        self.client.login(username=user.username, password=DEFAULT_PASSWORD)

        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertFalse(response.context["in_wishlist"])

        WishlistItemFactory(user=user, ad=ad)
        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertTrue(response.context["in_wishlist"])


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdCreateViewTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("ads:ad-create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_logged_in_user_can_create_an_ad(self):
        user = UserFactory()
        self.client.login(username=user.username, password=DEFAULT_PASSWORD)
        response = self.client.post(
            reverse("ads:ad-create"),
            {
                "title": "Guitar",
                "text": "Acoustic, good condition.",
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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class WishlistTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.ad = AdFactory()
        self.client.login(
            username=self.user.username, password=DEFAULT_PASSWORD
        )

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

    def test_get_request_is_not_allowed(self):
        response = self.client.get(
            reverse("ads:wishlist-add", args=[self.ad.pk])
        )
        self.assertEqual(response.status_code, 405)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class MyAdsViewTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.login(
            username=self.user.username, password=DEFAULT_PASSWORD
        )

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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class SoftDeleteTests(TestCase):
    def test_delete_marks_the_ad_as_removed(self):
        ad = AdFactory()
        ad.delete()
        ad.refresh_from_db()
        self.assertTrue(ad.is_removed)
        self.assertTrue(Ad.all_objects.filter(pk=ad.pk).exists())

    def test_removed_ads_are_hidden_from_available_objects(self):
        kept = AdFactory()
        gone = AdFactory()
        gone.delete()
        self.assertEqual(list(Ad.available_objects.all()), [kept])
        self.assertEqual(Ad.all_objects.count(), 2)

    def test_queryset_delete_is_also_soft(self):
        AdFactory()
        AdFactory()
        Ad.available_objects.all().delete()
        self.assertEqual(Ad.available_objects.count(), 0)
        self.assertEqual(Ad.all_objects.count(), 2)

    def test_hard_delete_is_still_possible(self):
        ad = AdFactory()
        ad.delete(soft=False)
        self.assertEqual(Ad.all_objects.count(), 0)

    def test_removed_ad_is_not_listed(self):
        kept = AdFactory()
        gone = AdFactory()
        gone.delete()
        response = self.client.get(reverse("ads:ad-list"))
        self.assertEqual(list(response.context["ads"]), [kept])

    def test_removed_ad_detail_returns_404(self):
        ad = AdFactory()
        ad.delete()
        response = self.client.get(reverse("ads:ad-detail", args=[ad.pk]))
        self.assertEqual(response.status_code, 404)

    def test_related_access_still_works_for_removed_ads(self):
        item = WishlistItemFactory()
        item.ad.delete()
        item.refresh_from_db()
        self.assertTrue(item.ad.is_removed)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class SoftDeletedWishlistTests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.ad = AdFactory()
        self.client.login(
            username=self.user.username, password=DEFAULT_PASSWORD
        )

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


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AdminSoftDeleteTests(TestCase):
    def setUp(self):
        self.admin = AdAdmin(Ad, AdminSite())

    def test_admin_queryset_includes_removed_ads(self):
        ad = AdFactory()
        ad.delete()
        self.assertIn(ad, self.admin.get_queryset(None))

    def test_admin_bulk_delete_is_soft(self):
        AdFactory()
        AdFactory()
        self.admin.get_queryset(None).delete()
        self.assertEqual(Ad.available_objects.count(), 0)
        self.assertEqual(Ad.all_objects.count(), 2)

    def test_admin_can_restore_a_removed_ad(self):
        ad = AdFactory()
        ad.delete()
        self.admin.restore(None, Ad.all_objects.filter(pk=ad.pk))
        ad.refresh_from_db()
        self.assertFalse(ad.is_removed)

    def test_admin_changelist_shows_removed_ads(self):
        User.objects.create_superuser("boss", "boss@example.com", "pw12345!")
        ad = AdFactory()
        ad.delete()
        self.client.login(username="boss", password="pw12345!")
        response = self.client.get("/admin/ads/ad/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ad.title)


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
