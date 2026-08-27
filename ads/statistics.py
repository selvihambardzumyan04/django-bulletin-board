from django.db.models import Count, Min, Q
from django.utils import timezone

from .models import Ad, Category

DAYS_PER_WEEK = 7
DAYS_PER_MONTH = 30.44


def span_in_days(first_created):
    if first_created is None:
        return 0
    first_day = timezone.localtime(first_created).date()
    return (timezone.localdate() - first_day).days + 1


def category_counts():
    return Category.objects.annotate(
        post_count=Count("ads", filter=Q(ads__is_removed=False))
    ).order_by("-post_count", "name")


def post_statistics():
    posts = Ad.available_objects.all()
    totals = posts.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Ad.Status.ACTIVE)),
        deactivated=Count("id", filter=Q(status=Ad.Status.DEACTIVATED)),
        blocked=Count("id", filter=Q(status=Ad.Status.BLOCKED)),
        first_created=Min("created"),
    )
    span = span_in_days(totals["first_created"])
    per_day = totals["total"] / span if span else 0
    return {
        "total": totals["total"],
        "active": totals["active"],
        "deactivated": totals["deactivated"],
        "blocked": totals["blocked"],
        "deleted": Ad.all_objects.filter(is_removed=True).count(),
        "span_days": span,
        "per_day": round(per_day, 2),
        "per_week": round(per_day * DAYS_PER_WEEK, 2),
        "per_month": round(per_day * DAYS_PER_MONTH, 2),
        "categories": category_counts(),
    }
