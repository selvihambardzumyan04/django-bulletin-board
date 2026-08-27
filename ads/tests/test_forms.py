from ads.factories import CategoryFactory
from ads.forms import AdForm
from ads.models import Ad, Category

from .base import MediaTestCase, make_image


class AdFormDataMixin:
    def setUp(self):
        super().setUp()
        self.category = CategoryFactory(name="Bikes")

    def valid_data(self, **overrides):
        data = {
            "title": "A good desk",
            "text": "Barely used.",
            "category": self.category.pk,
            "phone_number": "+37455667788",
            "price": "120.00",
            "type": Ad.Type.PRIVATE,
            "status": Ad.Status.ACTIVE,
        }
        data.update(overrides)
        return {key: value for key, value in data.items() if value is not None}

    def build(self, image=None, **overrides):
        return AdForm(
            data=self.valid_data(**overrides),
            files={"image": image or make_image()},
        )

    def assertRejects(self, field, **overrides):
        form = self.build(**overrides)
        self.assertFalse(form.is_valid())
        self.assertIn(field, form.errors)
        return form


class AdFormTests(AdFormDataMixin, MediaTestCase):
    def test_valid_form(self):
        form = self.build()
        self.assertTrue(form.is_valid(), form.errors)

    def test_title_longer_than_100_is_rejected(self):
        self.assertRejects("title", title="x" * 101)

    def test_invalid_phone_number_is_rejected(self):
        self.assertRejects("phone_number", phone_number="not-a-phone")

    def test_image_larger_than_1mb_is_rejected(self):
        big = make_image(size=(1800, 1800), noisy=True)
        self.assertGreater(big.size, 1024 * 1024)
        form = self.build(image=big)
        self.assertFalse(form.is_valid())
        self.assertIn("Image must be 1MB or smaller.", form.errors["image"])

    def test_image_is_required(self):
        form = AdForm(data=self.valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)


class AdFormStatusTests(MediaTestCase):
    def test_blocked_is_not_offered_as_a_status(self):
        choices = dict(AdForm().fields["status"].choices)
        self.assertNotIn(Ad.Status.BLOCKED, choices)
        self.assertIn(Ad.Status.ACTIVE, choices)
        self.assertIn(Ad.Status.DEACTIVATED, choices)

    def test_owner_cannot_block_their_own_ad(self):
        category = CategoryFactory(name="Bikes")
        form = AdForm(
            data={
                "title": "A bike",
                "text": "Fast.",
                "category": category.pk,
                "phone_number": "+37455667788",
                "price": "50.00",
                "type": Ad.Type.PRIVATE,
                "status": Ad.Status.BLOCKED,
            },
            files={"image": make_image()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("status", form.errors)


class AdFormCategoryTests(AdFormDataMixin, MediaTestCase):
    def setUp(self):
        super().setUp()
        self.hidden = CategoryFactory(name="Retired", hidden=True)

    def test_only_active_categories_are_offered(self):
        choices = list(AdForm().fields["category"].queryset)
        self.assertIn(self.category, choices)
        self.assertNotIn(self.hidden, choices)

    def test_active_category_is_accepted(self):
        form = self.build(category=self.category.pk)
        self.assertTrue(form.is_valid(), form.errors)

    def test_hidden_category_is_rejected(self):
        self.assertRejects("category", category=self.hidden.pk)

    def test_category_is_required(self):
        self.assertRejects("category", category=None)

    def test_hidden_categories_reappear_when_reactivated(self):
        self.hidden.status = Category.Status.ACTIVE
        self.hidden.save()
        self.assertIn(
            self.hidden, list(AdForm().fields["category"].queryset)
        )
