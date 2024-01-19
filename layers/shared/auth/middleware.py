from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response
from aws_lambda_powertools.event_handler.middlewares import NextMiddleware
from aws_lambda_powertools.event_handler.exceptions import UnauthorizedError

from data_models import AuthorizationRequest
from .backends import elna_auth_backend


def elna_login_required(
    app: APIGatewayRestResolver, next_middleware: NextMiddleware
) -> Response:
    request_headers = app.current_event.headers
    request = AuthorizationRequest(**request_headers)
    try:
        elna_auth_backend.authenticate_with_token(request.token)
    except Exception as e:
        raise UnauthorizedError(f"Unauthorized: {e}")

    return next_middleware(app)
