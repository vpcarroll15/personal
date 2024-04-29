# Generated by Django 4.1.13 on 2024-04-28 19:22

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("daily_goals", "0002_user_last_end_text_sent_date_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="dailycheckin",
            name="chosen_focus_areas",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(),
                blank=True,
                help_text="The focus areas the user chose to focus on today.",
                null=True,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="dailycheckin",
            name="possible_focus_areas",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.TextField(),
                help_text="The focus areas the user could choose from (suggested by default).",
                size=None,
            ),
        ),
    ]