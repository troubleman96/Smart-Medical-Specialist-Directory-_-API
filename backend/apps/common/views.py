from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .responses import success_response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return success_response(data={'status': 'healthy'}, message='Service is healthy.')
