class SystemMessage:
    """SystemMessage"""

    def __init__(self, content):
        self.content = content


class HumanMessage:
    """HumanMessage"""

    def __init__(self, content):
        self.content = content


class AiMessage:
    """AiMessage"""

    def __init__(self, content):
        self.content = content


def format_message(messages):
    """format message to openai api call

    Args:
        messages (list): list of messages

    Returns:
        list: list of format message
    """
    converted_messages = []

    for message in messages:
        if isinstance(message, SystemMessage):
            converted_messages.append({"role": "system", "content": message.content})
        elif isinstance(message, HumanMessage):
            converted_messages.append({"role": "user", "content": message.content})
        elif isinstance(message, AiMessage):
            converted_messages.append({"role": "assistant", "content": message.content})

    return converted_messages
