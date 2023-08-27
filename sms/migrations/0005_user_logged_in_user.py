# Generated by Django 3.0.7 on 2021-01-06 04:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("sms", "0004_auto_20201117_1256"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="logged_in_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
