from django.db import models

class Member(models.Model):
    
    name     = models.CharField(max_length=100)
    remoteid = models.CharField(max_length=30, unique=True)

    
    def remote_object(self, trello):
        return trello.get_member(self.remoteid)

    def __str__(self):
    	return self.name