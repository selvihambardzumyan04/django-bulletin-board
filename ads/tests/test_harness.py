import tempfile

from django.conf import settings
from django.contrib.auth.hashers import get_hasher

from ads.factories import (
    DEFAULT_PASSWORD,
    AdFactory,
    CategoryFactory,
    UserFactory,
)

from .base import MediaTestCase


class HarnessTests(MediaTestCase):
    def test_media_root_is_a_temporary_directory(self):
        self.assertEqual(settings.MEDIA_ROOT, self.media_root)
        self.assertTrue(
            settings.MEDIA_ROOT.startswith(tempfile.gettempdir())
        )

    def test_uploads_stay_out_of_the_project_media_directory(self):
        ad = AdFactory()
        self.assertTrue(ad.image.path.startswith(self.media_root))

    def test_password_hashing_is_fast(self):
        self.assertEqual(get_hasher().algorithm, "md5")

    def test_login_helper_authenticates(self):
        user = self.login(UserFactory())
        self.assertEqual(
            int(self.client.session["_auth_user_id"]), user.pk
        )


class FactoryTests(MediaTestCase):
    def test_category_slug_follows_the_name(self):
        category = CategoryFactory(name="Home & Garden")
        self.assertEqual(category.slug, "home-garden")

    def test_category_hidden_trait(self):
        self.assertEqual(CategoryFactory(hidden=True).status, "hidden")

    def test_ad_status_traits(self):
        self.assertEqual(AdFactory(blocked=True).status, "blocked")
        self.assertEqual(
            AdFactory(deactivated=True).status, "deactivated"
        )

    def test_ad_removed_trait(self):
        ad = AdFactory(removed=True)
        self.assertTrue(ad.is_removed)
        self.assertFalse(
            AdFactory._meta.model.available_objects.filter(
                pk=ad.pk
            ).exists()
        )

    def test_ad_wishlisted_hook(self):
        ad = AdFactory(wishlisted=3)
        self.assertEqual(ad.wishlisted_by.count(), 3)

    def test_user_traits(self):
        self.assertTrue(UserFactory(staff=True).is_staff)
        superuser = UserFactory(superuser=True)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

    def test_users_get_a_usable_password(self):
        user = UserFactory()
        self.assertTrue(user.check_password(DEFAULT_PASSWORD))
