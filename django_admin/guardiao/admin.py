"""
Admin configuration for Guardião BETA
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.utils.safestring import mark_safe
from .models import (
    Usuario, ServidorPremium, ConfiguracaoServidor, 
    Denuncia, MensagemCapturada, VotoGuardiao, Estatisticas
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = [
        'username', 'id_discord', 'categoria', 'nivel_experiencia', 
        'experiencia', 'em_servico', 'status_cooldown', 'data_cadastro'
    ]
    list_filter = ['categoria', 'em_servico', 'data_cadastro']
    search_fields = ['username', 'email', 'id_discord']
    readonly_fields = ['data_cadastro', 'ultima_atividade']
    ordering = ['-data_cadastro']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('id_discord', 'username', 'email', 'categoria')
        }),
        ('Sistema', {
            'fields': ('experiencia', 'em_servico', 'cooldown_prova', 'cooldown_dispensa')
        }),
        ('Datas', {
            'fields': ('data_cadastro', 'ultima_atividade'),
            'classes': ('collapse',)
        }),
    )
    
    def nivel_experiencia(self, obj):
        return obj.nivel_experiencia
    nivel_experiencia.short_description = 'Nível'
    
    def status_cooldown(self, obj):
        if obj.cooldown_prova and obj.cooldown_prova > timezone.now():
            return format_html('<span style="color: red;">⏰ Cooldown Ativo</span>')
        return format_html('<span style="color: green;">✅ Disponível</span>')
    status_cooldown.short_description = 'Status'
    
    actions = ['ativar_servico', 'desativar_servico', 'resetar_cooldowns']
    
    def ativar_servico(self, request, queryset):
        updated = queryset.update(em_servico=True)
        self.message_user(request, f'{updated} usuários colocados em serviço.')
    ativar_servico.short_description = "Colocar em serviço"
    
    def desativar_servico(self, request, queryset):
        updated = queryset.update(em_servico=False)
        self.message_user(request, f'{updated} usuários removidos do serviço.')
    desativar_servico.short_description = "Remover do serviço"
    
    def resetar_cooldowns(self, request, queryset):
        updated = queryset.update(cooldown_prova=None, cooldown_dispensa=None)
        self.message_user(request, f'Cooldowns resetados para {updated} usuários.')
    resetar_cooldowns.short_description = "Resetar cooldowns"


@admin.register(ServidorPremium)
class ServidorPremiumAdmin(admin.ModelAdmin):
    list_display = ['nome_servidor', 'id_servidor', 'premium_ate', 'ativo', 'dias_restantes']
    list_filter = ['ativo', 'premium_ate']
    search_fields = ['nome_servidor', 'id_servidor']
    readonly_fields = ['data_criacao']
    
    def dias_restantes(self, obj):
        dias = (obj.premium_ate - timezone.now().date()).days
        if dias > 0:
            return format_html(f'<span style="color: green;">{dias} dias</span>')
        else:
            return format_html(f'<span style="color: red;">Expirado</span>')
    dias_restantes.short_description = 'Dias Restantes'


@admin.register(ConfiguracaoServidor)
class ConfiguracaoServidorAdmin(admin.ModelAdmin):
    list_display = ['id_servidor', 'auto_moderacao', 'data_atualizacao']
    list_filter = ['auto_moderacao']


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = [
        'hash_denuncia', 'denunciante_link', 'denunciado_username', 
        'status', 'e_premium', 'tempo_resolucao_display', 'data_criacao'
    ]
    list_filter = ['status', 'e_premium', 'data_criacao']
    search_fields = ['hash_denuncia', 'motivo', 'id_denunciante__username']
    readonly_fields = ['hash_denuncia', 'data_criacao', 'tempo_resolucao']
    ordering = ['-data_criacao']
    
    fieldsets = (
        ('Informações da Denúncia', {
            'fields': ('hash_denuncia', 'id_denunciante', 'id_denunciado', 'motivo')
        }),
        ('Status', {
            'fields': ('status', 'resultado_final', 'e_premium')
        }),
        ('Localização', {
            'fields': ('id_servidor', 'id_canal')
        }),
        ('Datas', {
            'fields': ('data_criacao', 'data_resolucao', 'tempo_resolucao'),
            'classes': ('collapse',)
        }),
    )
    
    def denunciante_link(self, obj):
        url = reverse('admin:guardiao_usuario_change', args=[obj.id_denunciante.id])
        return format_html('<a href="{}">{}</a>', url, obj.id_denunciante.username)
    denunciante_link.short_description = 'Denunciante'
    
    def tempo_resolucao_display(self, obj):
        tempo = obj.tempo_resolucao
        if tempo:
            return format_html('<span style="color: blue;">{}</span>', tempo)
        return format_html('<span style="color: gray;">Em andamento</span>')
    tempo_resolucao_display.short_description = 'Tempo de Resolução'
    
    actions = ['aprovar_denuncias', 'rejeitar_denuncias', 'marcar_premium']
    
    def aprovar_denuncias(self, request, queryset):
        updated = queryset.update(status='Aprovada', resultado_final='Aprovada', data_resolucao=timezone.now())
        self.message_user(request, f'{updated} denúncias aprovadas.')
    aprovar_denuncias.short_description = "Aprovar denúncias selecionadas"
    
    def rejeitar_denuncias(self, request, queryset):
        updated = queryset.update(status='Rejeitada', resultado_final='Rejeitada', data_resolucao=timezone.now())
        self.message_user(request, f'{updated} denúncias rejeitadas.')
    rejeitar_denuncias.short_description = "Rejeitar denúncias selecionadas"
    
    def marcar_premium(self, request, queryset):
        updated = queryset.update(e_premium=True)
        self.message_user(request, f'{updated} denúncias marcadas como premium.')
    marcar_premium.short_description = "Marcar como premium"


@admin.register(MensagemCapturada)
class MensagemCapturadaAdmin(admin.ModelAdmin):
    list_display = ['id', 'denuncia_link', 'autor_username', 'conteudo_resumido', 'timestamp_mensagem']
    list_filter = ['timestamp_mensagem', 'id_denuncia__status']
    search_fields = ['conteudo', 'id_denuncia__hash_denuncia']
    readonly_fields = ['timestamp_mensagem']
    ordering = ['-timestamp_mensagem']
    
    def denuncia_link(self, obj):
        url = reverse('admin:guardiao_denuncia_change', args=[obj.id_denuncia.id])
        return format_html('<a href="{}">{}</a>', url, obj.id_denuncia.hash_denuncia[:8])
    denuncia_link.short_description = 'Denúncia'


@admin.register(VotoGuardiao)
class VotoGuardiaoAdmin(admin.ModelAdmin):
    list_display = ['id_guardiao', 'id_denuncia', 'decisao', 'data_voto']
    list_filter = ['decisao', 'data_voto']
    search_fields = ['id_guardiao__username', 'id_denuncia__hash_denuncia']
    readonly_fields = ['data_voto']
    ordering = ['-data_voto']


@admin.register(Estatisticas)
class EstatisticasAdmin(admin.ModelAdmin):
    list_display = ['data', 'denuncias_criadas', 'denuncias_resolvidas', 'usuarios_ativos', 'guardioes_servico']
    list_filter = ['data']
    readonly_fields = ['data']
    ordering = ['-data']


# Custom Admin Site
class GuardiaoAdminSite(admin.AdminSite):
    site_header = "Guardião BETA - Painel Administrativo"
    site_title = "Guardião BETA Admin"
    index_title = "Bem-vindo ao Painel de Administração"
    
    def index(self, request, extra_context=None):
        """Custom index page with statistics"""
        extra_context = extra_context or {}
        
        # Estatísticas gerais
        total_usuarios = Usuario.objects.count()
        total_denuncias = Denuncia.objects.count()
        denuncias_em_analise = Denuncia.objects.filter(status='Em Análise').count()
        guardioes_servico = Usuario.objects.filter(em_servico=True, categoria='Guardião').count()
        
        # Estatísticas recentes (últimos 7 dias)
        from datetime import timedelta
        semana_passada = timezone.now() - timedelta(days=7)
        denuncias_recentes = Denuncia.objects.filter(data_criacao__gte=semana_passada).count()
        usuarios_recentes = Usuario.objects.filter(data_cadastro__gte=semana_passada).count()
        
        extra_context.update({
            'total_usuarios': total_usuarios,
            'total_denuncias': total_denuncias,
            'denuncias_em_analise': denuncias_em_analise,
            'guardioes_servico': guardioes_servico,
            'denuncias_recentes': denuncias_recentes,
            'usuarios_recentes': usuarios_recentes,
        })
        
        return super().index(request, extra_context)
