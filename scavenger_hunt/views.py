from django.shortcuts import render

from .models import ScavengerHuntTemplate


def list_hunt_templates(request):
    """Renders a view of all the scavenger hunt templates that can be instantiated."""
    hunt_templates = ScavengerHuntTemplate.objects.all().order_by("-updated_at")
    context = {'hunt_templates': hunt_templates}
    return render(request, 'scavenger_hunt/hunt_templates.html', context)
