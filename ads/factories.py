import factory
from django.contrib.auth.models import User
from django.utils.text import slugify

from .models import Ad, Category, WishlistItem

DEFAULT_PASSWORD = "pass12345"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    class Params:
        staff = factory.Trait(is_staff=True)
        superuser = factory.Trait(is_staff=True, is_superuser=True)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("slug",)

    class Params:
        hidden = factory.Trait(status=Category.Status.HIDDEN)

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.LazyAttribute(lambda category: slugify(category.name))
    status = Category.Status.ACTIVE


class AdFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ad
        skip_postgeneration_save = True

    class Params:
        deactivated = factory.Trait(status=Ad.Status.DEACTIVATED)
        blocked = factory.Trait(status=Ad.Status.BLOCKED)
        removed = factory.Trait(is_removed=True)

    @classmethod
    def _get_manager(cls, model_class):
        return model_class.available_objects

    owner = factory.SubFactory(UserFactory)
    category = factory.SubFactory(CategoryFactory)
    phone_number = "+37455667788"
    title = factory.Sequence(lambda n: f"Ad number {n}")
    text = factory.Faker("paragraph")
    image = factory.django.ImageField(width=50, height=50, color="blue")
    type = Ad.Type.PRIVATE
    price = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    status = Ad.Status.ACTIVE

    @factory.post_generation
    def wishlisted(self, create, extracted, **kwargs):
        if create and extracted:
            WishlistItemFactory.create_batch(extracted, ad=self)


class WishlistItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WishlistItem

    user = factory.SubFactory(UserFactory)
    ad = factory.SubFactory(AdFactory)
