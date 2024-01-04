from openai import OpenAI

class Client:

    def get_openAI(api_key):
        return OpenAI(api_key=api_key)
