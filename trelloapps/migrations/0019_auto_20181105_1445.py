# Generated by Django 2.1.3 on 2018-11-05 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('trelloapps', '0018_auto_20181102_1628'),
    ]

    operations = [
        migrations.AlterField(
            model_name='board',
            name='member',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='trelloapps.Member'),
        ),
        migrations.AlterField(
            model_name='board',
            name='project',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='trelloapps.Project'),
        ),
        migrations.AlterField(
            model_name='card',
            name='remoteid',
            field=models.CharField(blank=True, max_length=30, null=True, unique=True),
        ),
    ]