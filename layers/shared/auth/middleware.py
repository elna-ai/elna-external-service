"""Auth middleware."""
from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.middlewares import NextMiddleware
from aws_lambda_powertools.event_handler.exceptions import UnauthorizedError

from data_models import AuthorizationRequest
from .backends import elna_auth_backend, JWTAuthError


def elna_login_required(
    app: APIGatewayRestResolver, next_middleware: NextMiddleware
) -> Response:
    """Login required middleware

    :param app: application instance
    :param next_middleware: next middleware
    :return: Response object after the middleware has been applied
    """

    request = AuthorizationRequest(**app.current_event.headers)
    try:
        elna_auth_backend.authenticate_with_token(request.token)
    except JWTAuthError:
        raise UnauthorizedError(f"Unauthorized")
    return next_middleware(app)
