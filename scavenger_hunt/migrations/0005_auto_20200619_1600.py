# Generated by Django 3.0.3 on 2020-06-19 23:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scavenger_hunt', '0004_auto_20200619_1441'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scavengerhunt',
            name='current_location',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='scavenger_hunt.Location'),
        ),
    ]