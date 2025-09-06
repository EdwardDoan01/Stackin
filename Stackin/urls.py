from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/user/', include('user.urls')),
    # Task APIs
    path('api/task/', include('task.urls')),

    # Payment APIs (sau này thêm)
    path('api/payment/', include('payment.urls')),

    path('api/noti/', include('noti.urls')),

    path('api/review/', include('review.urls')),

    path('api/chat/', include('chat.urls')),

    path('api/report/', include('report.urls')),
    
    # Chatbot APIs
    path('api/chatbot/', include('chatbot.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
