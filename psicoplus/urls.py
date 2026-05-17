from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/login/')),
    path('', include('agenda.urls')),
    path('', include('atendimentos.urls')),
    path('', include('accounts.urls')),
]
