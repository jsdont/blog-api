from rest_framework import serializers

from apps.blog.constants import (
    COMMENT_POST_CANNOT_CHANGE,
    PUBLISHED_POST_REQUIRED,
)
from apps.blog.models import Category, Comment, Post, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "tags",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("author", "created_at", "updated_at")


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "post", "author", "body", "created_at")
        read_only_fields = ("author", "created_at")

    def validate_post(self, post: Post) -> Post:
        if post.status != Post.Status.PUBLISHED:
            raise serializers.ValidationError(PUBLISHED_POST_REQUIRED)
        if self.instance and self.instance.post_id != post.pk:
            raise serializers.ValidationError(COMMENT_POST_CANNOT_CHANGE)
        return post
