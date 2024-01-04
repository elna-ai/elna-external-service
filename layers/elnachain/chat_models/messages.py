
class SystemMessage:
    def __init__(self, content):
        self.content = content

class HumanMessage:
    def __init__(self, content):
        self.content = content

class AiMessage:
    def __init__(self, content):
        self.content = content

def format_message(messages):
    converted_messages=[]

    for message in messages:
        if isinstance(message, SystemMessage):
            converted_messages.append({"role": "system", "content": message.content})
        elif isinstance(message, HumanMessage):
            converted_messages.append({"role": "user", "content": message.content})
        elif isinstance(message, AiMessage):
            converted_messages.append({"role": "assistant", "content": message.content})

    return converted_messages



