from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board, Card, BoardList, Project, Member, Label
from django.db.models import Q
from trello.exceptions import ResourceUnavailable
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass
           
    def create_missing_mastercard(self, card, master, board, fake=False):
        """
        create the master card.
        """
        logger.info( 'Add to master [{0}]'.format(str(card)) )

        if fake: return
                
        mastercard           = Card(remoteid=None)
        mastercard.name      = card.name
        mastercard.desc      = card.desc
        mastercard.boardlist = card.boardlist.parent
        mastercard.closed    = card.closed
        mastercard.save()
        card.parent = mastercard
        card.save()

        if board.member:
            mastercard.members.add(board.member)

        if board.project:
            mastercard.labels.add( board.project.label(master) )

        #IT WAS USED FOR THE FIRST IMPORT, WHERE THERE WERE CARDS REPEATED IN THE PROJECTS AND MEMBERS BOARDS
        # store all the cards associated to the current card.
        # the variable is used to update the last state of the cards in the master 
        allcards = [card]
        
        # search for cards in other boards with the same name
        for tmp in Card.objects.exclude(
            boardlist__board__in=[master,board]).filter(
            name=card.name, parent=None):
            
            tmp.parent = mastercard

            if tmp.boardlist.board.member:
                mastercard.members.add(tmp.boardlist.board.member)

            if tmp.boardlist.board.project:
                mastercard.labels.add( tmp.boardlist.board.project.label(master) )
           
            tmp.save()

            allcards.append(tmp)

        allcards = sorted(allcards, key=lambda x:x.last_activity, reverse=True)
        lastupdated_card = allcards[0]
        mastercard.boardlist=lastupdated_card.boardlist.parent
        mastercard.closed=lastupdated_card.closed
        
        mastercard.save()





    def compute_modifications(self, master, fake=False):

        # SYNC ALL CARDS TO MASTER
        # Select to sync all the boards that were not marked to be removed.
        for card in Card.objects.exclude(boardlist__board=master).exclude(delete_remotely=True).order_by('last_activity'):
            
            if card.parent is None:
                # Create the card in the master board
                self.create_missing_mastercard(
                    card, master, card.boardlist.board, fake=fake
                )

        for card in Card.objects.filter(
                Q(update_name=True) | Q(update_desc=True) | Q(update_closed=True) | 
                Q(update_members=True) | Q(update_labels=True) | Q(update_list=True) | Q(delete_remotely=True)
            ).order_by('last_activity'):

            if card.delete_remotely:
                label  = card.boardlist.board.label()
                member = card.boardlist.board.member

                logger.info(
                    "Found removed card [{0}]".format( str(card) )
                )

                if card.parent:
                    if label:
                        logger.info(
                            "Remove label from [{0}] from card [{1}]".format(label, str(card.parent) )
                        )
                        if not fake:
                            try:
                                card.parent.labels.remove(label.parent)
                                card.parent.update_labels = True
                                card.parent.save()
                            except ValueError:
                                pass

                    if member:
                        logger.info(
                            "Remove member from [{0}] from card [{1}]".format(str(member), str(card.parent) )
                        )
                        if not fake:
                            try:
                                card.parent.members.remove(member)
                                card.parent.update_members = True
                                card.parent.save()
                            except ValueError:
                                pass

                    if not fake: card.save()
                else:
                    for child in card.card_set.all():
                        logger.info(
                            "Remove card [{0}]".format(str(child))
                        )
                        if not fake:
                            child.delete_remotely = True
                            child.save()
                    logger.info(
                        "Remove card [{0}]".format(str(card))
                    )
                    if not fake: card.delete()

            siblings = Card.objects.filter( Q(parent=card.parent) | Q(pk=card.parent.pk) ) if card.parent else Card.objects.filter( Q(parent=card) | Q(pk=card.pk) )
            siblings = siblings.order_by('-last_activity')

            # NAME
            if card.update_name:
                updated = siblings.filter(update_name=True)
                
                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling name [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    
                    if not fake:
                        c.name = ref.name
                        c.update_name = True
                        c.save()

            # DESCRIPTION
            if card.update_desc:
                updated = siblings.filter(update_desc=True)

                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling description [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    
                    if not fake:
                        c.desc = ref.desc
                        c.update_desc = True
                        c.save()

            # CLOSED
            if card.update_closed:
                updated = siblings.filter(update_closed=True)
                
                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling closed [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    if not fake:
                        c.closed = ref.closed
                        c.update_closed = True
                        c.save()

            # BOARD LIST
            if card.update_list:
                updated = siblings.filter(update_list=True)
                
                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling list [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    if not fake:
                        c.boardlist.boardlist = BoardList.objects.get(name=ref.boardlist.name, board=c.boardlist.board)
                        c.update_list = True
                        c.save()

            # ONLY IF MASTER
            if card.boardlist.board.name==settings.TRELLO_MASTER:

                # MEMBERS
                if card.update_members:
                    cards_to_remove = siblings.exclude(pk=card.pk).exclude(boardlist__board__member=None)
                    
                    for member in card.members.all():
                        cards_to_remove = cards_to_remove.exclude(boardlist__board__member=member)

                    for c in cards_to_remove:
                        logger.info("[MEMBERS] Remove card [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                        if not fake:
                            c.delete_remotely = True
                            c.save()

                    for member in card.members.all():
                        try:
                            obj = Card.objects.get(boardlist__board__member=member, parent=card)
                        except Card.DoesNotExist:
                            blist = BoardList.objects.get(board__member=member, name=card.boardlist.name)
                            obj = Card(name=card.name, desc=card.desc, closed=card.closed, boardlist=blist, parent=card)
                            logger.info("[MEMBERS] Created the card [{1} > {2} > {0}]".format( obj.name, obj.boardlist.board.name, obj.boardlist.name))
                            
                            if not fake: obj.save()
                            
                # LABELS
                if card.update_labels:
                    cards_to_remove = siblings.exclude(pk=card.pk).exclude(boardlist__board__project=None)
                    cards_to_add    = card.labels.all()
                    
                    for label in card.labels.all():
                        cards_to_remove = cards_to_remove.exclude(boardlist__board__name=label.name)

                    for c in cards_to_remove:
                        logger.info("[LABELS] Remove card [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                        if not fake: 
                            c.delete_remotely = True
                            c.save()
                    
                    for label in card.labels.all():
                        try:
                            obj = Card.objects.get(boardlist__board__name=label.name, parent=card)
                        except Card.DoesNotExist:
                            blist = BoardList.objects.get(board__project__name=label.name, name=card.boardlist.name)
                            obj = Card(name=card.name, desc=card.desc, closed=card.closed, boardlist=blist, parent=card)
                            logger.info("[LABELS] Created the card [{1} > {2} > {0}]".format( obj.name, obj.boardlist.board.name, obj.boardlist.name))
                            if not fake: obj.save()
                            


    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        master = Board.objects.get(name=settings.TRELLO_MASTER)

        self.compute_modifications(master, fake=True)
        