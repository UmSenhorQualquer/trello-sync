from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Project, Member, Board, Label, BoardList, Card
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Merge cards by name'


    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        
        for mastercard in Card.objects.filter(boardlist__board__name=settings.TRELLO_MASTER):
            
            for card in Card.objects.exclude(
                    boardlist__board__name=settings.TRELLO_MASTER
                ).filter(name=mastercard.name, parent=None):

                card.parent = mastercard
                card.save()

                logger.info( 'Merge card [{1}] -> [{0}]'.format(str(card), str(card.parent)) )
