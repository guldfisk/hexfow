from django.shortcuts import render
from rest_framework.decorators import api_view
from django.http import HttpResponse, HttpRequest, JsonResponse


@api_view(["GET"])
def status(request: HttpRequest) -> HttpResponse:
    return JsonResponse({"status": "ok"})


def index(request):
    return render(request, "frontend/index.html")
