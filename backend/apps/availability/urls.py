from django.urls import path
from .views import SetAvailabilityView, AvailabilityListView, ScheduleTemplateView

urlpatterns = [
    path('', SetAvailabilityView.as_view(), name='set-availability'),
    path('list/', AvailabilityListView.as_view(), name='availability-list'),
    path('schedule-template/', ScheduleTemplateView.as_view(), name='schedule-template'),
]
