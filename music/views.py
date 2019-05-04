import os

from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from django.utils.safestring import mark_safe
import markdown2

from website.settings import BASE_DIR
from .models import Music


# START HELPER FUNCTIONS


def convert_name_to_directory_format(name):
    """Returns human-readable names to a format that is friendlier for Unix directories."""
    name = name.lower()
    return name.replace(" ", "_")


def get_review(music):
    """Takes in a music object, and returns an HTML review as a string, or None if the
    review can't be found."""
    path_to_review = os.path.join(BASE_DIR,
                                  'music/reviews/',
                                  convert_name_to_directory_format(music.musician.name),
                                  convert_name_to_directory_format(music.name) + '.md')
    try:
        with open(path_to_review, encoding='utf-8') as review_file:
            review_as_markdown = review_file.read()
    except IOError:
        return None

    review_as_html = markdown2.markdown(review_as_markdown)
    # We mark this as safe because we want Django to render it as HTML. This is obviously safe since I am going to be
    # one writing the markdown. :)
    return mark_safe(review_as_html)


# END HELPER FUNCTIONS


def home(request):
    """Renders the homepage for the music app."""
    recent_music = (Music.objects.order_by('-created_at')
                    .select_related('musician')
                    .prefetch_related('musician__tags'))[:10]
    context = {'albums': recent_music}

    recommended_albums = Music.objects.filter(rating__gte=2)
    if recommended_albums:
        album_of_the_month = recommended_albums.order_by('-created_at')[0]
        context['album'] = album_of_the_month
        context['review'] = get_review(album_of_the_month)

    return render(request, 'music/home.html', context)


def music(request, music_id):
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)
    context = {'album': music,
               'tags': music.musician.tags.all(),
               'review': get_review(music)}

    return render(request, 'music/music.html', context)


def search(request):
    """Searches for a particular search term in our set of musicians, music, and tags."""
    search_term = request.GET['search_term']

    music = (Music.objects.filter(
        Q(name__istartswith=search_term) |
        Q(musician__name__istartswith=search_term) |
        Q(musician__tags__name__istartswith=search_term))
        .select_related('musician')
        .prefetch_related('musician__tags'))

    context = {'albums': music}
    return render(request, 'music/search.html', context)


def ratings(request):
    """Displays the page that explains my ratings philosophy."""
    context = {}
    return render(request, 'music/ratings.html', context)
