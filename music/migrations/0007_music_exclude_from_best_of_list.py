# Generated by Django 2.2.7 on 2019-12-08 23:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("music", "0006_music_very_short_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="music",
            name="exclude_from_best_of_list",
            field=models.BooleanField(default=False),
        ),
    ]
