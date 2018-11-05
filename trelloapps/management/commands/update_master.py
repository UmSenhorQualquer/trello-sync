from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board, Card, BoardList, Project, Member, Label
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass

    def commit_newcards_to_master(self, trello):
        """
        Add all the new cards remotely 
        """
        remote_labels  = {}
        remote_members = {}

        # ADD ALL THE NEW BOARDS
        total_cards = Card.objects.filter(remoteid=None).count()
        for index, card in enumerate(Card.objects.filter(remoteid=None)):
            
            # Find all the labels of the new card
            labels = []
            for label in card.labels.all():
                if label.id not in remote_labels:
                    remote_labels[label.id] = label.remote_object(trello)
                labels.append(remote_labels[label.id])

            # Find all the members of the new card
            members = []
            for member in card.members.all():
                if member.id not in remote_members:
                    remote_members[member.id] = member.remote_object(trello)
                members.append(remote_members[member.id])

            logger.info('Upload ({0}/{1}) > {2} > {3} {4} {5}'.format(index+1, total_cards, card.boardlist.board.name, card.name, str(members), str(labels) ) )

            # add the card remotely
            c = card.boardlist.remote_object(trello).add_card(
                card.name, 
                desc=card.desc, 
                labels=labels if labels else None, 
                assign=members if members else None,
            )
            c.set_closed(card.closed)

            # update the local card
            card.remoteid=c.id
            card.last_activity=c.date_last_activity
            card.save()
            
    def create_missing_mastercard(self, card, master, board):
        logger.info('Adicionar ao master > {0} > {1}'.format(board.name, card.name) )
                
        mastercard = Card(remoteid=None)
        mastercard.name = card.name
        mastercard.desc = card.desc
        mastercard.boardlist = card.boardlist.parent
        mastercard.closed = card.closed
        mastercard.save()
        card.parent = mastercard
        card.save()

        if board.member:
            mastercard.members.add(board.member)

        if board.project:
            mastercard.labels.add( board.project.label(master) )

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


    def commit_updates_to_remote(self,trello, master):

        remote_labels  = {}


        for card in Card.objects.filter(boardlist__board=master).filter(
                Q(update_info=True) | Q(update_members=True) | Q(update_labels=True)
            ):

            c = card.remote_object(trello)

            if card.update_info:
                c.set_name(card.name)
                c.set_description(card.desc)
                c.set_closed(card.closed)
                card.update_info = False
                logger.info('Update info for card [{0}]'.format(card.name) )

            if card.update_members:
                members_ids = c.member_id
                for member in card.members.all():
                    members_ids.remove(member.remoteid)
                for m_id in members_ids:
                    c.unassign(m_id)
                    logger.info('Unsign member [{1}] for card [{0}]'.format(card.name, m_id) )
                card.update_members = False

            if card.update_labels:
                labels_ids = c.idLabels
                for label in card.labels.all():
                    labels_ids.remove(label.remoteid)
                for l_id in labels_ids:
                    if l_id not in remote_labels:
                        remote_labels[l_id] = trello.get_label(l_id, master.remoteid)
                    c.remove_label(remote_labels[l_id])
                    logger.info('Remove label [{1}] for card [{0}]'.format(card.name, remote_labels[l_id].name) )
                card.update_labels = False

            card.save()

    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        master = Board.objects.get(name=settings.TRELLO_MASTER)

        # SYNC ALL CARDS TO MASTER
        # Select to sync all the boards that were not marked to be removed.
        for card in Card.objects.exclude(boardlist__board=master).exclude(delete_remotely=True):
            board = card.boardlist.board

            if card.parent is None:
                # Create the card in the master board
                self.create_missing_mastercard(card, master, board)
            else:
                # check which card has the latest version and update it,
                # in the boards
                parent = card.parent
                
                if parent.name!=card.name:     parent.update_info = True
                if parent.desc!=card.desc:     parent.update_info = True
                if parent.closed!=card.closed: parent.update_info = True

                if parent.update_info:
                    parent.name = card.name
                    parent.desc = card.desc
                    parent.closed = card.closed
                    parent.save()

        self.commit_newcards_to_master(trello)
        self.commit_updates_to_remote(trello, master)
        