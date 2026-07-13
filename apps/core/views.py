from django.http import Http404


def private_media_not_found(request, path=""):
    """Never expose CV storage through Django's development media handler."""
    raise Http404
