from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse

from .models import (
    Location,
    ScavengerHunt,
    ScavengerHuntTemplate,
    UnknownLocationException,
)


def _get_next_location(
    location_ids: list[int], current_location: Location | None = None
) -> tuple[Location | HttpResponse | None, bool]:
    """
    Get the next Location that we should visit, given a sequence of location ids and the current location.

    Returns a tuple with the Location and whether we successfully fetched it.
    (Returns None if we think that we have finished the hunt.)

    If we encounter anything strange, then we return a Response with an error message.
    This should be propagated back to the user.
    """
    error_response = (
        "This hunt appears to be broken. Please contact Paul to fix. Issue: "
    )
    # Check if there are duplicate location ids.
    if len(set(location_ids)) != len(location_ids):
        return (
            HttpResponse(reason=error_response + "duplicate location ids", status=400),
            False,
        )

    # Get all the elements after the current location id.
    current_index = -1
    if current_location is not None:
        try:
            current_index = location_ids.index(current_location.id)
        except ValueError:
            return (
                HttpResponse(
                    reason=error_response + "invalid current location", status=400
                ),
                False,
            )
    next_index = current_index + 1
    # We interpret this as "you are done with the hunt."
    if next_index >= len(location_ids):
        return None, True

    # Get that Location from the DB (if it exists) and return it.
    next_location_id = location_ids[next_index]
    try:
        next_location = Location.objects.get(pk=next_location_id)
    except Location.DoesNotExist:
        return (
            HttpResponse(reason=error_response + "invalid next location", status=400),
            False,
        )

    return next_location, True


def hunt_templates(request: HttpRequest) -> HttpResponse:
    """Renders a view of all the scavenger hunt templates that can be instantiated."""
    hunt_templates = ScavengerHuntTemplate.objects.all().order_by("-updated_at")
    return render(
        request,
        "scavenger_hunt/hunt_templates.html",
        {"hunt_templates": hunt_templates},
    )


def hunt_template(request: HttpRequest, id: int) -> HttpResponse:
    """Renders a single hunt template detailed view."""
    hunt_template = get_object_or_404(ScavengerHuntTemplate, pk=id)
    return render(
        request, "scavenger_hunt/hunt_template.html", {"hunt_template": hunt_template}
    )


def hunt(request: HttpRequest, id: int) -> HttpResponse:
    """Renders a single hunt detailed view."""
    hunt = get_object_or_404(ScavengerHunt, pk=id)
    if request.method == "GET":
        success = request.GET.get("success", "True") == "True"
        first_time = request.GET.get("firstTime", "False") == "True"
        return render(
            request,
            "scavenger_hunt/hunt.html",
            {"hunt": hunt, "success": success, "first_time": first_time},
        )
    elif request.method == "POST":
        latitude = float(request.POST.get("latitude", 0.0))
        longitude = float(request.POST.get("longitude", 0.0))
        solution = request.POST.get("solution")

        if hunt.location_is_completed(latitude, longitude, solution):
            if not hunt.post_location_phase:
                hunt.post_location_phase = True
                success = True
            else:
                # Otherwise, advance to the next location.
                next_location_or_response, success = _get_next_location(
                    hunt.location_ids, current_location=hunt.current_location
                )
                if not success:
                    return next_location_or_response
                hunt.post_location_phase = False
                hunt.current_location = next_location_or_response
                hunt.is_finished = hunt.current_location is None
            hunt.save()
        else:
            success = False
        url = (
            reverse("scavenger_hunt:hunt", kwargs={"id": hunt.id})
            + f"?success={success}"
        )
        return redirect(url)

    return HttpResponseNotAllowed(["GET", "POST"])


def create_new_hunt(request: HttpRequest, template_id: int) -> HttpResponse:
    """Creates a new hunt and redirects the user so that he/she can find it.

    Only accepts POST requests.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    hunt_template = get_object_or_404(ScavengerHuntTemplate, pk=template_id)
    next_location_or_response, success = _get_next_location(hunt_template.location_ids)
    if not success:
        return next_location_or_response
    next_location = next_location_or_response
    is_finished = next_location is None

    hunt = ScavengerHunt(
        hunt_template=hunt_template,
        location_ids=hunt_template.location_ids,
        current_location=next_location,
        is_finished=is_finished,
    )
    hunt.save()
    url = reverse("scavenger_hunt:hunt", kwargs={"id": hunt.id}) + "?firstTime=True"
    return redirect(url)


def hunt_heading(request: HttpRequest, id: int) -> HttpResponse | JsonResponse:
    """
    Returns a JSON dictionary consisting of a heading for the hunt with id.
    """
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    hunt = get_object_or_404(ScavengerHunt, pk=id)

    try:
        latitude = float(request.GET["latitude"])
        longitude = float(request.GET["longitude"])
    except (KeyError, ValueError):
        return HttpResponse(reason="Invalid input to GET", status=400)

    if hunt.current_location.disable_heading:
        return HttpResponse(
            reason="Not allowed to request a heading for this location", status=403
        )

    try:
        distance, direction = hunt.distance_and_direction_to_current_location(
            latitude, longitude
        )
    except UnknownLocationException:
        return HttpResponse(
            reason="Can't compute heading to location with unspecified coords",
            status=404,
        )

    return JsonResponse(
        {
            "distance": distance,
            "direction": direction,
            "required_distance": hunt.current_location.radius,
        }
    )
