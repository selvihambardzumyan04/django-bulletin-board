from django import forms
from django.core.validators import RegexValidator

from .models import Ad, Category

MAX_IMAGE_SIZE = 1 * 1024 * 1024

OWNER_STATUSES = (Ad.Status.ACTIVE, Ad.Status.DEACTIVATED)

phone_validator = RegexValidator(
    regex=r"^\+?\d{9,15}$",
    message="Enter a valid phone number, e.g. +37455667788",
)


class AdForm(forms.ModelForm):
    phone_number = forms.CharField(max_length=20, validators=[phone_validator])

    class Meta:
        model = Ad
        fields = (
            "title",
            "text",
            "category",
            "phone_number",
            "image",
            "type",
            "price",
            "status",
        )
        widgets = {"text": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(
            status=Category.Status.ACTIVE
        )
        self.fields["status"].choices = [
            (value, label)
            for value, label in Ad.Status.choices
            if value in OWNER_STATUSES
        ]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError("Image must be 1MB or smaller.")
        return image
