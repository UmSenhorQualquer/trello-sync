from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Card

class Command(BaseCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        
        for card in Card.objects.all():
            if card.desc.startswith('card-id:'):
                card_id = card.desc[8:32]
                if card_id!=card.remoteid:
                    try:
                        parent = Card.objects.get(remoteid=card_id)
                        card.parent = parent
                        card.save()
                    except Card.DoesNotExist:
                        print('errr')
                    