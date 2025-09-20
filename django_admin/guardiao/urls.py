from django.urls import path
from . import views

app_name = 'guardiao'

urlpatterns = [
    # Discord OAuth2
    path('discord-login/', views.discord_login, name='discord_login'),
    path('discord-callback/', views.discord_callback, name='discord_callback'),
    
    # Rotas migradas do Flask
    path('dashboard/', views.dashboard, name='dashboard'),
    path('servers/', views.servers, name='servers'),
    path('server/<int:server_id>/', views.server_panel, name='server_panel'),
    path('premium/', views.premium, name='premium'),
    
    # API Endpoints migrados do Flask
    path('api/user/stats/', views.api_user_stats, name='api_user_stats'),
    path('api/server/<int:server_id>/stats/', views.api_server_stats, name='api_server_stats'),
    path('api/server/<int:server_id>/denuncias/', views.api_server_denuncias, name='api_server_denuncias'),
]
