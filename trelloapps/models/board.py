from django.db import models
from django.conf import settings



class Board(models.Model):
    
    name     = models.CharField(max_length=100)
    remoteid = models.CharField(max_length=30)
    closed   = models.BooleanField('Closed', null=True)
    
    member   = models.ForeignKey('Member', on_delete=models.CASCADE, null=True, blank=True)
    project  = models.ForeignKey('Project', on_delete=models.CASCADE, null=True, blank=True)
    
    last_activity = models.DateTimeField('Last activity', null=True)

    def remote_object(self, trello):
        return trello.get_board(self.remoteid)

    @staticmethod
    def __find_board(trello, name):
        for board in trello.list_boards():
            if board.name==name:
                return board

    @staticmethod
    def import_board(trello, name):
        print('import ', name)

        importing_master = name==settings.TRELLO_MASTER

        from trelloapps.models import BoardList
        from trelloapps.models import Member

        # search for the remote board
        b = Board.__find_board(trello, name)
        if b is None:
            raise Exception('Board [{0}] not found'.format(name))
            
        # IMPORT THE BOARD
        try:
            # check if the board already exists in the database
            board = Board.objects.get(remoteid=b.id)
            # No modifications
            if board.last_activity is not None and board.last_activity>=b.date_last_activity:
                print('No modifications detected')
                return

        except Board.DoesNotExist:
            # if not, import the board from trello
            board = Board(remoteid=b.id)
            
        board.name          = b.name 
        board.closed        = b.closed
        board.save()

        # IMPORT ALL LISTS IN THE BOARD
        for l in b.list_lists():

            if l.name.upper() in settings.TRELLO_LISTS:
                try:
                    boardlist = BoardList.objects.get(remoteid=l.id)
                except BoardList.DoesNotExist:
                    boardlist = BoardList(remoteid=l.id)

                boardlist.name     = l.name
                boardlist.board    = board
                boardlist.closed   = l.closed
                boardlist.position = l.pos

                if not importing_master:
                    boardlist.parent = BoardList.objects.get(
                        board__name=settings.TRELLO_MASTER,
                        name = l.name.upper()
                    )

                boardlist.save()

                # IMPORT ALL THE CARDS IN THE LIST
                boardlist.import_cards(l)

        
        
        board.last_activity = b.date_last_activity
        board.save()
       