from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display
from unfold.forms import BaseDialogForm
from unfold.sections import TableSection

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count, QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator

from apps.blog.models import Category, Comment, Post, Tag

COMMENT_PREVIEW_LENGTH = 80
COMMENTS_PER_PAGE = 10


class CategoryPostsSection(TableSection):
    related_name = "posts"
    fields = ("title", "status", "created_at")


class PostCommentsSection(TableSection):
    related_name = "comments"
    fields = ("author", "body", "created_at")


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ("name", "post_count")
    ordering = ("name",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(post_total=Count("posts"))

    @display(description="Posts", ordering="post_total")
    def post_count(self, obj: Tag | Category) -> int:
        return obj.post_total


@admin.register(Category)
class CategoryAdmin(TagAdmin):
    list_sections = (CategoryPostsSection,)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).prefetch_related("posts")


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ("post", "author", "body_preview", "created_at")
    list_filter = (
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("body", "author__email", "post__title")
    autocomplete_fields = ("post", "author")
    list_select_related = ("post", "author")

    @display(description="Comment")
    def body_preview(self, obj: Comment) -> str:
        return Truncator(obj.body).chars(COMMENT_PREVIEW_LENGTH)


class CommentInline(TabularInline):
    model = Comment
    tab = True
    per_page = COMMENTS_PER_PAGE
    extra = 0
    fields = ("author", "body", "created_at")
    autocomplete_fields = ("author",)
    readonly_fields = ("created_at",)
    ordering = ("pk",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).select_related("author")


@admin.register(Post)
class PostAdmin(ModelAdmin):
    ordering = ("-created_at", "-pk")
    list_display = (
        "post_header status_label category tags_dropdown comment_count created_at"
    ).split()
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    )
    list_filter_submit = True
    search_fields = ("title", "body", "author__email")
    list_sections = (PostCommentsSection,)
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("author", "category", "tags")
    readonly_fields = ("created_at", "updated_at")
    warn_unsaved_form = True
    inlines = (CommentInline,)
    formfield_overrides = {models.TextField: {"widget": WysiwygWidget}}
    fieldsets = [
        (title, {"classes": ("tab",), "fields": fields.split()})
        for title, fields in (
            ("Content", "title slug body"),
            ("Classification", "category tags status"),
            ("Meta", "author created_at updated_at"),
        )
    ]
    actions = ("publish_selected", "move_to_drafts")
    actions_row = ("publish_unpublish",)
    actions_list = ("publish_all_drafts",)
    actions_detail = ("open_comments",)
    actions_submit_line = ("save_and_publish",)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request).select_related("author", "category")
        return queryset.annotate(
            comment_total=Count("comments", distinct=True)
        ).prefetch_related("tags", "comments__author")

    @display(description="Post", header=True)
    def post_header(self, obj: Post) -> tuple[str, str]:
        return obj.title, obj.author.email

    @display(description="Status", label={"published": "success", "draft": "warning"})
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> dict:
        return {
            "title": "Tags",
            "items": [{"title": tag.name} for tag in obj.tags.all()],
        }

    @display(description="Comments", ordering="comment_total")
    def comment_count(self, obj: Post) -> int:
        return obj.comment_total

    @action(description="Publish selected", permissions=["change"])
    def publish_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(status="published", updated_at=timezone.now())

    @action(description="Move to drafts", permissions=["change"])
    def move_to_drafts(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(status="draft", updated_at=timezone.now())

    @action(
        description="Publish / unpublish",
        permissions=["change"],
        dialog={"title": "Switch publication status?"},
    )
    def publish_unpublish(
        self,
        request: HttpRequest,
        form: BaseDialogForm,
        object_id: str,
    ) -> HttpResponse:
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404
        if not self.has_change_permission(request, obj):
            raise PermissionDenied
        obj.status = "draft" if obj.status == "published" else "published"
        obj.save(update_fields=("status", "updated_at"))
        return HttpResponse(
            headers={"HX-Redirect": reverse("admin:blog_post_changelist")}
        )

    @action(
        description="Publish all drafts",
        permissions=["change"],
        dialog={"title": "Publish all drafts?"},
    )
    def publish_all_drafts(
        self,
        request: HttpRequest,
        form: BaseDialogForm,
    ) -> HttpResponse:
        self.publish_selected(
            request, self.get_queryset(request).filter(status="draft")
        )
        return HttpResponse(
            headers={"HX-Redirect": reverse("admin:blog_post_changelist")}
        )

    @action(description="Open comments", permissions=["view_comments"])
    def open_comments(self, request: HttpRequest, object_id: str) -> HttpResponse:
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404
        return redirect(
            f"{reverse('admin:blog_comment_changelist')}?post__id__exact={obj.pk}"
        )

    def has_view_comments_permission(
        self,
        request: HttpRequest,
        object_id: str | None = None,
    ) -> bool:
        return request.user.has_perm("blog.view_comment") or request.user.has_perm(
            "blog.change_comment"
        )

    @action(description="Save & publish", permissions=["change"])
    def save_and_publish(self, request: HttpRequest, obj: Post) -> None:
        obj.status = "published"
        obj.save(update_fields=("status", "updated_at"))
