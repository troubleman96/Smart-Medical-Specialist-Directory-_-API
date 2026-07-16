from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message="Success", meta=None, status_code=status.HTTP_200_OK):
    return Response(
        {"success": True, "message": message, "data": data, "errors": None, "meta": meta},
        status=status_code,
    )


def error_response(errors=None, message="Something went wrong.", status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {"success": False, "message": message, "data": None, "errors": errors, "meta": None},
        status=status_code,
    )
