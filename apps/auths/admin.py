from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from apps.auths.forms import UserChangeForm, UserCreationForm
from apps.auths.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("user_header", "active_label", "staff_label", "post_count")
    list_filter = (("is_active", BooleanRadioFilter), ("is_staff", BooleanRadioFilter))
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    actions = ("activate_users", "deactivate_users")
    fieldsets = [
        (title, {"classes": ("tab",), "fields": fields.split()})
        for title, fields in (
            ("Personal info", "email password first_name last_name"),
            ("Permissions", "is_active is_staff is_superuser groups user_permissions"),
            ("Important dates", "last_login"),
        )
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(post_total=Count("posts"))

    @display(description="User", header=True)
    def user_header(self, obj: User) -> tuple[str, str, str]:
        name = f"{obj.first_name} {obj.last_name}".strip()
        initials = f"{obj.first_name[:1]}{obj.last_name[:1]}".upper()
        return name or obj.email, obj.email, initials

    @display(description="Active", label={True: "success", False: "danger"})
    def active_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_active, "Active" if obj.is_active else "Inactive"

    @display(description="Staff", label={True: "info", False: "warning"})
    def staff_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_staff, "Staff" if obj.is_staff else "Regular"

    @display(description="Posts", ordering="post_total")
    def post_count(self, obj: User) -> int:
        return obj.post_total

    @action(description="Activate", permissions=["change"])
    def activate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(is_active=True)

    @action(description="Deactivate", permissions=["change"])
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(is_active=False)


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    pass
