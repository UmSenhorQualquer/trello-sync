from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board
from trelloapps.models import BoardList
from trelloapps.models import Member
from trelloapps.models import Card
import logging; logger = logging.getLogger(__name__)

from dateutil import parser as dateparser

class Command(BaseCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        master = Board.objects.get(name=settings.TRELLO_MASTER)

        updatedcards_ids = []

        for board in Board.objects.all().order_by('pk'):
            logger.info( 'Importing board {0}'.format(board.name) )

            # search for the remote board
            b = board.remote_object(trello)

            # check if the board was updated since the last update
            if board.last_activity is not None and b.date_last_activity<=board.last_activity:
                logger.info( 'No activity detected' )
                continue

            board.last_activity = b.date_last_activity
            board.save()

            # If is the first update then import all the lists from the board.
            if not board.last_activity:
                for lst in board.boardlist_set.all():
                    l = lst.remote_object(trello)
                    lst.name     = l.name
                    lst.closed   = l.closed
                    lst.position = l.pos
                    lst.save()
                    lst.import_cards(l)

            else:
                # if is not the first board update, update only the latest modifications
                # the board was already imported once
                query = {'since': board.last_activity.isoformat( timespec='microseconds')}
                data  = trello.fetch_json('/boards/' + board.remoteid + '/actions', query_params=query)

                ids   = []
                for update in data:
                    
                    action_type = update.get('type',None)
                    card_info   = update['data'].get('card', None)
                    date_last_activity = dateparser.parse(update.get('date'))
                        
                    if card_info:
                        card_id = card_info['id']

                        if action_type=='deleteCard':
                            try:
                                card = Card.objects.get(remoteid=card_id)
                                card.last_activity = date_last_activity
                                card.delete_remotely = True
                                card.remoteid = None
                                card.save()
                                logger.info("The card [{0}] in the board [{1}] was marked to be removed".format(card.name, card.boardlist.board.name))
                            except Card.DoesNotExist:
                                # ignore
                                pass
                        else:
                            # append to the list all the modified cards ids
                            updatedcards_ids.append(card_id)

                if master==board:
                    for c in b.open_cards():
                        try:
                            card = Card.objects.get(remoteid=c.id)
                            if card.last_activity<c.date_last_activity:
                                updatedcards_ids.append(c.id)

                        except Card.DoesNotExist:
                            pass

        # get all the remote cards.
        cards = []
        updatedcards_ids = list(set(updatedcards_ids))
        for idx, i in enumerate(updatedcards_ids):
            logger.info("Get remote card ({0}/{1})".format(idx+1, len(updatedcards_ids) )  )
            cards.append(trello.get_card(i) )

        # sort the cards by activity, so the latest card is the one updated
        cards = sorted(cards, key=lambda x: x.date_last_activity)

        lists = {} # cache all the boards lists

        for c in cards:
            # check if the boad list is already in cache, otherwise add it
            if c.list_id not in lists:
                lists[c.list_id] = BoardList.objects.get(remoteid=c.list_id)

            try:
                card = Card.objects.get(remoteid=c.id)

                # the card list is diferent, mark it to update
                if card.name!=c.name:
                    card.update_name = True
                    card.name = c.name

                if card.desc!=c.description:
                    card.update_desc = True
                    card.desc = c.description

                if card.closed!=c.closed:
                    card.update_closed = True
                    card.closed = c.closed
                
                if card.boardlist!=lists[c.list_id]:
                    card.update_list = True
                    card.boardlist = lists[c.list_id]

            except Card.DoesNotExist:
                # the card does not exists, create it
                card = Card(remoteid = c.id)
                card.name = c.name
                card.desc = c.description
                card.closed = c.closed
                card.boardlist = lists[c.list_id]

            card.position = c.pos
            card.last_activity = c.date_last_activity
            card.save()
            card.update_members_by_id(trello, c.member_id)
            card.update_labels_by_id(trello,  c.idLabels)

            logger.info(
                "Updated card [{1} > {2} > {0}]: name:{3}, description:{4}, closed:{5}, list:{6}, members:{7}, labels:{8}".format(
                    card.name, card.boardlist.board.name, card.boardlist.name,
                    card.update_name, card.update_desc, card.update_closed,
                    card.update_list, card.update_members, card.update_labels
                )
            )