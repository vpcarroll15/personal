from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseNotAllowed, HttpResponse

from .models import ScavengerHuntTemplate, ScavengerHunt, Location


DEFAULT_SCAVENGER_HUNT_RADIUS_M = 50


def _get_next_location(location_ids, current_location=None):
    """
    Get the next Location that we should visit, given a sequence of location ids and the current location.

    Returns a tuple with the Location and whether we successfully fetched it.
    (Returns None if we think that we have finished the hunt.)

    If we encounter anything strange, then we return a Response with an error message.
    This should be propagated back to the user.
    """
    error_response = "This hunt appears to be broken. Please contact Paul to fix. Issue: "
    # Check if there are duplicate location ids.
    if len(set(location_ids)) != len(location_ids):
        return HttpResponse(reason=error_response + "duplicate location ids", status=400), False

    # Get all the elements after the current location id.
    current_index = -1
    if current_location is not None:
        try:
            current_index = location_ids.index(current_location.id)
        except ValueError:
            return HttpResponse(reason=error_response + "invalid current location", status=400), False
    next_index = current_index + 1
    # We interpret this as "you are done with the hunt."
    if next_index >= len(location_ids):
        return None, True
    
    # Get that Location from the DB (if it exists) and return it.
    next_location_id = location_ids[next_index]
    try:
        next_location = Location.objects.get(pk=next_location_id)
    except Location.DoesNotExist:
        return HttpResponse(reason=error_response + "invalid next location", status=400), False

    return next_location, True


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
    hunt = get_object_or_404(ScavengerHunt, pk=id)
    if request.method == 'GET':
        return render(request, 'scavenger_hunt/hunt.html', {'hunt': hunt})
    elif request.method == 'POST':
        try:
            latitude = float(request.POST['latitude'])
            longitude = float(request.POST['longitude'])
            radius_meters = float(request.POST.get('radius_meters', DEFAULT_SCAVENGER_HUNT_RADIUS_M))
        except ValueError:
            return HttpResponse(reason="Invalid input to POST", status=400)

        if hunt.should_advance_to_next_location(latitude, longitude, radius_meters):
            next_location_or_response, success = _get_next_location(
                hunt.hunt_template.location_ids,
                current_location=hunt.current_location
            )
            if not success:
                return next_location_or_response
            hunt.current_location = next_location_or_response
            hunt.is_finished = hunt.current_location is None
            hunt.save()
        return redirect("scavenger_hunt:hunt", id=hunt.id)

    return HttpResponseNotAllowed(["GET", "POST"])


def create_new_hunt(request, template_id):
    """Creates a new hunt and redirects the user so that he/she can find it.

    Only accepts POST requests.
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(["POST"])

    hunt_template = get_object_or_404(ScavengerHuntTemplate, pk=template_id)
    next_location_or_response, success = _get_next_location(hunt_template.location_ids)
    if not success:
        return next_location_or_response
    next_location = next_location_or_response
    is_finished = next_location is None

    hunt = ScavengerHunt(hunt_template=hunt_template, current_location=next_location, is_finished=is_finished)
    hunt.save()
    return redirect("scavenger_hunt:hunt", id=hunt.id)
