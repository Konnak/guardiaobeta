"""
Modelos do Banco de Dados - Sistema Guardião BETA
Schema completo com todas as tabelas especificadas
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, 
    DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Usuario(Base):
    """Tabela de usuários do sistema"""
    __tablename__ = 'usuarios'
    
    id_discord = Column(BigInteger, primary_key=True, comment='ID do usuário no Discord')
    username = Column(String(100), nullable=False, comment='Username do Discord')
    display_name = Column(String(100), nullable=False, comment='Nome de exibição no servidor')
    nome_completo = Column(String(255), nullable=False, comment='Nome completo do formulário')
    idade = Column(Integer, nullable=False, comment='Idade do usuário')
    email = Column(String(255), unique=True, nullable=False, comment='Email único do usuário')
    telefone = Column(String(20), nullable=False, comment='Telefone do usuário')
    pontos = Column(Integer, default=0, nullable=False, comment='Pontos de serviço')
    experiencia = Column(Integer, default=0, nullable=False, comment='Pontos de experiência')
    em_servico = Column(Boolean, default=False, nullable=False, comment='Status do turno')
    categoria = Column(String(50), default='Usuário', nullable=False, comment='Categoria do usuário')
    data_criacao_registro = Column(DateTime, default=func.current_timestamp(), nullable=False, comment='Data do cadastro')
    ultimo_turno_inicio = Column(DateTime, nullable=True, comment='Início do último turno')
    cooldown_prova = Column(DateTime, nullable=True, comment='Cooldown para refazer prova')
    cooldown_dispensa = Column(DateTime, nullable=True, comment='Cooldown após dispensar')
    cooldown_inativo = Column(DateTime, nullable=True, comment='Cooldown após inatividade')
    
    def __repr__(self):
        return f"<Usuario(id_discord={self.id_discord}, username='{self.username}', categoria='{self.categoria}')>"


class Denuncia(Base):
    """Tabela de denúncias do sistema"""
    __tablename__ = 'denuncias'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID único da denúncia')
    hash_denuncia = Column(String(64), unique=True, nullable=False, comment='Hash único para identificação')
    id_servidor = Column(BigInteger, nullable=False, comment='ID do servidor Discord')
    id_canal = Column(BigInteger, nullable=False, comment='ID do canal Discord')
    id_denunciante = Column(BigInteger, nullable=False, comment='ID do usuário que denunciou')
    id_denunciado = Column(BigInteger, nullable=False, comment='ID do usuário denunciado')
    motivo = Column(Text, nullable=False, comment='Motivo da denúncia')
    status = Column(String(50), default='Pendente', nullable=False, comment='Status da denúncia')
    data_criacao = Column(DateTime, default=func.current_timestamp(), nullable=False, comment='Data da denúncia')
    e_premium = Column(Boolean, default=False, nullable=False, comment='Se é servidor premium')
    resultado_final = Column(String(50), nullable=True, comment='Resultado final da denúncia')
    
    def __repr__(self):
        return f"<Denuncia(id={self.id}, hash='{self.hash_denuncia}', status='{self.status}')>"


class MensagemCapturada(Base):
    """Tabela de mensagens capturadas das denúncias"""
    __tablename__ = 'mensagens_capturadas'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID único da mensagem')
    id_denuncia = Column(Integer, ForeignKey('denuncias.id'), nullable=False, comment='ID da denúncia relacionada')
    id_autor = Column(BigInteger, nullable=False, comment='ID do autor da mensagem')
    conteudo = Column(Text, nullable=False, comment='Conteúdo da mensagem')
    anexos_urls = Column(Text, nullable=True, comment='URLs dos anexos separados por vírgula')
    timestamp_mensagem = Column(DateTime, nullable=False, comment='Timestamp da mensagem original')
    
    def __repr__(self):
        return f"<MensagemCapturada(id={self.id}, id_denuncia={self.id_denuncia}, autor={self.id_autor})>"


class VotoGuardaio(Base):
    """Tabela de votos dos guardiões"""
    __tablename__ = 'votos_guardioes'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID único do voto')
    id_denuncia = Column(Integer, ForeignKey('denuncias.id'), nullable=False, comment='ID da denúncia')
    id_guardiao = Column(BigInteger, ForeignKey('usuarios.id_discord'), nullable=False, comment='ID do guardião')
    voto = Column(String(20), nullable=False, comment='Tipo do voto (OK!, Intimidou, Grave)')
    data_voto = Column(DateTime, default=func.current_timestamp(), nullable=False, comment='Data do voto')
    
    # Constraint para evitar que o mesmo guardião vote duas vezes na mesma denúncia
    __table_args__ = (
        UniqueConstraint('id_denuncia', 'id_guardiao', name='unique_voto_guardiao_denuncia'),
    )
    
    def __repr__(self):
        return f"<VotoGuardaio(id={self.id}, denuncia={self.id_denuncia}, guardiao={self.id_guardiao}, voto='{self.voto}')>"


class ServidorPremium(Base):
    """Tabela de servidores premium"""
    __tablename__ = 'servidores_premium'
    
    id_servidor = Column(BigInteger, primary_key=True, comment='ID do servidor premium')
    data_inicio = Column(DateTime, default=func.current_timestamp(), nullable=False, comment='Data de início da assinatura')
    data_fim = Column(DateTime, nullable=False, comment='Data de término da assinatura')
    
    def __repr__(self):
        return f"<ServidorPremium(servidor={self.id_servidor}, fim={self.data_fim})>"


class ConfiguracaoServidor(Base):
    """Tabela para configurações personalizadas dos servidores premium"""
    __tablename__ = 'configuracoes_servidor'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID único da configuração')
    id_servidor = Column(BigInteger, nullable=False, comment='ID do servidor')
    canal_log = Column(BigInteger, nullable=True, comment='ID do canal de log')
    duracao_intimidou = Column(Integer, default=1, nullable=False, comment='Duração do mute por intimidação (horas)')
    duracao_intimidou_grave = Column(Integer, default=6, nullable=False, comment='Duração do mute por intimidação+grave (horas)')
    duracao_grave = Column(Integer, default=12, nullable=False, comment='Duração do mute por grave (horas)')
    duracao_grave_4plus = Column(Integer, default=24, nullable=False, comment='Duração do ban por 4+ graves (horas)')
    
    def __repr__(self):
        return f"<ConfiguracaoServidor(servidor={self.id_servidor})>"


class MensagemGuardiao(Base):
    """Tabela para rastrear mensagens enviadas aos guardiões"""
    __tablename__ = 'mensagens_guardioes'
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='ID único da mensagem')
    id_denuncia = Column(Integer, ForeignKey('denuncias.id'), nullable=False, comment='ID da denúncia relacionada')
    id_guardiao = Column(BigInteger, ForeignKey('usuarios.id_discord'), nullable=False, comment='ID do guardião')
    id_mensagem = Column(BigInteger, nullable=False, comment='ID da mensagem no Discord')
    data_envio = Column(DateTime, default=func.current_timestamp(), nullable=False, comment='Data de envio')
    timeout_expira = Column(DateTime, nullable=False, comment='Quando expira o timeout de 5 minutos')
    status = Column(String(20), default='Enviada', nullable=False, comment='Status: Enviada, Atendida, Dispensada, Expirada')
    
    def __repr__(self):
        return f"<MensagemGuardiao(denuncia={self.id_denuncia}, guardiao={self.id_guardiao}, status='{self.status}')>"


# Lista de todas as tabelas para facilitar operações
TABELAS = [
    Usuario,
    Denuncia,
    MensagemCapturada,
    VotoGuardaio,
    ServidorPremium,
    ConfiguracaoServidor,
    MensagemGuardiao
]
