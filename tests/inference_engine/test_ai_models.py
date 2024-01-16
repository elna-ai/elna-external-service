from src.lambdas.inference_engine.packages.ai_models import choose_service_model


def test_mock_model():
    """Test the mock model

    :return:
    """

    mock_biography = "bio_value"
    mock_input_prompt = "prompt_value"

    mock_event = {"biography": mock_biography
        ,
                  "input_prompt":
        mock_input_prompt}
    selected_model_cls = choose_service_model(
        mock_event, None)
    ai_model = selected_model_cls(mock_event,
                                  "asd_test")
    assert ai_model.create_response() is True
    assert ai_model.get_text_response()[0] == mock_biography
    assert ai_model.get_text_response()[1] == mock_input_prompt
