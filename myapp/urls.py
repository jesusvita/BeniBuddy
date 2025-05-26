from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('your-tips/', views.user_tips, name='user_tips'),
    path('add-tip/', views.add_tip, name='add_tip'),
    path('edit-tip/<int:tip_id>/', views.edit_tip, name='edit_tip'),
    path('delete-tip/<int:tip_id>/', views.delete_tip, name='delete_tip'),
    path('tips/<int:year>/<int:month>/', views.user_tips, name='user_tips'),
    path('set-cycle/', views.set_pay_cycle, name='set_pay_cycle'),
    path('delete-tip/<int:tip_id>/', views.delete_tip, name='delete_tip'),
    path('benihana-qr/', views.benihana_qr_view, name='benihana_qr'),
    path('chat/create/', views.create_chat_room, name='create_chat_room'),
    path('chat/<uuid:room_id>/', views.chat_room_view, name='chat_room'),
]
