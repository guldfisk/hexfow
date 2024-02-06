import dataclasses

from django.conf import settings
from django.http import HttpRequest
from django.shortcuts import render
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from game.game.map.hexmap import generate_super_map


# from game.map.hexmap import generate_super_map


# def index(request: HttpRequest) -> :


class GenerateMap(generics.GenericAPIView):
    def get(self, request: Request, *args, **kwargs) -> Response:
        return Response(generate_super_map().serialize())
