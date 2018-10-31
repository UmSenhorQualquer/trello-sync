from confapp             import conf
from trello              import TrelloClient
from bitbucket.bitbucket import Bitbucket


class TrelloMasterBoard(object):

    def __init__(self, master_boardname, sync_boards, sync_lists):
        self.master_boardname = master_boardname
        self.sync_boards      = sync_boards
        self.sync_lists       = sync_lists

        self._trello    = TrelloClient(conf.TRELLO_API_KEY, conf.TRELLO_TOKEN)

    def __find_board(self, board_name):
        for board in self._trello.list_boards():
            if board.name==board_name:
                return board
        return None


    def __get_lists(self, board, lists_names):
        lists = []
        names = [x.lower() for x in lists_names]
       
        # search for the lists
        for lst in board.list_lists():
            if lst.name.lower() in names:
                lists.append(lst)
       
        return lists

    def __get_and_create_lists(self, board, lists_names):
        """
        Search for the lists in the board. If they do not exists create them
        """
        lists = []
        names = [x.lower() for x in lists_names]
        lists_names = list(lists_names) # make a copy

        # search for the lists
        for lst in board.list_lists():
            name = lst.name.lower()

            if name in names:
                lists.append(lst)
                i = names.index(name)
                lists_names.pop(i)
                names.pop(i)
                
        # create the non existing lists
        for lst_name in lists_names:
            lst = board.add_list(lst_name)
            lists.append(lst)

        return lists

    def __card_id(self, card):
        if card.description.startswith('card-id:'):
            return card.description[8:32]
        else:
            return card.id

    def __get_label(self, board, label_name):

        if not hasattr(board, 'labels'):
            board.labels = dict([ (l.name, l) for l in board.get_labels(limit=100) ])
            
        label = board.labels.get(label_name, None)
        if label is None: 
            label = board.add_label(label_name, 'red')
            board.labels[label_name]=label
        return label


    def sync(self):
        #### FIND THE MASTER BOARD OR CREATE IT ###############################################
        masterboard = self.__find_board(self.master_boardname)
        if masterboard is None:
            masterboard = self._trello.add_board(self.master_boardname, default_lists=False)
        #######################################################################################

        #### GET ALL THE BOARD LISTS ##########################################################
        mboard_lists    = dict([(l.name.lower(), l) for l in self.__get_and_create_lists(masterboard, self.sync_lists)])
        mboard_listsids = dict([(l.id, l) for l in mboard_lists.values()])
        #######################################################################################

        #### GET ALL THE BOARD CARDS IN THE LISTS #############################################
        mboard_cardsids = {}
        for lst in mboard_lists.values():
            for c in lst.list_cards(card_filter='all'):
                mboard_cardsids[self.__card_id(c)] = c
        #######################################################################################
        

        boards = {}
        boards_lists = {}
        boards_cards = {}

        for board_name in self.sync_boards:
            board = self.__find_board(board_name)

            boards[board_name.lower()] = board
            lists    = dict([(l.name.lower(), l) for l in self.__get_and_create_lists(board, self.sync_lists)])
            listsids = dict([(l.id, l) for l in lists.values()])

            if board.id not in boards_lists:
                boards_lists[board.id] = {}
            boards_lists[board.id].update(lists)

            for list_name, lst in lists.items():
                cards = lst.list_cards(card_filter='all')
    
                if board_name.lower() not in boards_cards:
                    boards_cards[board_name.lower()] = {}



                for card in cards:
                    card_id     = self.__card_id(card)
                    boards_cards[board_name.lower()][card_id] = card

                    ### GET THE MASTER CARD, IF DOES NOT EXISTS CREATE IT #####################
                    master_card = mboard_cardsids.get(card_id, None)
                    if master_card is None:
                        master_card  = mboard_lists[list_name].add_card(card.name, "card-id:{0}".format( card.id ))
                        master_card.set_closed(card.closed)
                        master_label = self.__get_label(masterboard, board_name)
                        master_card.add_label(master_label)
                    ###########################################################################

                    ### CHECK WITCH CARD SHOULD BE UPDATED ####################################
                    if master_card.dateLastActivity<card.dateLastActivity:
                        card_to   = master_card
                        card_from = card
                        lists_id_to   = mboard_listsids
                        lists_id_from = listsids
                        lists_to   = mboard_lists
                        lists_from = lists
                    else:
                        card_to   = card
                        card_from = master_card
                        lists_id_to   = listsids
                        lists_id_from = mboard_listsids
                        lists_to   = lists
                        lists_from = mboard_lists
                    ###########################################################################

                    ### UPDATE THE NAME IF NECESSARY ##########################################
                    if card_from.name!=card_to.name:
                        card_to.set_name(card_from.name)
                    ###########################################################################

                    ### UPDATE THE NAME IF NECESSARY ##########################################
                    if card_from.closed!=card_to.closed:
                        card_to.set_closed(card_from.closed)
                    ###########################################################################


                    ### UPDATE THE DESCRIPTION IF NECESSARY ###################################
                    from_desc = card_from.description
                    to_desc   = card_to.description
                    if from_desc.startswith('card-id'): from_desc = from_desc[33:]
                    if to_desc.startswith('card-id'):   to_desc   = to_desc[33:]
                    if from_desc!=to_desc:
                        card_to.set_description( "card-id:{0}\n{1}".format( card_id, from_desc ))
                    ###########################################################################

                    ### UPDATE THE LIST IF NECESSARY ##########################################
                    list_to   = lists_id_to[card_to.list_id]
                    list_from = lists_id_from[card_from.list_id]
                    if list_to.name.lower()!=list_from.name.lower():
                        new_lst = lists_to[list_from.name.lower()]
                        card_to.change_list(new_lst.id)
                    ###########################################################################



        for card_id, card in mboard_cardsids.items():
            print(card.plugin_data)
            labels = card.labels if card.labels else []
            for label in labels:
                board    = boards.get(label.name.lower(), None)
                if board is None: continue

                if card_id not in boards_cards[board.name.lower()]:
                    old_list = mboard_listsids[card.list_id]
                    new_list = boards_lists[board.id][old_list.name.lower()]
                    new_list.add_card(card.name, "card-id:{0}\n{1}".format(card_id, card.description) )






if __name__=='__main__':

    p = TrelloMasterBoard(
        'MASTER',
        ['PYBPOD', 'CORE', 'IDTRACKER.AI', 'VIDEO ANNOTATOR', 'HUGO CACHITAS', 'RICARDO RIBEIRO', 'BAÚTO', 'PYFORMS'],
        ['BACKLOG', 'TODO', 'WORKING ON', 'DONE']
    )

    p.sync()
