from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
class Command(BaseCommand):
    help = 'Create demo access groups without creating accounts'
    def handle(self, *args, **kwargs):
        Group.objects.get_or_create(name='Clinician')
        self.stdout.write(self.style.SUCCESS('Clinician group is ready. Assign users in Django Admin.'))
