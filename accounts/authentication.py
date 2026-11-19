from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class FastTokenAuthentication(TokenAuthentication):
    """Authenticate without reading the member's stored profile photo."""

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = (
                model.objects.select_related('user')
                .defer('user__profile_picture')
                .get(key=key)
            )
        except model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')

        return (token.user, token)
