from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.ChatbotMessageView.as_view(), name='chatbot-message'),
    path('suggestions/', views.ChatbotSuggestionsView.as_view(), name='chatbot-suggestions'),
]
