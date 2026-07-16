from django.urls import path
from .views import OverviewReportView, SearchReportView

urlpatterns = [
    path('overview/', OverviewReportView.as_view(), name='overview-report'),
    path('searches/', SearchReportView.as_view(), name='search-report'),
]
