
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),
    path('expenses/', include('expenses.urls')), # Add this line for the expenses app
    path('accounts/', include('django.contrib.auth.urls')),
]
