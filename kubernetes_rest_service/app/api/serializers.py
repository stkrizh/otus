from secrets import token_urlsafe

from django.contrib.auth.hashers import make_password
from rest_framework.serializers import ModelSerializer

from app.api import models


class User(ModelSerializer):
    class Meta:
        model = models.User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["password"] = make_password(token_urlsafe())
        return super().create(validated_data)
