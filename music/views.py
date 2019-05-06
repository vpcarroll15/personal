from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from .models import Music


def update_context_with_album(context, album):
    context['album'] = album
    context['tags'] = album.musician.tags.all()


def home(request):
    """Renders the homepage for the music app."""
    recent_music = (Music.objects.order_by('-reviewed_at')
                    .select_related('musician')
                    .prefetch_related('musician__tags'))[:10]
    context = {'albums': recent_music}

    recommended_albums = Music.objects.filter(album_of_the_month=True)
    if recommended_albums:
        album_of_the_month = recommended_albums.order_by('-reviewed_at')[0]
        update_context_with_album(context, album_of_the_month)

    return render(request, 'music/home.html', context)


def music(request, music_id):
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)

    context = {}
    update_context_with_album(context, music)

    return render(request, 'music/music.html', context)


def search(request):
    """Searches for a particular search term in our set of musicians, music, and tags."""
    search_term = request.GET['search_term']

    music = Music.objects.filter(
        Q(name__istartswith=search_term) |
        Q(musician__name__istartswith=search_term) |
        Q(musician__tags__name__iexact=search_term)
    ).select_related('musician').prefetch_related('musician__tags')

    context = {'albums': music, 'search_term': search_term}
    return render(request, 'music/search.html', context)


def ratings(request):
    """Displays the page that explains my ratings philosophy."""
    context = {}
    return render(request, 'music/ratings.html', context)
