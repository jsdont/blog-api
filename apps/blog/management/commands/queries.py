from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Count, Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.auths.models import User
from apps.blog.models import Category, Post, Tag
from apps.blog.queries import QUERIES

PREVIEW_ROWS = 5
MUTATING_QUERIES = {40, 41, 42, 43, 44}
SAMPLE_DAYS = 30
SAMPLE_HISTORY_DAYS = 365
PAIR_SIZE = 2


def sample_arguments() -> dict[int, dict[str, Any]]:
    """Pick examples before measuring the query functions themselves."""
    post = (
        Post.objects.filter(status=Post.Status.PUBLISHED)
        .select_related("author")
        .first()
    )
    user = post.author if post else User.objects.first()
    created = timezone.localtime(post.created_at) if post else timezone.localtime()
    word = post.title.split()[0] if post and post.title.split() else "Django"
    category = Category.objects.filter(posts__comments__isnull=False).first()
    tagged = (
        Post.objects.annotate(tag_count=Count("tags"))
        .filter(tag_count__gte=PAIR_SIZE)
        .first()
    )
    tags = (
        list(tagged.tags.values_list("slug", flat=True)[:PAIR_SIZE]) if tagged else []
    )
    tag = Tag.objects.filter(posts__isnull=False).first()
    today = timezone.localdate()
    return {
        4: {"slug": post.slug if post else "missing-post"},
        7: {"page": 1},
        8: {"word": word},
        9: {"domain": user.email.rsplit("@", 1)[-1] if user else "example.com"},
        11: {"slugs": ["python", "django"]},
        12: {"year": created.year, "month": created.month},
        13: {"days": SAMPLE_DAYS},
        14: {"start": today - timedelta(days=SAMPLE_HISTORY_DAYS), "end": today},
        15: {"email": user.email if user else "missing@example.com"},
        16: {"tag_slug": tag.slug if tag else "python"},
        17: {"category_slug": category.slug if category else "python"},
        21: {
            "first_slug": tags[0] if tags else "python",
            "second_slug": tags[1] if tags else "django",
        },
        22: {"text": word},
        34: {"min_posts": 1},
        37: {"text": user.first_name if user else "John"},
        40: {"name": "Django ORM"},
        41: {"days": SAMPLE_DAYS},
        42: {"category_slug": "python", "tag_slug": "django"},
        43: {"source_slug": "python", "target_slug": "django"},
    }


def render_row(row: Any, annotations: tuple[str, ...] = ()) -> str:
    """Include computed attributes beside the model's ordinary label."""
    if isinstance(row, Model) and annotations:
        extra = {name: getattr(row, name) for name in annotations}
        return f"{row} {extra}"
    return str(row)


def render_result(result: Any) -> list[str]:
    """Evaluate lazy rows and produce a short preview inside the SQL capture."""
    annotations: tuple[str, ...] = ()
    if isinstance(result, QuerySet):
        annotations = tuple(result.query.annotations)
        result = list(result)
    if isinstance(result, list):
        lines = [f"  {render_row(row, annotations)}" for row in result[:PREVIEW_ROWS]]
        return [*lines, f"  ({len(result)} rows)"]
    return [f"  {render_row(result)}"]


class Command(BaseCommand):
    help = "Run ORM homework queries; data changes require --number."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--number", type=int, help="Run one query by its number")
        parser.add_argument("--sql", action="store_true", help="Show executed SQL")

    def handle(self, *args: Any, **options: Any) -> None:
        number = options["number"]
        if number is not None and number not in QUERIES:
            raise CommandError(f"Unknown query number: {number}. Choose 1-50.")
        arguments = sample_arguments()
        numbers = (
            [number]
            if number is not None
            else [key for key in QUERIES if key not in MUTATING_QUERIES]
        )
        for current in numbers:
            function = QUERIES[current]
            with CaptureQueriesContext(connection) as context:
                result = function(**arguments.get(current, {}))
                lines = render_result(result)
            count = len(context.captured_queries)
            label = "query" if count == 1 else "queries"
            self.stdout.write(f"#{current} {function.__name__} - {count} SQL {label}")
            if options["sql"]:
                for query in context.captured_queries:
                    self.stdout.write(query["sql"])
            for line in lines:
                self.stdout.write(line)
