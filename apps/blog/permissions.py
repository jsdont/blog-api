from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.blog.models import Comment, Post


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(
        self, request: Request, view: APIView, obj: Post | Comment
    ) -> bool:
        return request.method in SAFE_METHODS or obj.author_id == request.user.pk


class IsStaffOrReadOnly(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in SAFE_METHODS or bool(request.user.is_staff)
