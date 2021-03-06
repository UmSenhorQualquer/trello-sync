# Generated by Django 2.1.2 on 2018-10-31 22:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trelloapps', '0002_auto_20181031_2222'),
    ]

    operations = [
        migrations.AddField(
            model_name='boardlist',
            name='closed',
            field=models.BooleanField(null=True, verbose_name='Closed'),
        ),
        migrations.AddField(
            model_name='boardlist',
            name='position',
            field=models.PositiveSmallIntegerField(null=True, verbose_name='Position'),
        ),
        migrations.AddField(
            model_name='card',
            name='closed',
            field=models.BooleanField(null=True, verbose_name='Closed'),
        ),
        migrations.AddField(
            model_name='card',
            name='desc',
            field=models.TextField(null=True, verbose_name='Description'),
        ),
        migrations.AddField(
            model_name='card',
            name='position',
            field=models.PositiveSmallIntegerField(null=True, verbose_name='Position'),
        ),
    ]
