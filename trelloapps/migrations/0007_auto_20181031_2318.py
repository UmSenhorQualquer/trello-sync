# Generated by Django 2.1.2 on 2018-10-31 23:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trelloapps', '0006_card_childs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='name',
            field=models.CharField(max_length=300),
        ),
    ]
