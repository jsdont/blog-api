from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from django.db.models import Q, QuerySet

from apps.blog.models import Category, Comment, Post, Tag
from apps.blog.permissions import IsAuthorOrReadOnly, IsStaffOrReadOnly
from apps.blog.serializers import (
    CategorySerializer,
    CommentSerializer,
    PostSerializer,
    TagSerializer,
)


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = (IsStaffOrReadOnly,)


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsStaffOrReadOnly,)


class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def get_queryset(self) -> QuerySet[Post]:
        visible = Q(status=Post.Status.PUBLISHED)
        if self.request.user.is_authenticated:
            visible |= Q(author=self.request.user)
        return Post.objects.filter(visible)

    def perform_create(self, serializer: PostSerializer) -> None:
        serializer.save(author=self.request.user)


class CommentViewSet(ModelViewSet):
    queryset = Comment.objects.filter(post__status=Post.Status.PUBLISHED)
    serializer_class = CommentSerializer
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def perform_create(self, serializer: CommentSerializer) -> None:
        serializer.save(author=self.request.user)
