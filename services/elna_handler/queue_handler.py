# queue_handler.py - COMPLETELY FIXED to return only plain response text
"""Updated queue handler for the Canister HTTP outcall with dynamic model selection - FIXED"""

import json
import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext
from elnachain import PromptTemplate
from shared import RequestDataHandler
from model_factory import ModelFactory, create_model_from_request

tracer = Tracer()
logger = Logger()

dynamodb_client = boto3.resource("dynamodb")

request_data_handler = RequestDataHandler(
    os.environ["AI_RESPONSE_TABLE"], dynamodb_client, logger
)


def handle_chat_prompt(uuid: str, payload: str):
    """Generate response using dynamic model selection based on request payload - FIXED

    Args:
        uuid (str): uuid
        payload (str): body of the message containing model_details
    """
    try:
        # Parse the payload
        body = json.loads(payload)
        logger.info(f"Processing request with payload: {body}")
        
        # Extract model details
        model_details = body.get("model_details")
        
        if not model_details:
            logger.error("No model_details found in payload")
            error_response = "Error: No model configuration provided"
            request_data_handler.store_prompt_response(uuid, error_response)
            return
        
        # Validate model_details structure
        required_fields = ["platform", "apiKey"]
        for field in required_fields:
            if not model_details.get(field):
                logger.error(f"Missing required field in model_details: {field}")
                error_response = f"Error: Missing required field '{field}' in model configuration"
                request_data_handler.store_prompt_response(uuid, error_response)
                return
        
        # Check if web search/tools should be enabled
        enable_tools = body.get("enable_web_search", False) or body.get("enable_tools", False)
        
        # Create the appropriate model
        try:
            llm = create_model_from_request(model_details, enable_tools=enable_tools, logger=logger)
            logger.info(f"Successfully created {model_details['platform']} model")
        except Exception as e:
            logger.error(f"Failed to create model: {str(e)}")
            error_response = f"Error: Failed to initialize {model_details.get('platform', 'unknown')} model - {str(e)}"
            request_data_handler.store_prompt_response(uuid, error_response)
            return
        
        # Create prompt template
        template = PromptTemplate(
            body=body,
            logger=logger,
        )
        
        # Format the message for the model
        try:
            chat_prompt = template.format_message()
            logger.info(f"Generated prompt for {model_details['platform']} model")
        except Exception as e:
            logger.error(f"Failed to format prompt: {str(e)}")
            error_response = f"Error: Failed to format prompt - {str(e)}"
            request_data_handler.store_prompt_response(uuid, error_response)
            return
        
        # Generate response using the selected model
        try:
            response = llm(chat_prompt)
            
            # Validate response
            if not response or response.strip() == "":
                logger.error("Model returned empty response")
                response = "I apologize, but I couldn't generate a response. Please try again."
            
            logger.info(f"AI response generated successfully using {model_details['platform']}: {str(response)[:100]}...")
            
            # CRITICAL FIX: Check if response is a JSON string and extract just the response
            try:
                # If the model returned JSON with metadata, extract just the response
                if response.strip().startswith('{') and '"response"' in response:
                    parsed_response = json.loads(response)
                    if isinstance(parsed_response, dict) and 'response' in parsed_response:
                        response = parsed_response['response']
                        logger.info("Extracted response from JSON metadata wrapper")
            except (json.JSONDecodeError, KeyError):
                # If it's not JSON or doesn't have the expected structure, use as-is
                pass
            
            # FIXED: Store only the response text (no metadata wrapper)
            request_data_handler.store_prompt_response(uuid, response)
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            response = f"Error: Failed to generate response using {model_details.get('platform', 'unknown')} model - {str(e)}"
            request_data_handler.store_prompt_response(uuid, response)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {str(e)}")
        error_response = "Error: Invalid JSON format in request"
        request_data_handler.store_prompt_response(uuid, error_response)
        
    except Exception as e:
        logger.error(f"Unexpected error in handle_chat_prompt: {str(e)}")
        error_response = f"Error: Unexpected error occurred - {str(e)}"
        request_data_handler.store_prompt_response(uuid, error_response)


def handle_chat_prompt_with_fallback(uuid: str, payload: str):
    """Enhanced version with backward compatibility for old agents - COMPLETELY FIXED
    
    Args:
        uuid (str): uuid
        payload (str): body of the message
    """
    try:
        # Parse the payload
        body = json.loads(payload)
        logger.info(f"Processing request with payload keys: {list(body.keys())}")
        
        # Check if model_details exists (new agents) or not (old agents)
        model_details = body.get("model_details")
        
        if not model_details:
            # OLD AGENTS: Use original SERPAPI behavior for backward compatibility
            logger.info("No model_details found - using original SERPAPI behavior for backward compatibility")
            
            try:
                from elnachain import SERPAPI
                
                api_key = os.environ.get("OPEN_AI_KEY")
                if not api_key:
                    error_response = "Error: No OpenAI API key available for fallback"
                    request_data_handler.store_prompt_response(uuid, error_response)
                    return
                
                # Use original SERPAPI model (as in original code)
                llm = SERPAPI(api_key=api_key, logger=logger)
                template = PromptTemplate(
                    body=body,
                    logger=logger,
                )
                chat_prompt = template.format_message()
                response = llm(chat_prompt)
                
                # Validate response
                if not response or response.strip() == "":
                    logger.error("SERPAPI returned empty response")
                    response = "I apologize, but I couldn't generate a response. Please try again."
                
                logger.info(f"SERPAPI response generated successfully: {str(response)[:100]}...")
                
                # Store just the response text for old agents (no metadata)
                request_data_handler.store_prompt_response(uuid, response)
                
                # Log model information separately for tracking
                logger.info(f"Model info: Using OpenAI SERPAPI (fallback for old agents)")
                return
                
            except Exception as e:
                logger.error(f"Original SERPAPI approach failed: {str(e)}")
                error_response = "I apologize, but I'm experiencing technical difficulties. Please try again."
                request_data_handler.store_prompt_response(uuid, error_response)
                return
        
        # NEW AGENTS: Use dynamic model selection
        logger.info("model_details found - using dynamic model selection")
        
        # Validate model_details structure
        required_fields = ["platform", "apiKey"]
        for field in required_fields:
            if not model_details.get(field):
                logger.error(f"Missing required field in model_details: {field}")
                error_response = f"Error: Missing required field '{field}' in model configuration"
                request_data_handler.store_prompt_response(uuid, error_response)
                return
        
        # Check if web search/tools should be enabled
        enable_tools = body.get("enable_web_search", False) or body.get("enable_tools", False)
        
        # Create the appropriate model
        try:
            llm = create_model_from_request(model_details, enable_tools=enable_tools, logger=logger)
            logger.info(f"Successfully created {model_details['platform']} model")
        except Exception as e:
            logger.error(f"Failed to create model: {str(e)}")
            error_response = f"Error: Failed to initialize {model_details.get('platform', 'unknown')} model - {str(e)}"
            request_data_handler.store_prompt_response(uuid, error_response)
            return
        
        # Create prompt template
        template = PromptTemplate(
            body=body,
            logger=logger,
        )
        
        # Format the message for the model
        try:
            chat_prompt = template.format_message()
            logger.info(f"Generated prompt for {model_details['platform']} model")
        except Exception as e:
            logger.error(f"Failed to format prompt: {str(e)}")
            error_response = f"Error: Failed to format prompt - {str(e)}"
            request_data_handler.store_prompt_response(uuid, error_response)
            return
        
        # Generate response using the selected model
        try:
            response = llm(chat_prompt)
            
            # Validate response
            if not response or response.strip() == "":
                logger.error("Model returned empty response")
                response = "I apologize, but I couldn't generate a response. Please try again."
            
            logger.info(f"AI response generated successfully using {model_details['platform']}: {str(response)[:100]}...")
            
            # CRITICAL FIX: Check if response is a JSON string and extract just the response
            try:
                # If the model returned JSON with metadata, extract just the response
                if response.strip().startswith('{') and '"response"' in response:
                    parsed_response = json.loads(response)
                    if isinstance(parsed_response, dict) and 'response' in parsed_response:
                        response = parsed_response['response']
                        logger.info("Extracted response from JSON metadata wrapper")
            except (json.JSONDecodeError, KeyError):
                # If it's not JSON or doesn't have the expected structure, use as-is
                pass
            
            # CRITICAL FIX: Store ONLY the clean response text (NO metadata wrapper)
            request_data_handler.store_prompt_response(uuid, response)
            
            # Log model information separately for internal tracking only
            logger.info(f"Model info: Using {model_details['platform']} - {model_details.get('modelName', 'default')} (dynamic selection)")
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            response = f"Error: Failed to generate response using {model_details.get('platform', 'unknown')} model - {str(e)}"
            # Store error response normally
            request_data_handler.store_prompt_response(uuid, response)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {str(e)}")
        error_response = "Error: Invalid JSON format in request"
        request_data_handler.store_prompt_response(uuid, error_response)
        
    except Exception as e:
        logger.error(f"Unexpected error in handle_chat_prompt_with_fallback: {str(e)}")
        error_response = f"Error: Unexpected error occurred - {str(e)}"
        request_data_handler.store_prompt_response(uuid, error_response)


@tracer.capture_lambda_handler
def invoke(event: dict, context: LambdaContext):
    """Lambda Invoke function with backward compatibility

    Args:
        event (dict): SQS event with message records
        context (LambdaContext): Lambda context
    """
    records = event["Records"]
    logger.info(f"New event: {len(records)} records found for event -> {str(event)}")
    
    # Process each record in the event
    for record in records:
        try:
            payload = json.loads(record["body"])
            uuid = record["attributes"]["MessageGroupId"]
            
            # Use the backward compatible handler
            handle_chat_prompt_with_fallback(uuid, json.dumps(payload))
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            # Try to extract UUID for error storage
            try:
                uuid = record["attributes"]["MessageGroupId"]
                error_response = f"Error: Failed to process request - {str(e)}"
                request_data_handler.store_prompt_response(uuid, error_response)
            except:
                logger.error("Could not store error response - UUID extraction failed")