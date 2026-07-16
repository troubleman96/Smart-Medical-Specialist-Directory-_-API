from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from apps.common.responses import success_response
from apps.common.permissions import IsSuperAdmin
from .services import ReportService


class OverviewReportView(generics.GenericAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        data = ReportService.overview()
        return success_response(data=data)


class SearchReportView(generics.GenericAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        data = ReportService.search_reports()
        return success_response(data=data)
