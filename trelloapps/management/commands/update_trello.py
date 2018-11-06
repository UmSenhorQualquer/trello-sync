from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Board, Card, BoardList, Project, Member, Label
from django.db.models import Q
from trello.exceptions import ResourceUnavailable
import logging

from .fake_update_trello import Command as FakeCommand

logger = logging.getLogger(__name__)

class Command(FakeCommand):
    help = 'Import Trello'

    def add_arguments(self, parser):
        pass

    def commit_newcards_to_remote(self, trello, master):
        """
        Add all the new cards remotely to the master
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
            card.last_activity = c.date_last_activity
            card.save()




     


    def commit_updates_to_remote(self,trello, master):

        labels = {}

        for card in Card.objects.exclude(remoteid=None).filter(
                Q(update_name=True)    | Q(update_desc=True) | Q(update_closed=True) | 
                Q(update_members=True) | Q(update_labels=True) | Q(update_list=True) | Q(delete_remotely=True)
            ).order_by('last_activity'):

           

            try:
                c = card.remote_object(trello)
            except ResourceUnavailable:
                logger.error("Card [{1} > {2} > {0}] does not exists remotely".format( card.name, card.boardlist.board.name, card.boardlist.name))  
                card.delete()
                logger.info("Delete card [{1} > {2} > {0}]".format( card.name, card.boardlist.board.name, card.boardlist.name))  
                continue

            if card.delete_remotely:
                logger.error("Delete local and remote card [{1} > {2} > {0}]".format( card.name, card.boardlist.board.name, card.boardlist.name))  
                c.delete()
                card.delete()
                continue

            if card.update_name:
                c.set_name(card.name)
                card.update_name = False
                logger.info('Updated [name] for card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name) )

            if card.update_desc:
                c.set_description(card.desc)
                card.update_desc = False
                logger.info('Updated [description] for card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name) )

            if card.update_closed:
                c.set_closed(card.closed)
                card.update_closed = False
                logger.info('Updated [closed] for card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name) )

            if card.update_list:
                c.change_list(card.boardlist.remoteid)
                card.update_list = False
                logger.info('Moved [card] [{1} > {2} > {0}] to list [{3}]'.format(card.name, card.boardlist.board.name, card.boardlist.name, card.boardlist.name) )

            if card.update_members:
                members_ids = c.member_id
                for member in card.members.all():
                    if member.remoteid not in members_ids:
                        logger.info('Assign member [{3}] for card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name, member.remoteid) )
                        c.assign(member.remoteid)
                    else:
                        members_ids.remove(member.remoteid)
                for m_id in members_ids:
                    c.unassign(m_id)
                    logger.info('Unsign member [{3}] for card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name, m_id) )
                card.update_members = False



            if card.update_labels:
                labels_ids = c.idLabels
                
                for label in card.labels.all():
                    if label.remoteid not in labels_ids:

                        if label.remoteid not in labels:
                            labels[label.remoteid] = trello.get_label(label.remoteid, card.boardlist.board.remoteid)
                        logger.info('Add label [{3}] for card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name, labels[label.remoteid].name) )
                        c.add_label(labels[label.remoteid])
                    else:
                        labels_ids.remove(label.remoteid)

                for l_id in labels_ids:
                    if l_id not in labels:
                        labels[l_id] = trello.get_label(l_id, card.boardlist.board.remoteid)
                    c.remove_label(labels[l_id])
                    logger.info('Remove label [{3}] from card [{1} > {2} > {0}]'.format(card.name, card.boardlist.board.name, card.boardlist.name, labels[l_id].name) )
                
                card.update_labels = False

            card.save()


    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        master = Board.objects.get(name=settings.TRELLO_MASTER)

        self.compute_modifications(master)
        self.commit_updates_to_remote(trello, master)
        self.commit_newcards_to_remote(trello, master)
        