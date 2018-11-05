# Generated by Django 2.1.3 on 2018-11-05 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trelloapps', '0021_card_marker_to_update'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='card',
            name='marker_to_update',
        ),
        migrations.AddField(
            model_name='card',
            name='marker_to_delete',
            field=models.BooleanField(default=False, verbose_name='Marked to delete'),
        ),
    ]