"""
Comando Django para criar usuário admin automaticamente
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Cria usuário admin padrão se não existir'

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin123'
        email = 'admin@guardiao.local'
        
        # Verifica se usuário já existe
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuário "{username}" atualizado com sucesso!')
            )
        else:
            # Cria novo usuário
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuário "{username}" criado com sucesso!')
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'📝 Credenciais:\n'
                f'   Username: {username}\n'
                f'   Password: {password}\n'
                f'   Email: {email}\n'
                f'   Staff: {user.is_staff}\n'
                f'   Superuser: {user.is_superuser}\n'
                f'   Active: {user.is_active}'
            )
        )
