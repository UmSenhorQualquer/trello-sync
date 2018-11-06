from django.core.management.base import BaseCommand, CommandError
from trello import TrelloClient
from django.conf import settings
from trelloapps.models import Project, Member, Board, Label, BoardList

class Command(BaseCommand):
    help = 'Install Trello'

    def __search_by_name(self, name, objects):
        for obj in objects:
            if obj.name==name:
                return obj
        return None

    def __search_board_by_name(self, name, boards):
        return self.__search_by_name(name, boards)

    def __search_list_by_name(self, name, lists):
        return self.__search_by_name(name, lists)

    def __search_label_by_name(self, name, labels):
        return self.__search_by_name(name, labels)

    def __search_member_by_id(self, memberid, members):
        for obj in members:
            if obj.id==memberid:
                return obj
        return None



    def __install_lists(self, b, board, master=None):
        # get all the remote board lists
        lists = b.all_lists()

        for list_name in settings.TRELLO_LISTS:

            # for each list to install check if it exists, otherwise create it.
            l = self.__search_list_by_name(list_name, lists)
            if l is None: l = b.add_list(list_name)

            # check the the local object exists otherwise create it
            try:
                lst = BoardList.objects.get(remoteid=l.id)
            except BoardList.DoesNotExist:
                lst = BoardList(remoteid=l.id)

            lst.name=l.name
            lst.position = l.pos 
            lst.closed = l.closed
            lst.board = board

            # in the case the master board was defined associate the master board list as parent
            if master is not None:
                lst.parent = master.boardlist_set.get(name=lst.name)

            lst.save()

    def __install_labels(self, b, board, master=None):
        labels = b.get_labels()

        for label_name in settings.TRELLO_PROJECTS:
            l = self.__search_label_by_name(label_name, labels)
            if l is None: l = b.add_label(label_name, 'red')

            # check the the local object exists otherwise create it
            try:
                label = Label.objects.get(remoteid=l.id)
            except Label.DoesNotExist:
                label = Label(remoteid=l.id)

            label.name = l.name
            label.board = board
            
            # in the case the master board was defined associate the master board list as parent
            if master is not None:
                label.parent = master.label_set.get(name=label.name)
            label.save()


    def __install_members(self, b):

        # Add all members to the database
        for member_id in settings.TRELLO_MEMBERS.keys():
            # check the the local object exists otherwise create it
            try:
                member = Member.objects.get(remoteid=member_id)
            except Member.DoesNotExist:
                m = b.client.get_member(member_id)
                member = Member(remoteid=member_id, name=m.username)
                member.save()

        # Add all members to the board
        members = b.all_members()
        for member_id in settings.TRELLO_MEMBERS.keys():
            m = self.__search_member_by_id(member_id, members)
            if m is None:
                m = b.client.get_member(member_id)
                b.add_member(m)


    def __install_projects_boards(self, trello, master, boards):
        
        # CREATE THE PROJECTS BOARDS
        for proj_name in settings.TRELLO_PROJECTS:
            
            # create the project in the database
            try:
                prj = Project.objects.get(name=proj_name)
            except Project.DoesNotExist:
                prj = Project(name=proj_name)
                prj.save()

            # check if the remote boards exists
            b = self.__search_board_by_name(proj_name, boards)

            # if the remote board does not exists create it
            if b is None: b = trello.add_board(proj_name, default_lists=False)

            # check if the board exists otherwise create it
            try:
                board = Board.objects.get(remoteid=b.id)
            except Board.DoesNotExist:
                board = Board(remoteid=b.id)

            board.name      = proj_name
            board.closed    = False
            board.project   = prj
            board.last_activity = None
            board.save()

            self.__install_lists(b, board, master)
            self.__install_labels(b, board, master)
            self.__install_members(b)

    def __install_members_boards(self, trello, master, boards):
        
        # CREATE THE PROJECTS BOARDS
        for member_id, board_name in settings.TRELLO_MEMBERS.items():

            member = Member.objects.get(remoteid=member_id)

            # check if the remote boards exists
            b = self.__search_board_by_name(board_name, boards)
            # if the remote board does not exists create it
            if b is None: b = trello.add_board(board_name, default_lists=False)

            # check if the board exists otherwise create it
            try:
                board = Board.objects.get(remoteid=b.id)
            except Board.DoesNotExist:
                board = Board(remoteid=b.id)

            board.name = board_name
            board.closed = False
            board.member = member
            board.last_activity = None
            board.save()

            self.__install_lists(b, board, master)
            self.__install_labels(b, board, master)
            self.__install_members(b)


    def handle(self, *args, **options):
        trello = TrelloClient(settings.TRELLO_API_KEY, settings.TRELLO_TOKEN)
        boards = trello.list_boards()

        #######################################################################
        # INSTALL THE MASTER BOARD ############################################
        #######################################################################
        
        # check if the board exists 
        m = self.__search_board_by_name(settings.TRELLO_MASTER, boards)
        
        # if not create it
        if m is None: m = trello.add_board(settings.TRELLO_MASTER, default_lists=False)

        try:
            master = Board.objects.get(remoteid=m.id)
        except Board.DoesNotExist:
            master = Board(remoteid=m.id)
        
        master.name = m.name
        master.closed = m.closed
        master.last_activity = None
        master.save()

        self.__install_lists(m, master)
        self.__install_labels(m, master)
        self.__install_members(m)
        #######################################################################

        self.__install_projects_boards(trello, master, boards)

        self.__install_members_boards(trello, master, boards)
