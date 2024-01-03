
class Client:

    def get_openAI(api_key):
        from openai import OpenAI
        return OpenAI(api_key=api_key)
