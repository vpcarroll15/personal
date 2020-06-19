from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.http import HttpResponseNotAllowed

from .models import ScavengerHuntTemplate, ScavengerHunt


def hunt_templates(request):
    """Renders a view of all the scavenger hunt templates that can be instantiated."""
    hunt_templates = ScavengerHuntTemplate.objects.all().order_by("-updated_at")
    return render(request, 'scavenger_hunt/hunt_templates.html', {'hunt_templates': hunt_templates})


def hunt_template(request, id):
    """Renders a single hunt template detailed view."""
    hunt_template = get_object_or_404(ScavengerHuntTemplate, pk=id)
    return render(request, 'scavenger_hunt/hunt_template.html', {'hunt_template': hunt_template})


def hunt(request, id):
    """Renders a single hunt detailed view."""
    if request.method == 'GET':
        hunt = get_object_or_404(ScavengerHunt, pk=id)
        return render(request, 'scavenger_hunt/hunt.html', {'hunt': hunt})
    elif request.method == 'POST':
        # TODO: This.
        raise NotImplementedError
    return HttpResponseNotAllowed(["GET", "POST"])
