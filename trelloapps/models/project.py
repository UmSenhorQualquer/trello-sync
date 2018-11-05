from django.db import models
from .label import Label

class Project(models.Model):
    
    name = models.CharField(max_length=100, unique=True)
    
    def label(self, board):
        """
        Find the label corresponding to the project
        """
        try:
            return Label.objects.get(board=board, name=self.name)
        except Label.DoesNotExist:
            return None

    