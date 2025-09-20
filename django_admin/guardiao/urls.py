from django.urls import path
from . import views

app_name = 'guardiao'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('estatisticas/', views.estatisticas, name='estatisticas'),
    path('denuncias/<int:denuncia_id>/', views.detalhes_denuncia, name='detalhes_denuncia'),
    path('discord-login/', views.discord_login, name='discord_login'),
    path('discord-callback/', views.discord_callback, name='discord_callback'),
]
