from random import choice, randint, random, sample
from time import perf_counter
from typing import Any

from faker import Faker

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.utils.text import slugify

from apps.auths.constants import NAME_MAX_LENGTH
from apps.auths.models import User
from apps.blog.constants import POST_TITLE_MAX_LENGTH, SLUG_MAX_LENGTH
from apps.blog.models import Category, Comment, Post, Tag

DEFAULTS = {"users": 20, "posts": 100, "comments": 500}
SEED_PASSWORD = "BlogSeed2026!"
EMAIL_DOMAIN = "@example.com"
EMAIL_LOCAL_LIMIT = 64
INACTIVE_SHARE = STAFF_SHARE = 0.1
PUBLISHED_SHARE = 0.7
NO_CATEGORY_SHARE = 0.1
POST_PARAGRAPHS = 3
TAG_MIN, TAG_MAX = 0, 5
SENTENCE_RANGE = (1, 3)
FIRST_SUFFIX = 2
CATEGORY_NAMES = (
    "Python Django DevOps Databases Frontend Testing Security Career".split()
)
TAG_NAMES = (
    "Python Django REST PostgreSQL SQLite Docker Git Linux JavaScript HTML CSS "
    "Testing Pytest Security Authentication Performance Deployment Tutorial "
    "Beginners Practices"
).split()


def unique(base: str, used: set[str], limit: int, tail: str = "") -> str:
    base = base[:limit]
    value = base + tail
    number = FIRST_SUFFIX
    while value in used:
        suffix = f"-{number}"
        value = base[: limit - len(suffix)] + suffix + tail
        number += 1
    used.add(value)
    return value


class Command(BaseCommand):
    help = "Fill the database with fake data."

    def add_arguments(self, parser: CommandParser) -> None:
        for name, count in DEFAULTS.items():
            parser.add_argument(
                f"--{name}", type=int, default=count, help=f"Number of {name}"
            )
        parser.add_argument("--clear", action="store_true", help="Delete old data")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        start = perf_counter()
        counts = {name: options[name] for name in DEFAULTS}
        if min(counts.values()) < 0:
            raise CommandError("Counts must be zero or greater.")
        if options["clear"]:
            for model in (Comment, Post, Tag, Category):
                model.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        fake = Faker()
        emails = {
            email.lower() for email in User.objects.values_list("email", flat=True)
        }
        password = make_password(SEED_PASSWORD)
        users = []
        for index in range(counts["users"]):
            first = fake.first_name()[:NAME_MAX_LENGTH]
            last = fake.last_name()[:NAME_MAX_LENGTH]
            email = unique(
                slugify(f"{first}-{last}") or "user",
                emails,
                EMAIL_LOCAL_LIMIT,
                EMAIL_DOMAIN,
            )
            user = User(
                email=email,
                first_name=first,
                last_name=last,
                password=password,
                is_active=index >= counts["users"] * INACTIVE_SHARE,
                is_staff=index >= (counts["users"] - 1) * (1 - STAFF_SHARE),
            )
            users.append(user)
        User.objects.bulk_create(users)
        users = list(User.objects.all())
        if (counts["posts"] or counts["comments"]) and not users:
            raise CommandError("Posts and comments require users.")

        for model, names in ((Category, CATEGORY_NAMES), (Tag, TAG_NAMES)):
            before = model.objects.count()
            model.objects.bulk_create(
                (model(name=name, slug=slugify(name)) for name in names),
                ignore_conflicts=True,
            )
            counts["categories" if model is Category else "tags"] = (
                model.objects.count() - before
            )

        categories = list(Category.objects.all())
        tags = list(Tag.objects.all())
        slugs = set(Post.objects.values_list("slug", flat=True))
        posts = []
        for _ in range(counts["posts"]):
            title = fake.sentence()[:POST_TITLE_MAX_LENGTH]
            post = Post(
                author=choice(users),
                title=title,
                slug=unique(slugify(title) or "post", slugs, SLUG_MAX_LENGTH),
                body="\n\n".join(fake.paragraphs(nb=POST_PARAGRAPHS)),
                category=choice(categories) if random() >= NO_CATEGORY_SHARE else None,
                status="published" if random() < PUBLISHED_SHARE else "draft",
            )
            posts.append(post)
        Post.objects.bulk_create(posts)

        for post in posts:
            post.tags.set(sample(tags, randint(TAG_MIN, min(TAG_MAX, len(tags)))))

        published = list(Post.objects.filter(status="published"))
        if counts["comments"] and not published:
            raise CommandError("Comments require published posts.")
        Comment.objects.bulk_create(
            Comment(
                post=choice(published),
                author=choice(users),
                body=" ".join(fake.sentences(nb=randint(*SENTENCE_RANGE))),
            )
            for _ in range(counts["comments"])
        )
        for name, count in counts.items():
            self.stdout.write(f"{name.title()}: {count} created")
        self.stdout.write(
            self.style.SUCCESS(f"Done in {perf_counter() - start:.2f} seconds")
        )
