from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board
from trelloapps.models import Card

import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update projects and members boards'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        master = Board.objects.get(name=settings.TRELLO_MASTER)

        for mastercard in Card.objects.filter(boardlist__board=master):

            for card in mastercard.card_set.filter(last_activity__lt=mastercard.last_activity):
                logger.info('{0} - {1}'.format(card.last_activity, mastercard.last_activity))
                logger.info("Updated card [{1} > {2} > {0}]".format(card.name, card.boardlist.board.name, card.boardlist.name))

            