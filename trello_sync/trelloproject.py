from confapp             import conf
from trello              import TrelloClient
from bitbucket.bitbucket import Bitbucket


class TrelloProject(object):

    def __init__(self, board_name, backlog_list_name, lists_names=[]):
        self.board_name   = board_name
        self.backlog_name = backlog_list_name
        self.lists_names  = lists_names + [backlog_list_name]

        self.repos = []

        self._trello    = TrelloClient(conf.TRELLO_API_KEY, conf.TRELLO_TOKEN)
        self._bitbucket = Bitbucket(conf.BITBUCKET_USER, conf.BITBUCKET_PASSWORD)

    def add_bitbucket_repo(self, owner, repo_slug):
        self.repos.append( ('bitbucket', owner, repo_slug) )

    def __find_board(self, board_name):
        for board in self._trello.list_boards():
            if board.name==board_name:
                return board
        return None

    def __find_card(self, lists, label_name):
        for lst in lists:
            for card in lst.cards:
                if card.name==label_name:
                    return card
                    break
        return None

    def __sync_bitbucket(self, board, owner, repo_slug, backlog_list, board_lists, board_labels):
        
        success, data = self._bitbucket.issue.all(repo_slug=repo_slug, owner=owner)
        
        for issue in data['issues']:

            title    = issue.get('title',None)
            desc     = issue.get('content',None)
            priority = issue.get('priority',None)
            kind     = issue.get('metadata').get('kind')
            status   = issue.get('status',None)

            card = self.__find_card(board_lists, title)

            if card is None:
                card = backlog_list.add_card(
                    name=title,
                    desc=desc
                )
            

            priority_label = board_labels.get(priority, None)
            kind_label     = board_labels.get(kind, None)
            status_label   = board_labels.get(status, None)

            if priority_label is None:
                priority_label = board.add_label(priority, 'red')
                board_labels[priority] = priority_label

            if kind_label is None:
                kind_label = board.add_label(kind, 'green')
                board_labels[kind] = kind_label

            if status_label is None:
                status_label = board.add_label(status, 'sky')
                board_labels[status] = status_label

            card_labels = (card.labels if card.labels else [])
            
            if priority_label not in card_labels:
                card.add_label(priority_label)
            if kind_label not in card_labels:
                card.add_label(kind_label)
            if status_label not in card_labels:
                card.add_label(status_label)





    def sync(self):
        board = self.__find_board(self.board_name)
        
        # if the board does not exists create it
        if board is None:
            board = self._trello.add_board(self.board_name, default_lists=False)

        # store all the board labels.
        board_labels = dict([(l.name, l) for l in board.get_labels()])

        board_lists  = []
        lower_names  = [x.lower() for x in self.lists_names]
        for lst in board.list_lists():
            list_name = lst.name.lower()

            if list_name in lower_names:
                board_lists.append(lst)
                i = lower_names.index(list_name)
                self.lists_names.pop(i)
                lower_names.pop(i)
                lst.cards = lst.list_cards(card_filter='all')    
                
                

        for lst_name in self.lists_names:
            lst = board.add_list(lst_name)
            lst.cards = []
            board_lists.append(lst)
        
        backlog_list = None
        for lst in board_lists:
            if lst.name.lower()==self.backlog_name.lower(): 
                backlog_list = lst
                break
                


        for platform, owner, repo_slug in self.repos:

            if platform=='bitbucket':
                self.__sync_bitbucket(board, owner, repo_slug, backlog_list, board_lists, board_labels)



        







if __name__=='__main__':

    p = TrelloProject('PYBPOD', 'BACKLOG', ['TODO', 'WORKING ON', 'DONE'])

    p.add_bitbucket_repo('fchampalimaud','pybpod')

    p.sync()
