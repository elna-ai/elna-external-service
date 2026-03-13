# model_factory.py
"""Model factory for creating different AI models based on ELNA.ai supported platforms"""

import json
from typing import Dict, Any, Optional
from elnachain.chat_models.openai_model import ChatOpenAI, SERPAPI
from elnachain.chat_models.base import BaseModel


class GrokModel(BaseModel):
    """Grok (X.AI) Chat Model"""
    
    def __init__(self, api_key: str, model_name: str = "grok-3", logger=None):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.x.ai/v1/chat/completions"  # X.AI API endpoint
        super().__init__(None, logger)
    
    def __call__(self, prompt_or_messages):
        """Generate response using Grok API"""
        try:
            import requests
            
            # Handle both string prompts and message format
            if isinstance(prompt_or_messages, str):
                messages = [{"role": "user", "content": prompt_or_messages}]
            else:
                messages = self._format_messages(prompt_or_messages)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            if self._logger:
                self._logger.info(f"Sending request to Grok: {self.model_name}")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                if self._logger:
                    self._logger.info(f"Grok response received: {content[:100]}...")
                return content
            else:
                # Parse error response to extract just the message
                try:
                    error_response = response.json()
                    if "error" in error_response and "message" in error_response["error"]:
                        error_message = error_response["error"]["message"]
                        if self._logger:
                            self._logger.info(f"Grok error message: {error_message}")
                        return error_message
                except:
                    pass
                
                error_msg = f"Grok API error: {response.status_code} - {response.text}"
                if self._logger:
                    self._logger.error(error_msg)
                return f"{error_msg}"
                
        except Exception as e:
            error_msg = f"Grok model error: {str(e)}"
            if self._logger:
                self._logger.error(error_msg)
            return f"{e}"
    
    def _format_messages(self, messages):
        """Convert message format if needed"""
        if isinstance(messages, list) and all(isinstance(m, dict) for m in messages):
            return messages
        
        formatted = []
        for msg in messages:
            if hasattr(msg, 'content'):
                if msg.__class__.__name__ == 'SystemMessage':
                    formatted.append({"role": "system", "content": msg.content})
                elif msg.__class__.__name__ == 'HumanMessage':
                    formatted.append({"role": "user", "content": msg.content})
                elif msg.__class__.__name__ == 'AiMessage':
                    formatted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, dict):
                formatted.append(msg)
        
        return formatted


class DeepseekModel(BaseModel):
    """Deepseek Chat Model with Enhanced Error Logging"""
    
    def __init__(self, api_key: str, model_name: str = "deepseek-chat", logger=None):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.deepseek.com/chat/completions"
        super().__init__(None, logger)
    
    def __call__(self, prompt_or_messages):
        """Generate response using Deepseek API with detailed debugging"""
        try:
            import requests
            import json
            
            # Handle both string prompts and message format
            if isinstance(prompt_or_messages, str):
                messages = [{"role": "user", "content": prompt_or_messages}]
            else:
                messages = self._format_messages(prompt_or_messages)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            if self._logger:
                self._logger.info(f"Deepseek API Request Details:")
                self._logger.info(f"  URL: {self.base_url}")
                self._logger.info(f"  Model: {self.model_name}")
                self._logger.info(f"  API Key: {self.api_key[:15]}...{self.api_key[-4:]}")
                self._logger.info(f"  Messages Count: {len(messages)}")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if self._logger:
                self._logger.info(f"Deepseek API Response:")
                self._logger.info(f"  Status Code: {response.status_code}")
                self._logger.info(f"  Response Headers: {dict(response.headers)}")
                self._logger.info(f"  Response Body: {response.text[:1000]}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    if self._logger:
                        self._logger.info(f"Deepseek Success: {content[:100]}...")
                    return content
                except (KeyError, IndexError) as e:
                    if self._logger:
                        self._logger.error(f"Deepseek response parsing error: {str(e)}")
                        self._logger.error(f"Full response: {response.text}")
                    return "I received a response from Deepseek but couldn't parse it properly. Please try again."
                    
            else:
                error_details = f"HTTP {response.status_code}: {response.text}"
                if self._logger:
                    self._logger.error(f"Deepseek API Error: {error_details}")
                
                # Parse error response to extract just the message
                try:
                    error_response = response.json()
                    if "error" in error_response and "message" in error_response["error"]:
                        error_message = error_response["error"]["message"]
                        if self._logger:
                            self._logger.info(f"Extracted error message: {error_message}")
                        return error_message
                except:
                    pass
                
                # Try alternative endpoint if primary fails
                if hasattr(self, '_tried_alternative'):
                    return f"Deepseek API failed: {error_details[:200]}"
                else:
                    return self._try_alternative_endpoint(prompt_or_messages)
                
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Deepseek Connection Error: {str(e)}"
            if self._logger:
                self._logger.error(error_msg)
            return "Cannot connect to Deepseek API. Please check network connectivity."
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Deepseek Timeout Error: {str(e)}"
            if self._logger:
                self._logger.error(error_msg)
            return "Deepseek API request timed out. Please try again."
            
        except Exception as e:
            error_msg = f"Deepseek Unexpected Error: {str(e)}"
            if self._logger:
                self._logger.error(error_msg)
                import traceback
                self._logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"Deepseek error: {str(e)[:100]}"
    
    def _try_alternative_endpoint(self, prompt_or_messages):
        """Try alternative Deepseek API endpoint"""
        self._tried_alternative = True
        original_url = self.base_url
        
        # Try alternative endpoints
        alternative_urls = [
            "https://api.deepseek.com/v1/chat/completions",
            "https://api.deepseek.com/api/v1/chat/completions",
            "https://api.deepseek.com/v1/completions"
        ]
        
        for alt_url in alternative_urls:
            try:
                if self._logger:
                    self._logger.info(f"Trying alternative Deepseek endpoint: {alt_url}")
                
                self.base_url = alt_url
                result = self.__call__(prompt_or_messages)
                
                # Success if doesn't start with common error prefixes
                if not any(result.startswith(prefix) for prefix in ["Deepseek", "Cannot connect", "Insufficient", "Invalid"]):
                    if self._logger:
                        self._logger.info(f"Alternative endpoint worked: {alt_url}")
                    return result
                    
            except Exception as e:
                if self._logger:
                    self._logger.warning(f"Alternative endpoint {alt_url} failed: {str(e)}")
                continue
        
        # Restore original URL
        self.base_url = original_url
        return "All Deepseek API endpoints failed. Please verify your API key and try again."
    
    def _format_messages(self, messages):
        """Convert message format if needed"""
        if isinstance(messages, list) and all(isinstance(m, dict) for m in messages):
            return messages
        
        formatted = []
        for msg in messages:
            if hasattr(msg, 'content'):
                if msg.__class__.__name__ == 'SystemMessage':
                    formatted.append({"role": "system", "content": msg.content})
                elif msg.__class__.__name__ == 'HumanMessage':
                    formatted.append({"role": "user", "content": msg.content})
                elif msg.__class__.__name__ == 'AiMessage':
                    formatted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, dict):
                formatted.append(msg)
        
        return formatted


class ModelFactory:
    """Factory class for creating AI models based on ELNA.ai supported platforms"""
    
    # Exact platforms and models from ELNA.ai interface
    SUPPORTED_PLATFORMS = {
        "grok": GrokModel,
        "openai": ChatOpenAI,
        "deepseek": DeepseekModel,
    }
    
    # Valid model names for each platform (from the UI screenshots)
    VALID_MODELS = {
        "grok": [
            "grok-3",
            "grok-3-latest", 
            "grok-3-mini",
            "grok-3-mini-latest",
            "grok-3-mini-fast",
            "grok-3-mini-fast-latest",
            "grok-2",
            "grok-2-latest"
        ],
        "openai": [
            "gpt-4-1",
            "gpt-4-1-mini", 
            "gpt-4-1-preview",
            "gpt-4o-2024-05-13",
            "gpt-4o-mini",
            "o1",
            "o1-pro",
            "o3",
            "gpt-4o",
            "o3-mini",
            "o1-mini",
            "gpt-3.5-turbo",
            "gpt-4"
        ],
        "deepseek": [
            "deepseek-chat",
            "deepseek-reasoner"
        ]
    }
    
    @classmethod
    def create_model(cls, model_details: Dict[str, Any], logger=None) -> BaseModel:
        """Create a model instance based on model_details
        
        Args:
            model_details: Dictionary containing platform, modelName, and apiKey
            logger: Logger instance
            
        Returns:
            Model instance
            
        Raises:
            ValueError: If platform is not supported or required fields are missing
        """
        try:
            platform = model_details.get("platform", "").lower()
            model_name = model_details.get("modelName", "")
            api_key = model_details.get("apiKey", "")
            
            # Validate required fields
            if not platform:
                raise ValueError("Platform is required in model_details")
            if not api_key:
                raise ValueError("API key is required in model_details")
            
            # Validate platform support
            if platform not in cls.SUPPORTED_PLATFORMS:
                raise ValueError(f"Unsupported platform: {platform}. Supported platforms: {list(cls.SUPPORTED_PLATFORMS.keys())}")
            
            # Validate model name for platform
            if model_name and platform in cls.VALID_MODELS:
                if model_name not in cls.VALID_MODELS[platform]:
                    if logger:
                        logger.warning(f"Model {model_name} not in validated list for {platform}, but proceeding anyway")
            
            # Get model class
            model_class = cls.SUPPORTED_PLATFORMS[platform]
            
            # Create model instance with appropriate parameters
            if platform == "openai":
                return model_class(api_key=api_key, logger=logger)
            elif platform in ["grok", "deepseek"]:
                return model_class(api_key=api_key, model_name=model_name, logger=logger)
            else:
                # Generic approach for any future platforms
                return model_class(api_key=api_key, logger=logger)
                
        except Exception as e:
            if logger:
                logger.error(f"Error creating model: {str(e)}")
            raise
    
    @classmethod
    def get_supported_platforms(cls) -> Dict[str, list]:
        """Get dictionary of supported platforms and their valid models"""
        return cls.VALID_MODELS.copy()
    
    @classmethod
    def validate_model_details(cls, model_details: Dict[str, Any]) -> Dict[str, Any]:
        """Validate model details and return validation result
        
        Args:
            model_details: Dictionary containing platform, modelName, and apiKey
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        platform = model_details.get("platform", "").lower()
        model_name = model_details.get("modelName", "")
        api_key = model_details.get("apiKey", "")
        
        if not platform:
            result["errors"].append("Platform is required")
        elif platform not in cls.SUPPORTED_PLATFORMS:
            result["errors"].append(f"Unsupported platform: {platform}")
        
        if not api_key:
            result["errors"].append("API key is required")
        
        if not model_name:
            result["warnings"].append("Model name not specified, will use default")
        elif platform in cls.VALID_MODELS and model_name not in cls.VALID_MODELS[platform]:
            result["warnings"].append(f"Model {model_name} not in validated list for {platform}")
        
        result["valid"] = len(result["errors"]) == 0
        return result


class ModelWithTools(BaseModel):
    """Wrapper for models that support tools (like web search)"""
    
    def __init__(self, base_model: BaseModel, enable_web_search: bool = False, logger=None):
        self.base_model = base_model
        self.enable_web_search = enable_web_search
        super().__init__(None, logger)
    
    def __call__(self, prompt_or_messages):
        """Generate response with optional tool support"""
        if self.enable_web_search and isinstance(self.base_model, ChatOpenAI):
            # Use SERPAPI for OpenAI models when web search is enabled
            serpapi_model = SERPAPI(api_key=self.base_model._client.api_key, logger=self._logger)
            return serpapi_model(prompt_or_messages)
        else:
            # Use base model (tools not implemented for Grok/Deepseek yet)
            return self.base_model(prompt_or_messages)


# Helper functions
def create_model_from_request(model_details: Dict[str, Any], enable_tools: bool = False, logger=None):
    """Helper function to create model from request details"""
    try:
        # Validate first
        validation = ModelFactory.validate_model_details(model_details)
        
        if not validation["valid"]:
            raise ValueError(f"Invalid model details: {', '.join(validation['errors'])}")
        
        # Log warnings
        if validation["warnings"] and logger:
            for warning in validation["warnings"]:
                logger.warning(warning)
        
        base_model = ModelFactory.create_model(model_details, logger)
        
        if enable_tools:
            return ModelWithTools(base_model, enable_web_search=True, logger=logger)
        else:
            return base_model
            
    except Exception as e:
        if logger:
            logger.error(f"Failed to create model from request: {str(e)}")
        
        # Fallback to OpenAI if available
        try:
            import os
            fallback_api_key = os.environ.get("OPEN_AI_KEY")
            if fallback_api_key:
                if logger:
                    logger.warning("Using fallback OpenAI model")
                return ChatOpenAI(api_key=fallback_api_key, logger=logger)
        except:
            pass
        
        raise Exception("Failed to create any model instance")


def get_platform_info():
    """Get detailed information about all supported platforms and models"""
    return {
        "platforms": ModelFactory.get_supported_platforms(),
        "examples": {
            "grok": {
                "platform": "grok",
                "modelName": "grok-3",
                "apiKey": "your-grok-api-key"
            },
            "openai": {
                "platform": "openai", 
                "modelName": "gpt-4o",
                "apiKey": "your-openai-api-key"
            },
            "deepseek": {
                "platform": "deepseek",
                "modelName": "deepseek-chat", 
                "apiKey": "your-deepseek-api-key"
            }
        }
    }