from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()

"""
Through this function, the API Tokens for the students can be generated. 
A student can insert the token into their repo like so: 
- Go to: Einstellungen > CI/CD > Variablen
- CI/CD Variablen, Variable Hinzufuegen 
    - Maskiert und ausgeblendet
    - Schluessel: SCOREBOARD_ACCESS_TOKEN
    - Wert: the value generated here

The output can be in CSV (<username>, <token>). I added this since it might be practical to have this in case you ever want 
to automatically send the tokens to students.
The default output has the format "Token for <username>: <token>"
"""
class Command(BaseCommand):
    help = 'Generate API tokens for all users or a specific user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Generate token for a specific user')
        parser.add_argument('--csv', action='store_true', help='Output in CSV format')


    def handle(self, *args, **options):
        username = options.get('username')
        csv_format = options.get('csv')

        if username:
            try:
                user = User.objects.get(username=username)
                token, created = Token.objects.get_or_create(user=user)
                self.output_token(user, token, csv_format)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" does not exist'))
        else:
            if csv_format:
                self.stdout.write("username,token")

            for user in User.objects.all():
                token, created = Token.objects.get_or_create(user=user)
                self.output_token(user, token, csv_format)

    def output_token(self, user, token, csv_format):
        if csv_format:
            self.stdout.write(f"{user.username},{token.key}")
        else:
            self.stdout.write(self.style.SUCCESS(f'Token for {user.username}: {token.key}'))