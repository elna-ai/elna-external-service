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

    def __call__(self, messages) -> bool:
        """Create the response message"""
        try:
            response = self._client.chat.completions.create(
                model=self.model_name, messages=format_message(messages)
            )
            self._text_response = self.parse_response(response)
        except Exception as e:
            self._error_response = e
            return None
        return self._text_response

    def __callf__(self, messages) -> bool:
        """Create the response message with tool integration for web search"""
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
            # Step 1: Format the input messages and make the initial request
            formatted_messages = format_message(messages)
            response = self._client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                tools=function_descriptions,
                tool_choice="auto"
            )

            # Step 2: Check if a tool call is triggered
            formatted_messages.append(response.choices[0].message)
            if response.choices[0].message.tool_calls:
                print("Entering tool call")
                tool_call = response.choices[0].message.tool_calls[0]
                arguments = json.loads(tool_call.function.arguments)

                # Step 3: Call the search_web function
                search_result = self.search_web(arguments["query"])

                # Truncate result if needed
                if len(search_result) > 200:
                    search_result = search_result[:200]

                # Step 4: Append tool result to messages and re-generate response
                tool_result_message = {
                    "role": "tool",
                    "content": json.dumps({
                        "query": arguments["query"],
                        "result": search_result
                    }),
                    "tool_call_id": tool_call.id
                }
                formatted_messages.append(tool_result_message)

                # Step 5: Re-generate the response with tool output
                response = self._client.chat.completions.create(
                    model=model,
                    messages=formatted_messages
                )

            # Parse the final response
            self._text_response = self.parse_response(response)

        except Exception as e:
            self._error_response = e
            return None
        return self._text_response

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
