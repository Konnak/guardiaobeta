from django.urls import path
from . import views

app_name = 'guardiao'

urlpatterns = [
    path('discord-login/', views.discord_login, name='discord_login'),
    path('discord-callback/', views.discord_callback, name='discord_callback'),
]
