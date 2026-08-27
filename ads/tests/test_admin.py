from django.contrib.admin.sites import AdminSite

from ads.admin import AdAdmin
from ads.factories import AdFactory, UserFactory
from ads.models import Ad

from .base import MediaTestCase


class AdminSoftDeleteTests(MediaTestCase):
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
        self.login(UserFactory(username="boss", superuser=True))
        ad = AdFactory()
        ad.delete()
        response = self.client.get("/admin/ads/ad/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ad.title)
