from django.db import models
from django.conf import settings



class Board(models.Model):
    
    name     = models.CharField(max_length=100, unique=True)
    remoteid = models.CharField(max_length=30,  unique=True)
    closed   = models.BooleanField('Closed', null=True)
    
    member   = models.ForeignKey('Member',  on_delete=models.CASCADE, null=True, blank=True, unique=True)
    project  = models.ForeignKey('Project', on_delete=models.CASCADE, null=True, blank=True, unique=True)
    
    last_activity = models.DateTimeField('Last activity', null=True, blank=True)


    def remote_object(self, trello):
        return trello.get_board(self.remoteid)


    def import_board(self, trello):
        from trelloapps.models import BoardList
        from trelloapps.models import Member

        print('Importing:', self.name)

        importing_master = self.name==settings.TRELLO_MASTER

        # search for the remote board
        b = self.remote_object(trello)

        if self.last_activity is not None and b.date_last_activity<=self.last_activity:
            print('No changes detected')
            return

        # IMPORT ALL LISTS IN THE BOARD
        for lst in self.boardlist_set.all():
            l = lst.remote_object(trello)
            
            lst.name     = l.name
            lst.closed   = l.closed
            lst.position = l.pos
            lst.save()

            # IMPORT ALL THE CARDS IN THE LIST
            lst.import_cards(l)

        self.last_activity = b.date_last_activity
        self.save()
       