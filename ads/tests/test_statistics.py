from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from ads.factories import AdFactory, CategoryFactory, UserFactory
from ads.models import Ad, Category
from ads.statistics import post_statistics

from .base import MediaTestCase


class StatisticsAccessTests(MediaTestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("ads:statistics"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_regular_user_is_forbidden(self):
        user = UserFactory()
        self.login(user)
        response = self.client.get(reverse("ads:statistics"))
        self.assertEqual(response.status_code, 403)

    def test_staff_user_is_allowed(self):
        staff = UserFactory(is_staff=True)
        self.login(staff)
        response = self.client.get(reverse("ads:statistics"))
        self.assertEqual(response.status_code, 200)

    def test_link_is_only_shown_to_staff(self):
        user = UserFactory()
        self.login(user)
        response = self.client.get(reverse("ads:ad-list"))
        self.assertNotContains(response, reverse("ads:statistics"))

        self.client.logout()
        staff = UserFactory(is_staff=True)
        self.login(staff)
        response = self.client.get(reverse("ads:ad-list"))
        self.assertContains(response, reverse("ads:statistics"))


class StatisticsTotalsTests(MediaTestCase):
    def test_counts_by_status(self):
        AdFactory.create_batch(3, status=Ad.Status.ACTIVE)
        AdFactory.create_batch(2, status=Ad.Status.DEACTIVATED)
        AdFactory(status=Ad.Status.BLOCKED)
        stats = post_statistics()
        self.assertEqual(stats["total"], 6)
        self.assertEqual(stats["active"], 3)
        self.assertEqual(stats["deactivated"], 2)
        self.assertEqual(stats["blocked"], 1)

    def test_deleted_posts_are_excluded_from_totals(self):
        AdFactory.create_batch(2)
        removed = AdFactory()
        removed.delete()
        stats = post_statistics()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["deleted"], 1)

    def test_counts_per_category(self):
        bikes = CategoryFactory(name="Bikes")
        books = CategoryFactory(name="Books")
        CategoryFactory(name="Empty")
        AdFactory.create_batch(2, category=bikes)
        AdFactory(category=books, status=Ad.Status.BLOCKED)
        removed = AdFactory(category=bikes)
        removed.delete()
        counts = {
            c.name: c.post_count for c in post_statistics()["categories"]
        }
        self.assertEqual(counts["Bikes"], 2)
        self.assertEqual(counts["Books"], 1)
        self.assertEqual(counts["Empty"], 0)

    def test_hidden_categories_are_still_reported(self):
        hidden = CategoryFactory(
            name="Retired", slug="retired", status=Category.Status.HIDDEN
        )
        AdFactory(category=hidden)
        counts = {
            c.name: c.post_count for c in post_statistics()["categories"]
        }
        self.assertEqual(counts["Retired"], 1)

    def test_totals_render_on_the_page(self):
        AdFactory.create_batch(2, status=Ad.Status.ACTIVE)
        staff = UserFactory(is_staff=True)
        self.login(staff)
        response = self.client.get(reverse("ads:statistics"))
        self.assertEqual(response.context["stats"]["total"], 2)
        self.assertContains(response, "Posts by category")


class StatisticsAveragesTests(MediaTestCase):
    def age_posts(self, ads, days):
        stamp = timezone.now() - timedelta(days=days)
        Ad.all_objects.filter(
            pk__in=[ad.pk for ad in ads]
        ).update(created=stamp)

    def test_no_posts_gives_zero_averages(self):
        stats = post_statistics()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["span_days"], 0)
        self.assertEqual(stats["per_day"], 0)
        self.assertEqual(stats["per_week"], 0)
        self.assertEqual(stats["per_month"], 0)

    def test_single_day_average(self):
        AdFactory.create_batch(4)
        stats = post_statistics()
        self.assertEqual(stats["span_days"], 1)
        self.assertEqual(stats["per_day"], 4.0)

    def test_average_spans_from_the_first_post(self):
        self.age_posts(AdFactory.create_batch(5), days=9)
        AdFactory.create_batch(5)
        stats = post_statistics()
        self.assertEqual(stats["span_days"], 10)
        self.assertEqual(stats["per_day"], 1.0)
        self.assertEqual(stats["per_week"], 7.0)
        self.assertEqual(stats["per_month"], 30.44)

    def test_deleted_posts_do_not_affect_averages(self):
        self.age_posts(AdFactory.create_batch(2), days=1)
        removed = AdFactory()
        removed.delete()
        stats = post_statistics()
        self.assertEqual(stats["span_days"], 2)
        self.assertEqual(stats["per_day"], 1.0)
