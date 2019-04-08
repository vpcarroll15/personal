from django.shortcuts import get_object_or_404, render
from django.db.models import Q

from .models import Music


def home(request):
    """Renders the homepage for the music app."""
    recent_music = Music.objects.order_by('-created_at')[:10]
    context = {'albums': recent_music}

    recommended_albums = Music.objects.filter(rating__gte=2)
    if recommended_albums:
        album_of_the_month = recommended_albums.order_by('-created_at')[0]
        context['album'] = album_of_the_month

    return render(request, 'music/home.html', context)


def music(request, music_id):
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)
    tags = music.musician.tags.all()

    context = {'album': music, 'tags': tags}
    return render(request, 'music/music.html', context)


def search(request):
    """Searches for a particular search term in our set of musicians, music, and tags."""
    search_term = request.GET['search_term']

    # TODO: Make this case-insensitive.
    music = Music.objects.filter(
        Q(name__startswith=search_term) |
        Q(musician__name__startswith=search_term) |
        Q(musician__tags__name__startswith=search_term)
    )

    context = {'albums': music }
    return render(request, 'music/search.html', context)
