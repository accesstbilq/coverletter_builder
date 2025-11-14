# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # page
    path("generate-cover-letter", views.chatbot_view, name="coverletter_chatbot"),
    path("api/genrate-cover-letter", views.generate_cover_letter, name="chat_stream")

]
