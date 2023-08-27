from django.core import mail
from django.utils.html import strip_tags
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from prayer.models import PrayerSchema
from prayer.permissions import UserInEmailTriggererGroup


class EmailTriggererView(APIView):
    permission_classes = [IsAuthenticated, UserInEmailTriggererGroup]

    def post(self, request):
        for schema in PrayerSchema.objects.all():
            if not schema.should_generate():
                continue
            html_prayer = schema.render()

            mail.send_mail(
                subject=schema.name,
                message=strip_tags(html_prayer),
                html_message=html_prayer,
                from_email=None,
                recipient_list=[schema.user.email],
                fail_silently=False,
            )
            schema.update_next_generation_time()
        return Response(
            {},
            status=status.HTTP_200_OK,
        )
