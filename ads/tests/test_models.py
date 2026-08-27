from django.db import IntegrityError, connection
from django.db.models import ProtectedError

from ads.factories import AdFactory, CategoryFactory, WishlistItemFactory
from ads.models import Ad, Category, WishlistItem

from .base import MediaTestCase


class AdModelTests(MediaTestCase):
    def test_str_is_the_title(self):
        ad = AdFactory(title="Bike for sale")
        self.assertEqual(str(ad), "Bike for sale")

    def test_ads_are_ordered_newest_first(self):
        first = AdFactory()
        second = AdFactory()
        self.assertEqual(
            list(Ad.available_objects.all()), [second, first]
        )


class CategoryModelTests(MediaTestCase):
    def test_str_is_the_name(self):
        category = CategoryFactory(name="Furniture")
        self.assertEqual(str(category), "Furniture")

    def test_default_status_is_active(self):
        self.assertEqual(CategoryFactory().status, Category.Status.ACTIVE)

    def test_categories_are_ordered_by_name(self):
        b = CategoryFactory(name="Bikes")
        a = CategoryFactory(name="Antiques")
        self.assertEqual(list(Category.objects.all()), [a, b])

    def test_duplicate_name_is_rejected(self):
        CategoryFactory(name="Books")
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Books", slug="other-books")

    def test_duplicate_slug_is_rejected(self):
        CategoryFactory(name="Books")
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Other books", slug="books")

    def test_name_and_slug_are_indexed(self):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor, Category._meta.db_table
            )
        indexed = {
            tuple(c["columns"])
            for c in constraints.values()
            if c["index"] or c["unique"]
        }
        self.assertIn(("name",), indexed)
        self.assertIn(("slug",), indexed)


class WishlistItemModelTests(MediaTestCase):
    def test_str_names_the_user_and_the_ad(self):
        item = WishlistItemFactory(ad__title="Bike for sale")
        self.assertEqual(str(item), f"{item.user} → Bike for sale")

    def test_items_are_ordered_newest_first(self):
        first = WishlistItemFactory()
        second = WishlistItemFactory(user=first.user)
        self.assertEqual(
            list(WishlistItem.objects.all()), [second, first]
        )


class CategoryDeletionTests(MediaTestCase):
    def setUp(self):
        self.category = CategoryFactory(name="Bikes")

    def test_category_with_ads_cannot_be_deleted(self):
        AdFactory(category=self.category)
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_unused_category_can_be_deleted(self):
        self.category.delete()
        self.assertFalse(
            Category.objects.filter(pk=self.category.pk).exists()
        )

    def test_deleting_a_category_leaves_its_ads_untouched(self):
        ad = AdFactory(category=self.category)
        with self.assertRaises(ProtectedError):
            self.category.delete()
        self.assertTrue(Ad.available_objects.filter(pk=ad.pk).exists())
