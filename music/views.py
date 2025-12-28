from collections import Counter, defaultdict
from typing import Any

from django.contrib.auth.decorators import login_required
from django.db.models import Q, QuerySet
from django.db.utils import IntegrityError
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render, redirect, reverse
from feedgen.feed import FeedGenerator
from .models import Music, BestOf, Comment, Tag
from .constants import URL_ROOT, MY_NAME, MY_EMAIL


def update_context_with_album(
    context: dict[str, Any], album: Music, show_comments: bool = True
) -> None:
    """Updates the template context with album, tags, and optionally comments."""
    context["album"] = album
    context["tags"] = album.musician.tags.all()
    context["show_comments"] = show_comments
    if show_comments:
        context["comments"] = album.comment_set.all().order_by("created_at")


def apply_common_preselects_music(music_queryset: QuerySet[Music]) -> QuerySet[Music]:
    """Applies select_related and prefetch_related optimizations to avoid N+1 queries."""
    return (
        music_queryset.select_related("musician")
        .prefetch_related("musician__tags", "comment_set")
        .distinct()
    )


def get_recent_music(quantity: int = 10) -> QuerySet[Music]:
    """Returns the most recently reviewed albums with optimized preselects."""
    return apply_common_preselects_music(Music.objects.order_by("-reviewed_at"))[
        :quantity
    ]


def home(request: HttpRequest) -> HttpResponse:
    """Renders the homepage for the music app."""
    recent_music = get_recent_music()
    context = {"albums": recent_music, "truncate": True}

    recommended_albums = apply_common_preselects_music(
        Music.objects.filter(album_of_the_month=True)
    )
    if recommended_albums:
        album_of_the_month = recommended_albums.order_by("-reviewed_at")[0]
        update_context_with_album(context, album_of_the_month, show_comments=False)

    return render(request, "music/home.html", context)


def music(request: HttpRequest, music_id: int) -> HttpResponse:
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)

    context: dict[str, Any] = {}
    update_context_with_album(context, music)

    return render(request, "music/music.html", context)


@login_required
def comment(request: HttpRequest, music_id: int) -> HttpResponse:
    """Adds a comment to a piece of music."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        comment_text = request.POST["comment"]
        Comment.objects.create(
            text=comment_text, author=request.user, album_id=music_id
        )
    except (KeyError, IntegrityError):
        return HttpResponse(reason="Invalid input to POST", status=400)

    url = reverse("music:music_detailed", kwargs={"music_id": music_id})

    return redirect(url)


def search(request: HttpRequest) -> HttpResponse:
    """Searches for a particular search term in our set of musicians, music, and tags."""
    search_term = request.GET["search_term"]

    music = apply_common_preselects_music(
        Music.objects.filter(
            Q(name__istartswith=search_term)
            | Q(musician__name__istartswith=search_term)
            | Q(musician__tags__name__iexact=search_term)
        )
    )

    context = {"albums": music, "search_term": search_term}
    return render(request, "music/search.html", context)


def ratings(request: HttpRequest) -> HttpResponse:
    """Displays the page that explains my ratings philosophy."""
    context: dict[str, Any] = {}
    return render(request, "music/ratings.html", context)


def rss(_: HttpRequest) -> HttpResponse:
    """Returns the XML content of my RSS feed for the music part of the website.

    NOTE: We are doing no caching here at all right now, because this function is very fast and the website has
    no traffic. If this situation changes, then I should cache it so that I don't build this object from scratch every
    time."""
    generator = FeedGenerator()

    # Add basic metadata.
    generator.title("Paul's Music Feed")
    generator.author(name=MY_NAME, email=MY_EMAIL)
    generator.contributor(name=MY_NAME, email=MY_EMAIL)
    # RSS requires that we point to our own feed here. Not sure why.
    generator.link(href=(URL_ROOT + "rss"), rel="self")
    favicon_path = URL_ROOT + "static/favicon.png"
    generator.icon(favicon_path)
    generator.logo(favicon_path)
    generator.subtitle("A feed for anyone who wants to know what albums I'm liking.")
    generator.language("en")

    albums = get_recent_music(quantity=30)
    for album in albums:
        entry = generator.add_entry()
        entry.title(album.name)
        path_to_album = URL_ROOT + "music/music/{}".format(album.id)
        entry.guid(path_to_album, permalink=True)
        entry.description(album.description())
        entry.updated(album.reviewed_at)
        entry.published(album.reviewed_at)
        entry.author(name=MY_NAME, email=MY_EMAIL)
        entry.link(href=path_to_album, rel="alternate")
        entry.category(term="score__{}".format(album.rating))

    return HttpResponse(generator.rss_str())


def best_of(request: HttpRequest, name: str) -> HttpResponse:
    """Searches for a particular search term in our set of musicians, music, and tags."""
    best_of = get_object_or_404(BestOf, name=name)
    relevant_albums = apply_common_preselects_music(
        Music.objects.filter(
            reviewed_at__gt=best_of.start_date,
            reviewed_at__lt=best_of.end_date,
            exclude_from_best_of_list=False,
        )
    )
    albums_by_score: defaultdict[int, list[Music]] = defaultdict(list)
    # Partition by rating.
    for album in relevant_albums:
        albums_by_score[album.rating].append(album)
    # Sort according to review date.
    for value in albums_by_score.values():
        value.sort(key=lambda x: x.reviewed_at)
    albums_with_photos = albums_by_score[3] + albums_by_score[2] + albums_by_score[1]
    albums_with_photos = [album for album in albums_with_photos if album.image_src()]

    tag_counter: Counter[Tag] = Counter()
    for album in relevant_albums:
        for tag in album.musician.tags.all():
            tag_counter[tag] += 1

    tags_by_popularity = list(tag_counter.keys())
    tags_by_popularity.sort(key=lambda x: tag_counter[x], reverse=True)
    corresponding_values = [tag_counter[tag] for tag in tags_by_popularity]

    context = {
        "best_of": best_of,
        "best_albums": albums_by_score[3],
        "great_albums": albums_by_score[2],
        "good_albums": albums_by_score[1],
        "tags_with_quantity": zip(tags_by_popularity, corresponding_values),
        "albums_with_photos": albums_with_photos[:10],
    }
    return render(request, "music/best_of.html", context)
