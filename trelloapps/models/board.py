from django.db import models
from django.conf import settings
from .label import Label
from .card import Card 
from .boardlist import BoardList
import logging

logger = logging.getLogger(__name__)

class Board(models.Model):
    
    name     = models.CharField(max_length=100, unique=True)
    remoteid = models.CharField(max_length=30,  unique=True)
    closed   = models.BooleanField('Closed', null=True)
    
    member   = models.OneToOneField('Member',  on_delete=models.CASCADE, null=True, blank=True)
    project  = models.OneToOneField('Project', on_delete=models.CASCADE, null=True, blank=True)
    
    last_activity = models.DateTimeField('Last activity', null=True, blank=True)

    def label(self):
        """
        Find the label corresponding to the project
        """
        try:
            return self.project.label(self)
        except:
            return None

    def remote_object(self, trello):
        return trello.get_board(self.remoteid)


    def import_board(self, trello):
        from trelloapps.models import BoardList
        from trelloapps.models import Member

        master = Board.objects.get(name=settings.TRELLO_MASTER)
        print('Importing:', self.name)

        # search for the remote board
        b = self.remote_object(trello)

        # check if the board was updated since the last update
        if self.last_activity is not None and b.date_last_activity<=self.last_activity:
            print('No changes detected')
            return

        # if is the first update then import all the lists from the board.
        if not self.last_activity:
            for lst in self.boardlist_set.all():
                l = lst.remote_object(trello)
                lst.name     = l.name
                lst.closed   = l.closed
                lst.position = l.pos
                lst.save()
                lst.import_cards(l)

       
        # if is not the first board update, update only the latest modifications
        if self.last_activity:

            # the board was already imported once
            query = {'since': self.last_activity.isoformat( timespec='microseconds')}
            data  = trello.fetch_json('/boards/' + self.remoteid + '/actions', query_params=query)
            ids   = []
            for update in data:
                action_type = update.get('type',None)
                card_info   = update['data'].get('card', None)

                if card_info:
                    card_id     = card_info['id']
                    
                    if action_type=='deleteCard':
                        try:
                            card = Card.objects.get(remoteid=card_id)

                            if card.boardlist.board.name==settings.TRELLO_MASTER:
                                logger.info("The card [{0}] was removed from the master".format(card.name))

                                # if the delete was done in the board master, remove all the boards in the other boards
                                for tmp in Card.objects.filter(parent=card):
                                    tmp.parent = None
                                    tmp.delete_remotely = True
                                    tmp.save()
                                    logger.info("The card [{0}] in the board [{1}] was marked to be removed".format(tmp.name, tmp.boardlist.board.name))

                                card.delete()

                            elif card.parent:
                                # the card exists in the master, remove all the associations of this board in the master
                                if card.boardlist.board.project:
                                    proj  = card.boardlist.board.project
                                    label = proj.label(master)
                                    card.parent.labels.remove(label)
                                    card.parent.update_labels = True
                                    logger.info("Remove the label [{1}] from the card [{0}] in the master".format(card.name, label.name))
                                    card.parent.save()

                                if card.boardlist.board.member:
                                    card.parent.members.remove(card.boardlist.board.member)
                                    logger.info("Remove the member [{1}] from the card [{0}] in the master".format(card.name, card.boardlist.board.member.name))
                                    card.parent.update_members = True
                                    card.parent.save()

                                logger.info("The card [{0}] was removed from the board [{1}]".format(card.name, card.boardlist.board.name))
                                card.delete()
                            else:
                                # the card only exists in this board, remove it from the database
                                card.delete()

                        except Card.DoesNotExist:
                            # ignore
                            pass
                    else:
                        ids.append(card_id)
                    
            cards = [trello.get_card(i) for i in list(set(ids))]

            lists = {}
            for c in cards:
                try:
                    card = Card.objects.get(remoteid=c.id)
                except Card.DoesNotExist:
                    card = Card(remoteid = c.id)
                
                if c.list_id not in lists:
                    lists[c.list_id] = BoardList.objects.get(board=self, remoteid=c.list_id)

                boardlist = lists[c.list_id]
                
                card.name          = c.name
                card.desc          = c.description
                card.closed        = c.closed
                card.position      = c.pos
                card.boardlist     = boardlist
                card.last_activity = c.date_last_activity
                card.save()

                card.members.through.objects.all().delete()
                for mid in c.member_id:
                    try:
                        member = Member.objects.get(remoteid=mid)
                    except Member.DoesNotExist:
                        m = trello.get_member(mid)
                        member = Member(remoteid=m.id, name=m.username)
                        member.save()
                    card.members.add(member)



        self.last_activity = b.date_last_activity
        self.save()