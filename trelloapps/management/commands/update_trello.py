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




            
    def create_missing_mastercard(self, card, master, board):
        """
        create the master card.
        """
        logger.info('Adicionar ao master > {0} > {1}'.format(board.name, card.name) )
                
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

        # IT WAS USED FOR THE FIRST IMPORT, WHERE THERE WERE CARDS REPEATED IN THE PROJECTS AND MEMBERS BOARDS
        # # store all the cards associated to the current card.
        # # the variable is used to update the last state of the cards in the master 
        # allcards = [card]
        
        # # search for cards in other boards with the same name
        # for tmp in Card.objects.exclude(
        #     boardlist__board__in=[master,board]).filter(
        #     name=card.name, parent=None):
            
        #     tmp.parent = mastercard

        #     if tmp.boardlist.board.member:
        #         mastercard.members.add(tmp.boardlist.board.member)

        #     if tmp.boardlist.board.project:
        #         mastercard.labels.add( tmp.boardlist.board.project.label(master) )
           
        #     tmp.save()

        #     allcards.append(tmp)

        # allcards = sorted(allcards, key=lambda x:x.last_activity, reverse=True)
        # lastupdated_card = allcards[0]
        # mastercard.boardlist=lastupdated_card.boardlist.parent
        # mastercard.closed=lastupdated_card.closed
        
        mastercard.save()


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

      



    def compute_modifications(self, master):

        # SYNC ALL CARDS TO MASTER
        # Select to sync all the boards that were not marked to be removed.
        for card in Card.objects.exclude(boardlist__board=master).exclude(delete_remotely=True).order_by('last_activity'):
            if card.parent is None:
                # Create the card in the master board
                self.create_missing_mastercard(card, master, card.boardlist.board)

        for card in Card.objects.filter(
                Q(update_name=True) | Q(update_desc=True) | Q(update_closed=True) | 
                Q(update_members=True) | Q(update_labels=True) | Q(update_list=True) | Q(delete_remotely=True)
            ).order_by('last_activity'):

            if card.delete_remotely:
                label  = card.boardlist.board.label()
                member = card.boardlist.board.member

                logger.info(
                    "Found removed card [{1} > {2} > {0}]".format( card.name, card.boardlist.board.name, card.boardlist.name)
                )

                if card.parent:
                    if label:
                        try:
                            card.parent.labels.remove(label.parent)
                            card.parent.update_labels = True
                            card.parent.save()
                        except ValueError:
                            pass

                    if member:
                        try:
                            card.parent.members.remove(member)
                            card.parent.update_members = True
                            card.parent.save()
                        except ValueError:
                            pass

                    card.save()
                else:
                    for child in card.card_set.all():
                        child.delete_remotely = True
                        child.save()
                    card.delete()

            siblings = Card.objects.filter( Q(parent=card.parent) | Q(pk=card.parent.pk) ) if card.parent else Card.objects.filter( Q(parent=card) | Q(pk=card.pk) )
            siblings = siblings.order_by('-last_activity')

            # NAME
            if card.update_name:
                updated = siblings.filter(update_name=True)
                
                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling name [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    c.name = ref.name
                    c.update_name = True
                    c.save()

            # DESCRIPTION
            if card.update_desc:
                updated = siblings.filter(update_desc=True)

                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling description [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    c.desc = ref.desc
                    c.update_desc = True
                    c.save()

            # CLOSED
            if card.update_closed:
                updated = siblings.filter(update_closed=True)
                
                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling closed [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                    c.closed = ref.closed
                    c.update_closed = True
                    c.save()

            # BOARD LIST
            if card.update_list:
                updated = siblings.filter(update_list=True)
                
                ref = updated[0]
                for c in siblings:
                    logger.info("Update sibling list [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
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
                        c.delete_remotely = True
                        c.save()

                    for member in card.members.all():
                        try:
                            obj = Card.objects.get(boardlist__board__member=member, parent=card)
                        except Card.DoesNotExist:
                            blist = BoardList.objects.get(board__member=member, name=card.boardlist.name)
                            obj = Card(name=card.name, desc=card.desc, closed=card.closed, boardlist=blist, parent=card)
                            obj.save()
                            logger.info("[MEMBERS] Created the card [{1} > {2} > {0}]".format( obj.name, obj.boardlist.board.name, obj.boardlist.name))
                        
                # LABELS
                if card.update_labels:
                    cards_to_remove = siblings.exclude(pk=card.pk).exclude(boardlist__board__project=None)
                    cards_to_add    = card.labels.all()
                    
                    for label in card.labels.all():
                        cards_to_remove = cards_to_remove.exclude(boardlist__board__name=label.name)

                    for c in cards_to_remove:
                        logger.info("[LABELS] Remove card [{1} > {2} > {0}]".format( c.name, c.boardlist.board.name, c.boardlist.name))
                        c.delete_remotely = True
                        c.save()
                    
                    for label in card.labels.all():
                        try:
                            obj = Card.objects.get(boardlist__board__name=label.name, parent=card)
                        except Card.DoesNotExist:
                            blist = BoardList.objects.get(board__project__name=label.name, name=card.boardlist.name)
                            obj = Card(name=card.name, desc=card.desc, closed=card.closed, boardlist=blist, parent=card)
                            obj.save()
                            logger.info("[LABELS] Created the card [{1} > {2} > {0}]".format( obj.name, obj.boardlist.board.name, obj.boardlist.name))
                        


    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        master = Board.objects.get(name=settings.TRELLO_MASTER)

        

        self.compute_modifications(master)
        self.commit_updates_to_remote(trello, master)
        self.commit_newcards_to_remote(trello, master)
        