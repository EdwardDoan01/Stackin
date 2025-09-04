from django.urls import path, include
from .views import RegisterView, LoginAPIView, ProfileView, UserUpdateView, IdentityVerificationView, TaskerRegistrationView, ChangePasswordView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'), 
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/update/', UserUpdateView.as_view(), name='update-profile'),
    path('identity/', IdentityVerificationView.as_view(), name='identity-verification'),
    path('tasker-register/', TaskerRegistrationView.as_view(), name='tasker-registration'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'), 

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), 
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), 
]
