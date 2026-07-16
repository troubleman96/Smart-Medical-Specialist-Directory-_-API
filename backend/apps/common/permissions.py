from rest_framework.permissions import BasePermission


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'PATIENT'
        )


class IsHospitalAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'HOSPITAL_ADMIN'
        )


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'SUPER_ADMIN'
        )


class IsOwnHospital(BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'hospital_id'):
            return request.user.hospital_id == obj.hospital_id
        return False
