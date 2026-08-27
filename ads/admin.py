from django.contrib import admin

from .models import Ad, WishlistItem


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "price",
        "type",
        "status",
        "is_removed",
        "created",
    )
    list_filter = ("status", "type", "is_removed")
    search_fields = ("title", "text")
    actions = ("restore",)

    def get_queryset(self, request):
        return Ad.all_objects.all()

    @admin.action(description="Restore selected ads")
    def restore(self, request, queryset):
        queryset.update(is_removed=False)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "ad", "added")
