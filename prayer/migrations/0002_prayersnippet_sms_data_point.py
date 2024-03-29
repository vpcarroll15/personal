# Generated by Django 4.1.7 on 2023-04-05 02:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sms", "0007_question_callback"),
        ("prayer", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="prayersnippet",
            name="sms_data_point",
            field=models.ForeignKey(
                blank=True,
                help_text="If this was created from an SMS message, we want to record it.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="sms.datapoint",
            ),
        ),
    ]
