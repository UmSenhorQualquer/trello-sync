from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board

class Command(BaseCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)

        Board.import_board(trello, settings.TRELLO_MASTER)
        
        for board_name in settings.TRELLO_BOARDS:
        	Board.import_board(trello, board_name)