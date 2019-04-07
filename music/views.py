from django.shortcuts import get_object_or_404, render

from .models import Music


def home(request):
    recent_music = Music.objects.order_by('-created_at')[:10]

    context = {'recent_music': recent_music}
    return render(request, 'music/home.html', context)


def music(request, music_id):
    """Displays a detailed view of a piece of music."""
    music = get_object_or_404(Music, pk=music_id)
    tags = music.musician.tags.all()

    context = {'music': music, 'tags': tags}
    return render(request, 'music/music.html', context)
