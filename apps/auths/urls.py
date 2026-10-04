from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from django.urls import path

app_name = "auths"

urlpatterns = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
