from django.db import models

class Label(models.Model):
    
    name     = models.CharField(max_length=100)
    remoteid = models.CharField(max_length=30)

    board  = models.ForeignKey('Board', on_delete=models.CASCADE, null=True)
    parent = models.ForeignKey('Label', on_delete=models.CASCADE, null=True, blank=True)

    def remote_object(self, trello):
        return trello.get_label(self.remoteid, self.board.remoteid)