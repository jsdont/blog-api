"""The fifty ORM exercises for Homework 3."""

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import (
    Avg,
    Case,
    Count,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat, Round, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post, Tag

NEWEST_LIMIT = TOP_AUTHORS_LIMIT = 5
PAGE_SIZE = 10
EDITED_AFTER = timedelta(hours=1)
AVERAGE_DIGITS = 2
HOT_COMMENTS = 10
NORMAL_COMMENTS = 3
HOT, NORMAL, QUIET = "hot", "normal", "quiet"
UNCATEGORIZED = "Uncategorized"
FULL_NAME_SEPARATOR = " "
FEED_LIMIT = 50
TAGGED_POSTS_LIMIT = 20


# Level 1: basic queries.
def categories_by_name() -> QuerySet[Category]:
    """Return all categories in alphabetical order."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Return published posts, newest first."""
    return Post.objects.filter(status=Post.Status.PUBLISHED).order_by(
        "-created_at", "-pk"
    )


def newest_published_posts() -> QuerySet[Post]:
    """Return the five newest published posts."""
    return published_posts()[:NEWEST_LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """Find a post by slug, returning None when absent."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Count active users who are not staff."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """Check whether any draft exists."""
    return Post.objects.filter(status=Post.Status.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Return a one-based page of published posts."""
    if page < 1:
        raise ValueError("Page must be at least 1.")
    start = (page - 1) * PAGE_SIZE
    return published_posts()[start : start + PAGE_SIZE]


# Level 2: field lookups.
def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Find titles containing the word, ignoring case."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Find users with the given email domain."""
    return User.objects.filter(email__iendswith="@" + domain)


def posts_without_category() -> QuerySet[Post]:
    """Return posts with no category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Return categories whose slugs appear in the list."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Return posts created in the specified year and month."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Return posts created during the last given number of days."""
    return Post.objects.filter(created_at__gte=timezone.now() - timedelta(days=days))


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Include both boundary dates when filtering creation dates."""
    return Post.objects.filter(created_at__date__range=(start, end))


# Level 3: relations.
def author_published_posts(email: str) -> QuerySet[Post]:
    """Return an author's published posts, matching email without case."""
    return published_posts().filter(author__email__iexact=email)


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Return posts carrying the specified tag."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Return comments under posts in the category."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Return each author of a published post once."""
    return User.objects.filter(posts__status=Post.Status.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Return posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Return users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Require both tags rather than either of them."""
    return (
        Post.objects.filter(tags__slug=first_slug)
        .filter(tags__slug=second_slug)
        .distinct()
    )


# Level 4: Q and F expressions.
def search_posts(text: str) -> QuerySet[Post]:
    """Search both title and body without case sensitivity."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """Return unique published posts missing a category or tags."""
    return (
        published_posts()
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """Return posts edited more than an hour after creation."""
    return Post.objects.filter(updated_at__gt=F("created_at") + EDITED_AFTER)


def comments_by_post_author() -> QuerySet[Comment]:
    """Return comments written by the author of their post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]:
    """Find comments whose dates incorrectly precede their post."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


# Level 5: selected columns.
def published_authors_emails() -> list[str]:
    """Return unique published-author emails in alphabetical order."""
    return list(
        User.objects.filter(posts__status=Post.Status.PUBLISHED)
        .order_by("email")
        .values_list("email", flat=True)
        .distinct()
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """Return three selected columns with a fallback category name."""
    return list(
        published_posts().values(
            "title",
            author_email=F("author__email"),
            category_name=Coalesce("category__name", Value(UNCATEGORIZED)),
        )
    )


# Level 6: aggregation.
def posts_stats() -> dict[str, Any]:
    """Calculate post counts and date boundaries in one query."""
    return Post.objects.aggregate(
        total=Count("pk"),
        published=Count("pk", filter=Q(status=Post.Status.PUBLISHED)),
        drafts=Count("pk", filter=Q(status=Post.Status.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """Average published-post comment counts, including zero counts."""
    result = (
        published_posts()
        .annotate(comment_count=Count("comments"))
        .aggregate(
            average=Round(Avg("comment_count", default=0.0), precision=AVERAGE_DIGITS)
        )
    )
    return float(result["average"])


# Level 7: annotations.
def categories_with_post_count() -> QuerySet[Category]:
    """Annotate all categories with their total post counts."""
    return Category.objects.annotate(post_count=Count("posts")).order_by(
        "-post_count", "name"
    )


def categories_with_published_count() -> QuerySet[Category]:
    """Count published posts without excluding empty categories."""
    return Category.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    )


def top_authors() -> QuerySet[User]:
    """Return the five users with the most published posts."""
    return User.objects.annotate(
        published_count=Count("posts", filter=Q(posts__status=Post.Status.PUBLISHED))
    ).order_by("-published_count", "email")[:TOP_AUTHORS_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Return tags whose post count reaches the given minimum."""
    return Tag.objects.annotate(post_count=Count("posts")).filter(
        post_count__gte=min_posts
    )


def posts_per_status() -> list[dict[str, Any]]:
    """Count posts grouped by status."""
    return list(
        Post.objects.values("status").annotate(count=Count("pk")).order_by("status")
    )


def users_activity() -> QuerySet[User]:
    """Count posts and comments independently for each user."""
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
    )


# Level 8: database functions and conditions.
def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Search a full name assembled by the database."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(FULL_NAME_SEPARATOR), "last_name")
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """Count published posts per month, oldest month first."""
    return list(
        published_posts()
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("pk"))
        .order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Annotate comment counts and their popularity labels."""
    return Post.objects.annotate(comment_count=Count("comments")).annotate(
        popularity=Case(
            When(comment_count__gte=HOT_COMMENTS, then=Value(HOT)),
            When(comment_count__gte=NORMAL_COMMENTS, then=Value(NORMAL)),
            default=Value(QUIET),
        )
    )


# Level 9: data changes (only run explicitly).
def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    """Reuse a tag with the same normalized slug, or create it."""
    return Tag.objects.get_or_create(slug=slugify(name), defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    """Publish old drafts and update their edit dates in one query."""
    now = timezone.now()
    return Post.objects.filter(
        status=Post.Status.DRAFT, created_at__lt=now - timedelta(days=days)
    ).update(status=Post.Status.PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    """Add a tag to every category post without duplicate relations."""
    tag = Tag.objects.get(slug=tag_slug)
    posts = Post.objects.filter(category__slug=category_slug)
    count = posts.count()
    tag.posts.add(*posts.values_list("pk", flat=True))
    return count


@transaction.atomic
def merge_categories(source_slug: str, target_slug: str) -> int:
    """Move source posts before deleting the source category."""
    if source_slug == target_slug:
        return 0
    source = Category.objects.get(slug=source_slug)
    target = Category.objects.get(slug=target_slug)
    count = source.posts.update(category=target)
    source.delete()
    return count


def delete_inactive_users_comments() -> int:
    """Delete comments authored by inactive users."""
    _, counts = Comment.objects.filter(author__is_active=False).delete()
    return counts.get(Comment._meta.label, 0)


# Level 10: eager loading and formatted output.
def published_feed() -> list[str]:
    """Build a feed with authors and categories loaded in one query."""
    posts = published_posts().select_related("author", "category")[:FEED_LIMIT]
    return [
        f"{post.title} | {post.author.email} | "
        f"{post.category.name if post.category else UNCATEGORIZED}"
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    """Build tagged post lines with at most two queries."""
    posts = Post.objects.order_by("-created_at", "-pk").prefetch_related("tags")[
        :TAGGED_POSTS_LIMIT
    ]
    return [
        f"{post.title}: {', '.join(tag.name for tag in post.tags.all())}"
        for post in posts
    ]


def categories_with_published_posts() -> dict[str, list[str]]:
    """Map every category to its newest-first published titles."""
    categories = Category.objects.prefetch_related(
        Prefetch("posts", queryset=published_posts(), to_attr="published_list")
    )
    return {
        category.name: [post.title for post in category.published_list]
        for category in categories
    }


# Level 11: subqueries.
def posts_with_last_comment() -> QuerySet[Post]:
    """Annotate published posts with their newest comment body."""
    comments = Comment.objects.filter(post=OuterRef("pk")).order_by(
        "-created_at", "-pk"
    )
    return published_posts().annotate(
        last_comment=Subquery(comments.values("body")[:1])
    )


def posts_with_staff_comments() -> QuerySet[Post]:
    """Use EXISTS to find posts commented on by staff."""
    comments = Comment.objects.filter(post=OuterRef("pk"), author__is_staff=True)
    return Post.objects.filter(Exists(comments))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    """Find users whose newest post is a draft."""
    posts = Post.objects.filter(author=OuterRef("pk")).order_by("-created_at", "-pk")
    return User.objects.annotate(
        latest_post_status=Subquery(posts.values("status")[:1])
    ).filter(latest_post_status=Post.Status.DRAFT)


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}
