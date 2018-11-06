from django.db import models
from django.conf import settings
from .label import Label
from .card import Card 
from .boardlist import BoardList
import logging

logger = logging.getLogger(__name__)

class Board(models.Model):
    
    name     = models.CharField(max_length=100, unique=True)
    remoteid = models.CharField(max_length=30,  unique=True)
    closed   = models.BooleanField('Closed', null=True)
    
    member   = models.OneToOneField('Member',  on_delete=models.CASCADE, null=True, blank=True)
    project  = models.OneToOneField('Project', on_delete=models.CASCADE, null=True, blank=True)
    
    last_activity = models.DateTimeField('Last activity', null=True, blank=True)

    def label(self):
        """
        Find the label corresponding to the project
        """
        try:
            return self.project.label(self)
        except:
            return None

    def remote_object(self, trello):
        return trello.get_board(self.remoteid)

