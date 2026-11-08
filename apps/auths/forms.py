from unfold.forms import UserChangeForm as DjangoUserChangeForm
from unfold.forms import UserCreationForm as DjangoUserCreationForm

from apps.auths.models import User


class UserCreationForm(DjangoUserCreationForm):
    usable_password = None

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = "__all__"
