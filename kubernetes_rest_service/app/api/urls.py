from rest_framework.routers import DefaultRouter

from app.api import views


router = DefaultRouter(trailing_slash=False)
router.register("users", views.UserViewSet, basename="user")

urlpatterns = router.urls
