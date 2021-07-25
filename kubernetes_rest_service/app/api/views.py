from rest_framework.viewsets import ModelViewSet

from app.api import models, serializers


class UserViewSet(ModelViewSet):
    serializer_class = serializers.User
    queryset = models.User.objects
