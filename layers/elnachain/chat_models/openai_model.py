"""chat models
"""

from elnachain.chat_models.base import BaseModel
from openai import OpenAI
from elnachain.chat_models.messages import format_message
from elnachain.chat_models.tools import search_web
import json


class ChatOpenAI(BaseModel):
    """ChatOpenAI

    Args:
        BaseModel (Base Chat model)
    """

    model_name = "gpt-4o"

    def __init__(self, api_key, logger=None) -> None:
        client = OpenAI(api_key=api_key)
        super().__init__(client, logger)


class SERPAPI(BaseModel):
    """ChatOpenAI

    Args:
        BaseModel (Base Chat model)
    """

    model_name = "gpt-4o"

    def __init__(self, api_key, logger=None) -> None:
        client = OpenAI(api_key=api_key)
        super().__init__(client, logger)

    def __call__(self, messages, url=None):
        """Create the response message with tool integration for web search or image description."""
        model = self.model_name
        function_descriptions = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web using SERPAPI and return the answer box.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search the web for (e.g., 'latest news about Palakkad', 'current weather in New York').",
                            }
                        },
                        "required": ["query"],
                    },
                },
            }
        ]

        try:
            formatted_messages = format_message(messages)

            if url:
                last_message = formatted_messages[-1]
                last_user_message_content = (
                    last_message["content"] if last_message["role"] == "user" else None
                )
                describe_text = last_user_message_content or "Describe the image below"

                print("Handling image description task.")
                formatted_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": describe_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": url},
                            },
                        ],
                    }
                ]
                response = self._client.chat.completions.create(
                    model=model, messages=formatted_messages
                )
                self._text_response = response.choices[0].message.content
            else:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=formatted_messages,
                    tools=function_descriptions,
                    tool_choice="auto",
                )

                # Check if a tool call is triggered
                formatted_messages.append(response.choices[0].message)
                self._logger.info(
                    msg=f"***** Formatted Message:{str(formatted_messages)})"
                )
                if response.choices[0].message.tool_calls:
                    print("Entering tool call")
                    tool_call = response.choices[0].message.tool_calls[0]
                    arguments = json.loads(tool_call.function.arguments)

                    search_result = search_web(arguments["query"])

                    if len(search_result) > 200:
                        search_result = search_result[:200]

                    tool_result_message = {
                        "role": "tool",
                        "content": json.dumps(
                            {"query": arguments["query"], "result": search_result}
                        ),
                        "tool_call_id": tool_call.id,
                    }
                    formatted_messages.append(tool_result_message)

                    response = self._client.chat.completions.create(
                        model=model, messages=formatted_messages
                    )

                self._text_response = self.parse_response(response)

            return self._text_response

        except Exception as e:
            self._error_response = str(e)
            print(f"An error occurred: {e}")
            return None
