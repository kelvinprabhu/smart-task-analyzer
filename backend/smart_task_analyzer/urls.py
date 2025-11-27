"""
URL configuration for smart_task_analyzer project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.views.static import serve
from pathlib import Path

FRONTEND_DIR = Path(settings.BASE_DIR).parent / 'frontend'

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('admin/', admin.site.urls),
    path('api/tasks/', include('taskapi.urls')),
]

if settings.DEBUG:
    # Serve frontend static files (css/js/assets) during development
    urlpatterns += [
        path('css/<path:path>', serve, {'document_root': FRONTEND_DIR / 'css'}),
        path('js/<path:path>', serve, {'document_root': FRONTEND_DIR / 'js'}),
        path('assets/<path:path>', serve, {'document_root': FRONTEND_DIR / 'assets'}),
    ]
