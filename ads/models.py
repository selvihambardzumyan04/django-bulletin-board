from django.conf import settings
from django.db import models
from model_utils.managers import SoftDeletableQuerySet
from model_utils.models import SoftDeletableModel


class Ad(SoftDeletableModel):
    class Type(models.TextChoices):
        PRIVATE = "private", "Private"
        BUSINESS = "business", "Business"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DEACTIVATED = "deactivated", "Deactivated"
        BLOCKED = "blocked", "Blocked"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ads",
    )
    phone_number = models.CharField(max_length=20)
    title = models.CharField(max_length=100)
    text = models.TextField()
    image = models.ImageField(upload_to="ads/")
    type = models.CharField(
        max_length=10, choices=Type.choices, default=Type.PRIVATE
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )
    created = models.DateTimeField(auto_now_add=True)

    all_objects = models.Manager.from_queryset(SoftDeletableQuerySet)()

    class Meta:
        ordering = ["-created"]
        default_manager_name = "available_objects"

    def __str__(self):
        return self.title


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    ad = models.ForeignKey(
        Ad, on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "ad"], name="unique_wishlist_item"
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.ad}"
