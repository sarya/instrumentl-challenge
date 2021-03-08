from django.contrib import admin
from django.urls import path

from filings import views


urlpatterns = [
    path('admin/', admin.site.urls),

    path('parse/', views.parse_filings),
    path('filings/', views.get_filings),
]
