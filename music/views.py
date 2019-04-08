from django.shortcuts import get_object_or_404, render

from .models import Music


def home(request):
    """Renders the homepage for the music app."""
    recent_music = Music.objects.order_by('-created_at')[:10]
    context = {'recent_music': recent_music}

    recommended_albums = Music.objects.filter(rating__gte=2)
    if recommended_albums:
        album_of_the_month = recommended_albums.order_by('-created_at')[0]
        context['album_of_the_month'] = album_of_the_month

    return render(request, 'music/home.html', context)


def music(request, music_id):
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)
    tags = music.musician.tags.all()

    context = {'music': music, 'tags': tags}
    return render(request, 'music/music.html', context)
