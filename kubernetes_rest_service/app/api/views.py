import random

from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from app.api import models, serializers


class UserViewSet(ModelViewSet):
    serializer_class = serializers.User
    queryset = models.User.objects

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, kwargs)

        # Emulate an internal server error
        if random.random() < 0.05:
            return Response({}, status=500)

        return response

    def destroy(self, request, *args, **kwargs):
        response = super().list(request, *args, kwargs)

        # Emulate an internal server error
        if random.random() < 0.01:
            return Response({}, status=500)

        return response
