from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board

class Command(BaseCommand):
    help = 'Import a Trello board'

    def add_arguments(self, parser):
        parser.add_argument('board_name', type=str)

    def handle(self, *args, **options):
        board_name = options['board_name']

        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)

        Board.import_board(trello, board_name)