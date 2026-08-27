import factory
from django.contrib.auth.models import User

from .models import Ad, WishlistItem

DEFAULT_PASSWORD = "pass12345"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()


class AdFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ad

    @classmethod
    def _get_manager(cls, model_class):
        return model_class.available_objects

    owner = factory.SubFactory(UserFactory)
    phone_number = "+37455667788"
    title = factory.Sequence(lambda n: f"Ad number {n}")
    text = factory.Faker("paragraph")
    image = factory.django.ImageField(width=50, height=50, color="blue")
    type = Ad.Type.PRIVATE
    price = factory.Faker(
        "pydecimal", left_digits=4, right_digits=2, positive=True
    )
    status = Ad.Status.ACTIVE


class WishlistItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WishlistItem

    user = factory.SubFactory(UserFactory)
    ad = factory.SubFactory(AdFactory)
