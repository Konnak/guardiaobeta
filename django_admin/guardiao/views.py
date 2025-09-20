"""
Views personalizadas para o Sistema Guardião BETA
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Usuario, Denuncia, MensagemCapturada, VotoGuardiao


@staff_member_required
def dashboard(request):
    """Dashboard principal com estatísticas"""
    
    # Estatísticas gerais
    total_usuarios = Usuario.objects.count()
    total_denuncias = Denuncia.objects.count()
    denuncias_em_analise = Denuncia.objects.filter(status='Em Análise').count()
    guardioes_servico = Usuario.objects.filter(em_servico=True, categoria='Guardião').count()
    
    # Estatísticas recentes (últimos 7 dias)
    semana_passada = timezone.now() - timedelta(days=7)
    denuncias_recentes = Denuncia.objects.filter(data_criacao__gte=semana_passada).count()
    usuarios_recentes = Usuario.objects.filter(data_cadastro__gte=semana_passada).count()
    
    # Top guardiões por atividade
    top_guardioes = Usuario.objects.filter(
        categoria='Guardião'
    ).annotate(
        total_votos=Count('votoguardiao')
    ).order_by('-total_votos')[:5]
    
    # Denúncias recentes
    denuncias_recentes_list = Denuncia.objects.select_related('id_denunciante').order_by('-data_criacao')[:10]
    
    context = {
        'total_usuarios': total_usuarios,
        'total_denuncias': total_denuncias,
        'denuncias_em_analise': denuncias_em_analise,
        'guardioes_servico': guardioes_servico,
        'denuncias_recentes': denuncias_recentes,
        'usuarios_recentes': usuarios_recentes,
        'top_guardioes': top_guardioes,
        'denuncias_recentes_list': denuncias_recentes_list,
    }
    
    return render(request, 'guardiao/dashboard.html', context)


@staff_member_required
def estatisticas(request):
    """Página de estatísticas detalhadas"""
    
    # Estatísticas por período
    hoje = timezone.now().date()
    semana_passada = hoje - timedelta(days=7)
    mes_passado = hoje - timedelta(days=30)
    
    # Denúncias por status
    denuncias_por_status = Denuncia.objects.values('status').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Usuários por categoria
    usuarios_por_categoria = Usuario.objects.values('categoria').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Denúncias por dia (últimos 30 dias)
    denuncias_por_dia = []
    for i in range(30):
        data = hoje - timedelta(days=i)
        count = Denuncia.objects.filter(data_criacao__date=data).count()
        denuncias_por_dia.append({'data': data, 'count': count})
    
    # Top denunciantes
    top_denunciantes = Usuario.objects.annotate(
        total_denuncias=Count('denuncias_feitas')
    ).filter(total_denuncias__gt=0).order_by('-total_denuncias')[:10]
    
    context = {
        'denuncias_por_status': denuncias_por_status,
        'usuarios_por_categoria': usuarios_por_categoria,
        'denuncias_por_dia': denuncias_por_dia,
        'top_denunciantes': top_denunciantes,
    }
    
    return render(request, 'guardiao/estatisticas.html', context)


@staff_member_required
def detalhes_denuncia(request, denuncia_id):
    """Detalhes de uma denúncia específica"""
    
    denuncia = get_object_or_404(Denuncia, id=denuncia_id)
    mensagens = MensagemCapturada.objects.filter(id_denuncia=denuncia).order_by('-timestamp_mensagem')
    votos = VotoGuardiao.objects.filter(id_denuncia=denuncia).select_related('id_guardiao')
    
    # Estatísticas da denúncia
    total_votos = votos.count()
    votos_aprovar = votos.filter(decisao='Aprovar').count()
    votos_rejeitar = votos.filter(decisao='Rejeitar').count()
    votos_abster = votos.filter(decisao='Abster').count()
    
    context = {
        'denuncia': denuncia,
        'mensagens': mensagens,
        'votos': votos,
        'total_votos': total_votos,
        'votos_aprovar': votos_aprovar,
        'votos_rejeitar': votos_rejeitar,
        'votos_abster': votos_abster,
    }
    
    return render(request, 'guardiao/detalhes_denuncia.html', context)
