"""AI models layer

Contains all the AI model related objects, parsing logic and implementations.
"""
from elnachain.chat_models.messages import format_message
import json
from elnachain.chat_models.tools import search_web


class BaseModel:
    """Base class for all AI models"""

    model_name: str = "base_model"

    def __init__(self, client, logger):
        self._logger = logger
        self._client = client
        self._messages = None
        self._text_response = ""
        self._error_response = ""

    def __str__(self):
        return f"{self.model_name} - Model"

    # def __call__(self, messages) -> bool:
    #     """Create the response message"""
    #     try:
    #         response = self._client.chat.completions.create(
    #             model=self.model_name, messages=format_message(messages)
    #         )
    #         self._text_response = self.parse_response(response)
    #     except Exception as e:
    #         self._error_response = e
    #         return None
    #     return self._text_response

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
                                "description": "The query to search the web for (e.g., 'latest news about Palakkad', 'current weather in New York')."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        try:
            # Format the messages
            formatted_messages = format_message(messages)

            # Get the last message directly

            if url:
                last_message = formatted_messages[-1]
                last_user_message_content = (
                    last_message["content"] if last_message["role"] == "user" else None
                )
                # Use the extracted user message content or a default text
                describe_text = last_user_message_content or "Describe the image below"

                # If a URL is provided, format a request to describe the image
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
                    model=model,
                    messages=formatted_messages
                )
                self._text_response = response.choices[0].message.content
            else:
                # Make the API call for web search
                response = self._client.chat.completions.create(
                    model=model,
                    messages=formatted_messages,
                    tools=function_descriptions,
                    tool_choice="auto"
                )

                # Check if a tool call is triggered
                formatted_messages.append(response.choices[0].message)
                if response.choices[0].message.tool_calls:
                    print("Entering tool call")
                    tool_call = response.choices[0].message.tool_calls[0]
                    arguments = json.loads(tool_call.function.arguments)

                    # Call the search_web function
                    search_result = search_web(arguments["query"])

                    # Truncate result if needed
                    if len(search_result) > 200:
                        search_result = search_result[:200]

                    # Append tool result to messages and re-generate response
                    tool_result_message = {
                        "role": "tool",
                        "content": json.dumps({
                            "query": arguments["query"],
                            "result": search_result
                        }),
                        "tool_call_id": tool_call.id
                    }
                    formatted_messages.append(tool_result_message)

                    # Re-generate the response with tool output
                    response = self._client.chat.completions.create(
                        model=model,
                        messages=formatted_messages
                    )

                # Parse the final response
                self._text_response = self.parse_response(response)

            return self._text_response

        except Exception as e:
            self._error_response = str(e)
            print(f"An error occurred: {e}")
            return None

    def parse_response(self, response):
        """Parse the response"""
        if self._logger:
            self._logger.info(msg=f"ai raw response:{str(response)})")
        result = response.choices[0].message.content.strip()
        return result

    def get_text_response(self):
        """Get the text response"""
        return self._text_response

    def get_error_response(self):
        """Get the error response"""
        return self._error_response
