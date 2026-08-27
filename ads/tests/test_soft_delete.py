from django.urls import reverse

from ads.factories import AdFactory, WishlistItemFactory
from ads.models import Ad

from .base import MediaTestCase


class SoftDeleteTests(MediaTestCase):
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
