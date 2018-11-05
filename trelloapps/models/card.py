from django.db import models

class Card(models.Model):
    
    name     = models.TextField('Name')
    remoteid = models.CharField(max_length=30, unique=True, null=True, blank=True)
    desc     = models.TextField('Description', null=True)
    position = models.IntegerField('Position', null=True)
    closed   = models.BooleanField('Closed', null=True)
    last_activity = models.DateTimeField('Last activity', null=True)

    update_info    = models.BooleanField('Update info',    default=False)
    update_members = models.BooleanField('Update members', default=False)
    update_labels  = models.BooleanField('Update labels',  default=False)
    delete_remotely = models.BooleanField('Marked to delete remotely', default=False)

    members   = models.ManyToManyField('Member')
    labels    = models.ManyToManyField('Label')
    boardlist = models.ForeignKey('BoardList', on_delete=models.CASCADE, null=True)

    parent = models.ForeignKey('Card', on_delete=models.CASCADE, null=True, blank=True)


    def remote_object(self, trello):
        return trello.get_card(self.remoteid)