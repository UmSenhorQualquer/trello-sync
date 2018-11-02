from django.db import models

class Card(models.Model):
    
    name     = models.TextField('Name')
    remoteid = models.CharField(max_length=30)
    desc     = models.TextField('Description', null=True)
    position = models.IntegerField('Position', null=True)
    closed   = models.BooleanField('Closed', null=True)
    last_activity = models.DateTimeField('Last activity', null=True)

    members   = models.ManyToManyField('Member')
    boardlist = models.ForeignKey('BoardList', on_delete=models.CASCADE, null=True)

    parent = models.ForeignKey('Card', on_delete=models.CASCADE, null=True, blank=True)


    def remote_object(self, trello):
        return trello.get_card(self.remoteid)