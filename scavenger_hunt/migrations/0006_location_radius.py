# Generated by Django 3.0.7 on 2020-07-03 23:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scavenger_hunt", "0005_auto_20200619_1600"),
    ]

    operations = [
        migrations.AddField(
            model_name="location",
            name="radius",
            field=models.IntegerField(
                default=30,
                help_text="How close the user needs to be in meters to the coordinate in order to advance.",
            ),
        ),
    ]
