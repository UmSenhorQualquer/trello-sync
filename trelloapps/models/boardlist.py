from django.db import models



class BoardList(models.Model):
    
    name     = models.CharField(max_length=100)
    remoteid = models.CharField(max_length=30)
    position = models.IntegerField('Position', null=True)
    closed   = models.BooleanField('Closed', null=True)
    
    parent = models.ForeignKey('BoardList', on_delete=models.CASCADE, null=True, blank=True)
    board  = models.ForeignKey('Board', on_delete=models.CASCADE, null=True)

    def remote_object(self, trello):
        return trello.get_list(self.remoteid)

    def import_cards(self, lst):
        from trelloapps.models import Card
        from trelloapps.models import Member

        # GET ONLY THE LATEST UPDATES
        if self.board.last_activity:
            query = {'since': self.board.last_activity.isoformat( timespec='microseconds')}
            data  = lst.list_actions(query)
            ids   = []
            for update in data:
                card_info = update['data'].get('card', None)
                if card_info: ids.append(card_info['id'])
            cards = [lst.client.get_card(i) for i in list(set(ids))]
        else:
            cards = lst.list_cards(card_filter='all')
       
        # UPDATE THE CARDS INFO
        for c in cards:
            try:
                card = Card.objects.get(remoteid=c.id)
            except Card.DoesNotExist:
                card = Card(remoteid = c.id)

            card.name          = c.name
            card.desc          = c.description
            card.closed        = c.closed
            card.position      = c.pos
            card.boardlist     = self
            card.last_activity = c.date_last_activity
            card.save()

            card.members.through.objects.all().delete()
            for m in c.member_id:
                try:
                    card.members.add(Member.objects.get(remoteid=m))
                except Member.DoesNotExist:
                    print('member not found')
                

           