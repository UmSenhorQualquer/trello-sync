from django.db import models

class Card(models.Model):
    
    name     = models.TextField('Name')
    remoteid = models.CharField(max_length=30, unique=True, null=True, blank=True)
    desc     = models.TextField('Description', null=True)
    position = models.IntegerField('Position', null=True)
    closed   = models.BooleanField('Closed', null=True)
    last_activity = models.DateTimeField('Last activity', null=True)

    update_name    = models.BooleanField('Update name',    default=False)
    update_desc    = models.BooleanField('Update desc',    default=False)
    update_closed  = models.BooleanField('Update closed',  default=False)
    update_members = models.BooleanField('Update members', default=False)
    update_labels  = models.BooleanField('Update labels',  default=False)
    update_list    = models.BooleanField('Update list',    default=False)
    delete_remotely = models.BooleanField('Marked to delete remotely', default=False)

    members   = models.ManyToManyField('Member')
    labels    = models.ManyToManyField('Label')
    boardlist = models.ForeignKey('BoardList', on_delete=models.CASCADE, null=True)

    parent = models.ForeignKey('Card', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return "{board} > {list} > ({pk}) {name}".format(
            board=self.boardlist.board.name, 
            list=self.boardlist.name, 
            name=self.name, 
            pk=self.pk
        )

    def remote_object(self, trello):
        return trello.get_card(self.remoteid)

    def update_members_by_id(self, trello, members_ids):
        from .member import Member

        to_remove  = []
        ids_to_add = members_ids

        for member in self.members.all():
            try:
                # the remaining members in the list, should be added
                ids_to_add.remove(member.remoteid)
            except ValueError:
                to_remove.append(member)

        if ids_to_add or to_remove: 
            self.update_members = True
            self.save()

        for mid in ids_to_add:
            try:
                member = Member.objects.get(remoteid=mid)
            except Member.DoesNotExist:
                m = trello.get_member(mid)
                member = Member(remoteid=m.id, name=m.username)
                member.save()
            self.members.add(member)

        for member in to_remove:
            self.members.remove(member)


    def update_labels_by_id(self, trello, labels_ids):
        from .label import Label

        to_remove  = []
        ids_to_add = labels_ids

        for label in self.labels.all():
            try:
                # the remaining label in the list, should be added
                ids_to_add.remove(label.remoteid)
            except ValueError:
                to_remove.append(label)

        for lid in ids_to_add:
            try:
                label = Label.objects.get(remoteid=lid)
                self.labels.add(label)
                self.update_labels = True
            except Label.DoesNotExist:
                pass

        for label in to_remove:
            self.update_labels = True
            self.labels.remove(label)

        self.save()