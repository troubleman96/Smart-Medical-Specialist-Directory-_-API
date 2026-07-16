from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from apps.common.responses import success_response
from apps.common.permissions import IsSuperAdmin
from .services import ReportService


@extend_schema(tags=['Reports'], summary='System overview report (Super Admin)')
class OverviewReportView(generics.GenericAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        data = ReportService.overview()
        return success_response(data=data)


@extend_schema(tags=['Reports'], summary='Search analytics report (Super Admin)')
class SearchReportView(generics.GenericAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        data = ReportService.search_reports()
        return success_response(data=data)
