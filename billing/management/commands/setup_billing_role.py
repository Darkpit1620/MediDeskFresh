from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create the Billing staff group (assign members manually through Django admin).'

    def handle(self, *args, **kwargs):
        _, created = Group.objects.get_or_create(name='Billing')
        self.stdout.write('Billing group ready' + (' (created).' if created else '.'))
