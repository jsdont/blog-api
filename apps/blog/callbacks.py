import json

from django.db.models import Count
from django.http import HttpRequest
from django.urls import reverse

from apps.auths.models import User
from apps.blog.models import Category, Comment, Post
from settings.conf import ENV_ID

TOP_AUTHORS = 5
PERCENT = 100


def environment(request: HttpRequest) -> list[str]:
    return ["Local", "warning"] if ENV_ID == "local" else ["Production", "danger"]


def drafts(request: HttpRequest) -> str:
    return str(Post.objects.filter(status="draft").count())


def item(title: str, icon: str, url: str) -> dict:
    return dict(title=title, icon=icon, link=reverse("admin:" + url))


def navigation(request: HttpRequest) -> list[dict]:
    posts = item("Posts", "article", "blog_post_changelist")
    posts["badge"] = "apps.blog.callbacks.drafts"
    groups = [
        dict(title="Overview", items=[item("Dashboard", "dashboard", "index")]),
        dict(
            title="Content",
            items=[
                posts,
                item("Comments", "comment", "blog_comment_changelist"),
                item("Categories", "folder", "blog_category_changelist"),
                item("Tags", "sell", "blog_tag_changelist"),
            ],
        ),
    ]
    if request.user.is_superuser:
        groups.append(
            dict(
                title="Users & Access",
                items=[
                    item("Users", "person", "auths_user_changelist"),
                    item("Groups", "group", "auth_group_changelist"),
                ],
            )
        )
    return groups


def tabs(request: HttpRequest) -> list[dict]:
    url = reverse("admin:blog_post_changelist")
    items = []
    for title, status in [("All", ""), ("Published", "published"), ("Drafts", "draft")]:
        items.append(
            dict(
                title=title,
                link=url + ("?status__exact=" + status if status else ""),
                active=request.GET.get("status__exact", "") == status,
            )
        )
    return [dict(models=["blog.post"], items=items)]


def dashboard(request: HttpRequest, context: dict) -> dict:
    published = Post.objects.filter(status="published").count()
    drafts = Post.objects.filter(status="draft").count()
    categories = Category.objects.annotate(total=Count("posts")).order_by("name")
    authors = User.objects.annotate(total=Count("posts")).order_by("-total", "email")
    progress = []
    for title, count in [("Published", published), ("Drafts", drafts)]:
        share = round(PERCENT * count / (published + drafts or 1))
        progress.append(dict(title=title, value=share, description=f"{share}%"))
    context.update(
        cards=[
            ("Users", User.objects.count()),
            ("Published posts", published),
            ("Drafts", drafts),
            ("Comments", Comment.objects.count()),
        ],
        chart=json.dumps(
            dict(
                labels=[c.name for c in categories] + ["Without category"],
                datasets=[
                    dict(
                        label="Posts",
                        backgroundColor="#2563eb",
                        data=[c.total for c in categories]
                        + [Post.objects.filter(category=None).count()],
                    )
                ],
            )
        ),
        chart_options=json.dumps(
            dict(
                maintainAspectRatio=False,
                scales=dict(y=dict(display=True, beginAtZero=True)),
            )
        ),
        table=dict(
            headers=["Author", "Posts"],
            rows=[[u.email, u.total] for u in authors[:TOP_AUTHORS]],
        ),
        progress=progress,
    )
    return context
