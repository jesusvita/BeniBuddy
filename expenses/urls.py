from django.urls import path
from . import views

app_name = 'expenses'  # This is important for namespacing

urlpatterns = [
    path('', views.expense_tracker_view, name='expense_tracker_current_month'),
    path('<int:year>/<int:month>/', views.expense_tracker_view, name='expense_tracker'),
    path('delete/<int:expense_id>/', views.delete_expense_view, name='delete_expense'),
    path('edit/<int:expense_id>/', views.edit_expense_view, name='edit_expense'),
]