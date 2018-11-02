from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board, Card, BoardList, Project, Member, Label
from django.db.models import Q

class Command(BaseCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass

    

    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        master = Board.objects.get(name=settings.TRELLO_MASTER)
        
        # SYNC ALL CARDS TO MASTER
        for card in Card.objects.exclude(boardlist__board=master):
            board  = card.boardlist.board

            # get the master label for the card board.
            try:
                label = Label.objects.get(board=master, name=board.name)
            except Label.DoesNotExist:
                label = None

            if card.parent is None:
                # Create the card in the master board
                print('Adicionar ao master >', board.name, '>', card.name)
                c = card.boardlist.parent.remote_object(trello).add_card(
                    card.name, 
                    desc=card.desc, 
                    labels=[label.remote_object(trello)] if label else None, 
                    assign=[board.member.remote_object(trello)] if board.member else None,
                )
                c.set_closed(card.closed)

                mastercard = Card(remoteid=c.id)
                mastercard.name=c.name
                mastercard.desc=c.desc
                mastercard.boardlist=card.boardlist.parent
                mastercard.position=c.pos
                mastercard.closed=c.closed
                mastercard.last_activity=c.date_last_activity
                mastercard.save()

                card.parent = mastercard
                card.save()

                if board.member:
                    mastercard.members.add(board.member)

                # search for cards in other boards with the same name
                for tmp in Card.objects.exclude(
                    boardlist__board__in=[master,board]).filter(
                    name=card.name, parent=None):
                    tmp.parent = mastercard
                    
                    try:
                        c.assign(tmp.boardlist.board.member.remoteid)
                    except:
                        pass

                    try:
                        tmp_label = Label.objects.get(board=master, name=tmp.boardlist.board.name)
                        c.add_label(tmp_label.remote_object(trello))
                    except Label.DoesNotExist:
                        pass

                    tmp.save()
            else:
                # check which card has the latest version and update it,
                # in the boards
                pass

            
            

            """
            parent = card.parent if card.parent else card

            cards = Card.objects.filter(
                Q(parent=parent) | Q(pk=parent.pk)
            ).order_by('-last_activity')

            mastercard = cards[0]
            
            for c in cards[1:]:
                card2move = trello.get_card(c.remoteid)
                
                print('**search',c.boardlist.board.name, mastercard.boardlist.name)
                list2move = BoardList.objects.get(board=c.boardlist.board, name=mastercard.boardlist.name)
                #card2move.change_list(list2move.id)
                print(c.boardlist.board.name, '\tchange', card2move.name, 'to list', list2move.name)
            """