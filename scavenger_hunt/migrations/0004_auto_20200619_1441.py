# Generated by Django 3.0.3 on 2020-06-19 21:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scavenger_hunt", "0003_auto_20200619_1417"),
    ]

    operations = [
        migrations.RenameField(
            model_name="scavengerhunt", old_name="hunt", new_name="hunt_template",
        ),
    ]
