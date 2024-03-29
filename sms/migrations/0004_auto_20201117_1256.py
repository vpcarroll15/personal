# Generated by Django 3.0.7 on 2020-11-17 20:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sms", "0003_user_expire_message_after"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="end_text_hour",
            field=models.SmallIntegerField(default=22),
        ),
        migrations.AddField(
            model_name="user",
            name="start_text_hour",
            field=models.SmallIntegerField(default=7),
        ),
        migrations.AddField(
            model_name="user",
            name="text_every_n_days",
            field=models.SmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="user",
            name="timezone",
            field=models.CharField(default="America/Los_Angeles", max_length=100),
        ),
    ]
