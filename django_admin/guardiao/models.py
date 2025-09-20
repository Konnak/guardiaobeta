"""
Models para o Sistema Guardião BETA
Baseados na estrutura do banco PostgreSQL existente
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Usuario(models.Model):
    """Model para usuários do sistema"""
    
    CATEGORIA_CHOICES = [
        ('Civil', 'Civil'),
        ('Guardião', 'Guardião'),
        ('Administrador', 'Administrador'),
    ]
    
    id_discord = models.BigIntegerField(unique=True, verbose_name="ID Discord")
    username = models.CharField(max_length=100, verbose_name="Username")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='Civil', verbose_name="Categoria")
    experiencia = models.IntegerField(default=0, verbose_name="Experiência")
    em_servico = models.BooleanField(default=False, verbose_name="Em Serviço")
    cooldown_prova = models.DateTimeField(blank=True, null=True, verbose_name="Cooldown da Prova")
    cooldown_dispensa = models.DateTimeField(blank=True, null=True, verbose_name="Cooldown da Dispensa")
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")
    ultima_atividade = models.DateTimeField(auto_now=True, verbose_name="Última Atividade")
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ['-data_cadastro']
    
    def __str__(self):
        return f"{self.username} ({self.categoria})"
    
    @property
    def nivel_experiencia(self):
        """Calcula o nível baseado na experiência"""
        if self.experiencia < 100:
            return "Novato"
        elif self.experiencia < 500:
            return "Experiente"
        elif self.experiencia < 1000:
            return "Veterano"
        elif self.experiencia < 2500:
            return "Especialista"
        else:
            return "Mestre"


class ServidorPremium(models.Model):
    """Model para servidores premium"""
    
    id_servidor = models.BigIntegerField(unique=True, verbose_name="ID do Servidor")
    nome_servidor = models.CharField(max_length=100, verbose_name="Nome do Servidor")
    premium_ate = models.DateTimeField(verbose_name="Premium Até")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    class Meta:
        verbose_name = "Servidor Premium"
        verbose_name_plural = "Servidores Premium"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.nome_servidor} (Premium até {self.premium_ate.strftime('%d/%m/%Y')})"


class ConfiguracaoServidor(models.Model):
    """Model para configurações dos servidores"""
    
    id_servidor = models.BigIntegerField(unique=True, verbose_name="ID do Servidor")
    canal_denuncias = models.BigIntegerField(blank=True, null=True, verbose_name="Canal de Denúncias")
    canal_logs = models.BigIntegerField(blank=True, null=True, verbose_name="Canal de Logs")
    auto_moderacao = models.BooleanField(default=False, verbose_name="Auto Moderação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Data de Atualização")
    
    class Meta:
        verbose_name = "Configuração do Servidor"
        verbose_name_plural = "Configurações dos Servidores"
    
    def __str__(self):
        return f"Configuração Servidor {self.id_servidor}"


class Denuncia(models.Model):
    """Model para denúncias"""
    
    STATUS_CHOICES = [
        ('Em Análise', 'Em Análise'),
        ('Aprovada', 'Aprovada'),
        ('Rejeitada', 'Rejeitada'),
        ('Pendente', 'Pendente'),
    ]
    
    RESULTADO_CHOICES = [
        ('Aprovada', 'Aprovada'),
        ('Rejeitada', 'Rejeitada'),
        ('Sem Decisão', 'Sem Decisão'),
    ]
    
    hash_denuncia = models.CharField(max_length=32, unique=True, verbose_name="Hash da Denúncia")
    id_servidor = models.BigIntegerField(verbose_name="ID do Servidor")
    id_canal = models.BigIntegerField(verbose_name="ID do Canal")
    id_denunciante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='denuncias_feitas', verbose_name="Denunciante")
    id_denunciado = models.BigIntegerField(verbose_name="ID do Denunciado")
    motivo = models.TextField(verbose_name="Motivo")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Em Análise', verbose_name="Status")
    e_premium = models.BooleanField(default=False, verbose_name="É Premium")
    resultado_final = models.CharField(max_length=20, choices=RESULTADO_CHOICES, blank=True, null=True, verbose_name="Resultado Final")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_resolucao = models.DateTimeField(blank=True, null=True, verbose_name="Data de Resolução")
    
    class Meta:
        verbose_name = "Denúncia"
        verbose_name_plural = "Denúncias"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Denúncia {self.hash_denuncia[:8]}... - {self.status}"
    
    @property
    def tempo_resolucao(self):
        """Calcula o tempo de resolução"""
        if self.data_resolucao and self.data_criacao:
            return self.data_resolucao - self.data_criacao
        return None
    
    @property
    def denunciado_username(self):
        """Tenta obter o username do denunciado"""
        try:
            usuario = Usuario.objects.get(id_discord=self.id_denunciado)
            return usuario.username
        except Usuario.DoesNotExist:
            return f"Usuário {self.id_denunciado}"


class MensagemCapturada(models.Model):
    """Model para mensagens capturadas"""
    
    id_denuncia = models.ForeignKey(Denuncia, on_delete=models.CASCADE, related_name='mensagens', verbose_name="Denúncia")
    id_autor = models.BigIntegerField(verbose_name="ID do Autor")
    conteudo = models.TextField(verbose_name="Conteúdo")
    anexos_urls = models.TextField(blank=True, null=True, verbose_name="URLs dos Anexos")
    timestamp_mensagem = models.DateTimeField(verbose_name="Timestamp da Mensagem")
    
    class Meta:
        verbose_name = "Mensagem Capturada"
        verbose_name_plural = "Mensagens Capturadas"
        ordering = ['-timestamp_mensagem']
    
    def __str__(self):
        return f"Mensagem de {self.id_autor} em {self.timestamp_mensagem.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def autor_username(self):
        """Tenta obter o username do autor"""
        try:
            usuario = Usuario.objects.get(id_discord=self.id_autor)
            return usuario.username
        except Usuario.DoesNotExist:
            return f"Usuário {self.id_autor}"
    
    @property
    def conteudo_resumido(self):
        """Retorna o conteúdo resumido"""
        if len(self.conteudo) > 100:
            return self.conteudo[:100] + "..."
        return self.conteudo


class VotoGuardiao(models.Model):
    """Model para votos dos guardiões"""
    
    DECISAO_CHOICES = [
        ('Aprovar', 'Aprovar'),
        ('Rejeitar', 'Rejeitar'),
        ('Abster', 'Abster'),
    ]
    
    id_guardiao = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Guardião")
    id_denuncia = models.ForeignKey(Denuncia, on_delete=models.CASCADE, related_name='votos', verbose_name="Denúncia")
    decisao = models.CharField(max_length=10, choices=DECISAO_CHOICES, verbose_name="Decisão")
    justificativa = models.TextField(blank=True, null=True, verbose_name="Justificativa")
    data_voto = models.DateTimeField(auto_now_add=True, verbose_name="Data do Voto")
    
    class Meta:
        verbose_name = "Voto do Guardião"
        verbose_name_plural = "Votos dos Guardiões"
        ordering = ['-data_voto']
        unique_together = ['id_guardiao', 'id_denuncia']  # Um guardião só pode votar uma vez por denúncia
    
    def __str__(self):
        return f"Voto de {self.id_guardiao.username}: {self.decisao}"


class Estatisticas(models.Model):
    """Model para estatísticas do sistema"""
    
    data = models.DateField(unique=True, verbose_name="Data")
    denuncias_criadas = models.IntegerField(default=0, verbose_name="Denúncias Criadas")
    denuncias_resolvidas = models.IntegerField(default=0, verbose_name="Denúncias Resolvidas")
    usuarios_ativos = models.IntegerField(default=0, verbose_name="Usuários Ativos")
    guardioes_servico = models.IntegerField(default=0, verbose_name="Guardiões em Serviço")
    tempo_medio_resolucao = models.DurationField(blank=True, null=True, verbose_name="Tempo Médio de Resolução")
    
    class Meta:
        verbose_name = "Estatística"
        verbose_name_plural = "Estatísticas"
        ordering = ['-data']
    
    def __str__(self):
        return f"Estatísticas de {self.data.strftime('%d/%m/%Y')}"
