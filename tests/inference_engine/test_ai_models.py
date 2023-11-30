from src.lambdas.inference_engine.packages.ai_models import choose_service_model
from src.lambdas.inference_engine.packages.ai_services import MOCK_AI_RESPONSE


def test_mock_model():
    """Test the mock model

    :return:
    """
    mock_event = None
    mock_context = None
    selected_model_cls = choose_service_model(mock_event, mock_context)
    ai_model = selected_model_cls(mock_event, "asd_test")
    assert ai_model.create_response() is True
    assert ai_model.get_text_response() == MOCK_AI_RESPONSE
