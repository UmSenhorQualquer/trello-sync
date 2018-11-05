from django.db import models

class Label(models.Model):
    
    name     = models.CharField(max_length=100)
    remoteid = models.CharField(max_length=30, unique=True)

    board  = models.ForeignKey('Board', on_delete=models.CASCADE, null=True)
    parent = models.ForeignKey('Label', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('board', 'name')

    def remote_object(self, trello):
        return trello.get_label(self.remoteid, self.board.remoteid)

    def __str__(self):
        return "{0}:{1}".format(self.name, self.remoteid)