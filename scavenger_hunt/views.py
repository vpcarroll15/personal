from django.shortcuts import render
from django.shortcuts import get_object_or_404

from .models import ScavengerHuntTemplate


def list_hunt_templates(request):
    """Renders a view of all the scavenger hunt templates that can be instantiated."""
    hunt_templates = ScavengerHuntTemplate.objects.all().order_by("-updated_at")
    return render(request, 'scavenger_hunt/hunt_templates.html', {'hunt_templates': hunt_templates})


def hunt_template(request, hunt_template_id):
    """Renders a single hunt template detailed view."""
    hunt_template = get_object_or_404(ScavengerHuntTemplate, pk=hunt_template_id)
    return render(request, 'scavenger_hunt/hunt_template.html', {'hunt': hunt_template})