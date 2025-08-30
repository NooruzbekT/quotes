from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import register
from . import views_moderation
app_name = "quotes"

urlpatterns = [
    path("", views.home, name="home"),
    path("add/", views.add_quote, name="add"),
    path("top/", views.top10, name="top"),
    path("<int:pk>/react/", views.react, name="react"),
    path("register/", register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="quotes/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("moderation/queue/", views_moderation.queue, name="moderation_queue"),
    path("moderation/quotes/<int:pk>/approve/", views_moderation.approve_quote, name="moderation_quote_approve"),
    path("moderation/quotes/<int:pk>/reject/", views_moderation.reject_quote, name="moderation_quote_reject"),
    path("moderation/sources/<int:pk>/approve/", views_moderation.approve_source, name="moderation_source_approve"),
    path("moderation/sources/<int:pk>/reject/", views_moderation.reject_source, name="moderation_source_reject"),
    path("moderation/sources/<int:pk>/merge/", views_moderation.merge_source, name="moderation_source_merge"),
    path("moderation/users/", views_moderation.users, name="moderation_users"),
    path("moderation/tag/add/", views_moderation.add_tag, name="add_tag"),
]