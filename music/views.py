from collections import defaultdict, Counter

from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.http import HttpResponse
from feedgen.feed import FeedGenerator

from .models import Music, BestOf
from .constants import URL_ROOT, MY_NAME, MY_EMAIL


def update_context_with_album(context, album):
    context["album"] = album
    context["tags"] = album.musician.tags.all()


def apply_common_preselects_music(music_queryset):
    return (
        music_queryset.select_related("musician")
        .prefetch_related("musician__tags")
        .distinct()
    )


def get_recent_music(quantity=10):
    return apply_common_preselects_music(Music.objects.order_by("-reviewed_at"))[
        :quantity
    ]


def home(request):
    """Renders the homepage for the music app."""
    recent_music = get_recent_music()
    context = {"albums": recent_music, "truncate": True}

    recommended_albums = apply_common_preselects_music(
        Music.objects.filter(album_of_the_month=True)
    )
    if recommended_albums:
        album_of_the_month = recommended_albums.order_by("-reviewed_at")[0]
        update_context_with_album(context, album_of_the_month)

    return render(request, "music/home.html", context)


def music(request, music_id):
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)

    context = {}
    update_context_with_album(context, music)

    return render(request, "music/music.html", context)


def search(request):
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


def ratings(request):
    """Displays the page that explains my ratings philosophy."""
    context = {}
    return render(request, "music/ratings.html", context)


def rss(_):
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


def best_of(request, name):
    """Searches for a particular search term in our set of musicians, music, and tags."""
    best_of = get_object_or_404(BestOf, name=name)
    relevant_albums = apply_common_preselects_music(
        Music.objects.filter(
            reviewed_at__gt=best_of.start_date,
            reviewed_at__lt=best_of.end_date,
            exclude_from_best_of_list=False,
        )
    )
    albums_by_score = defaultdict(list)
    # Partition by rating.
    for album in relevant_albums:
        albums_by_score[album.rating].append(album)
    # Sort according to review date.
    for value in albums_by_score.values():
        value.sort(key=lambda x: x.reviewed_at)
    albums_with_photos = albums_by_score[3] + albums_by_score[2] + albums_by_score[1]
    albums_with_photos = [album for album in albums_with_photos if album.image_src()]

    tag_counter = Counter()
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
