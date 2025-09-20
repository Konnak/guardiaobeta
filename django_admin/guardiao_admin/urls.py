"""
URL configuration for guardiao_admin project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.admin import AdminSite
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

# Customize admin site
admin.site.site_header = "Guardião BETA - Painel Administrativo"
admin.site.site_title = "Guardião BETA Admin"
admin.site.index_title = "Bem-vindo ao Painel de Administração do Guardião BETA"

def home_page(request):
    """Página inicial do site"""
    from django.shortcuts import render
    
    # Verifica se é o admin autorizado (você pode implementar lógica de sessão aqui)
    # Por enquanto, sempre mostra o botão Admin
    is_admin = True  # Você pode implementar verificação de sessão Discord aqui
    
    context = {
        'is_admin': is_admin,
        'site_title': 'Guardião BETA',
        'site_description': 'Sistema de Moderação Inteligente para Discord'
    }
    
    return render(request, 'guardiao/home.html', context)

urlpatterns = [
    path('', home_page, name='home'),
    path('dashboard/', home_page, name='dashboard'),
    path('admin/', admin.site.urls),
    path('discord-admin/', include('guardiao.urls')),  # Movido para fora do /admin/
    path('login/', LoginView.as_view(template_name='admin/login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
