import logging
import json
import aiohttp
import re
import time
from typing import Union, Dict, List, Any, Optional

logger = logging.getLogger("NinjaBot." + __name__)

class NinjaAI:
    """A helper class to handle AI integrations for the bot"""
    def __init__(self, bot) -> None:
        self.bot = bot
        self.http = aiohttp.ClientSession()
        self.ai_config = self._get_ai_config()
        self.channel_instructions = self._get_channel_instructions()
        logger.info(f"NinjaAI initialized with config: {self.ai_config}")
        logger.info(f"Channel instructions configured: {list(self.channel_instructions.keys()) if self.channel_instructions else 'None'}")
        
    def _get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration from the bot config"""
        default_config = {
            "enabled": False,
            "service": "NONE",
            "api_key": "",
            "model": "",
            "api_url": "",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Try to get AI configuration from bot config
        if self.bot.config.has("ai"):
            ai_config = self.bot.config.get("ai")
            logger.info(f"Found AI config in bot config: {ai_config}")
            return ai_config
            
        logger.warning("No AI config found in bot config, using defaults")
        return default_config
    
    def _get_channel_instructions(self) -> Dict[str, str]:
        """Get channel-specific instructions from the bot config"""
        if self.bot.config.has("channelInstructions"):
            return self.bot.config.get("channelInstructions")
        return {}
    
    def _get_system_instruction(self, channel_id: str) -> str:
        """Get the appropriate system instruction for the given channel"""
        # Default instruction if no channel-specific one is found
        default_instruction = (
            "You are VDO.Ninja's support assistant on Discord. VDO.Ninja is a free, open-source tool for "
            "WebRTC-based peer-to-peer video streaming, used by broadcasters and content creators.\n\n"
            "Key resources to reference:\n"
            "- Documentation: https://docs.vdo.ninja/\n"
            "- FAQ: https://docs.vdo.ninja/faq\n"
            "- GitHub Issues: https://github.com/steveseguin/vdo.ninja/issues\n"
            "- Related projects: Raspberry.Ninja (Raspberry Pi streaming), Social Stream Ninja (social media chat overlays), Captioning.Ninja (real-time captions)\n\n"
            "Guidelines:\n"
            "- Be concise and helpful - Discord users prefer shorter responses\n"
            "- Reference documentation URLs when applicable\n"
            "- For browser issues, ask about browser type/version and whether hardware acceleration is enabled\n"
            "- For connection issues, suggest checking firewall/VPN settings and trying &relay or TURN servers\n"
            "- Common parameters: &push, &view, &room, &scene, &solo, &bitrate, &quality\n"
            "- If unsure or the question is complex, suggest waiting for human assistance from Steve or community members\n"
            "- Don't make up features or parameters that don't exist\n"
            "- OBS integration uses Browser Sources with specific URLs from VDO.Ninja"
        )
        
        # If we have channel-specific instructions, use them
        if channel_id in self.channel_instructions:
            logger.info(f"Using channel-specific instruction for channel {channel_id}")
            return self.channel_instructions[channel_id]
        
        logger.info(f"No channel-specific instruction found for channel {channel_id}, using default")
        return default_instruction
        
    # In NinjaAI.py - Add this new method (as shown before)
    async def should_respond_with_history(self, messages: List[Dict[str, Any]], channel_id: str = None) -> bool:
        """Determine if the AI should respond based on consolidated user message history"""
        logger.debug(f"Checking if AI should respond to message history in channel {channel_id}")
        
        # Check if AI is enabled
        if not self.ai_config.get("enabled", False):
            logger.info("AI is not enabled in config, will not respond")
            return False
            
        # Get all consecutive messages from the same user at the start of the thread
        user_messages = []
        user_id = None
        
        for msg in messages:
            current_user_id = msg.get("author", {}).get("id")
            is_bot = msg.get("author", {}).get("bot", False)
            
            # Skip bot messages
            if is_bot:
                continue
                
            # Set initial user_id if not set
            if user_id is None:
                user_id = current_user_id
                
            # Stop if we encounter a different user's message
            if current_user_id != user_id:
                break
                
            # Add this message content to our collection
            content = msg.get("content", "")
            if content:
                user_messages.append(content)
        
        # Combine all messages from the user
        combined_content = " ".join(user_messages)
        logger.debug(f"Combined message content: '{combined_content}'")
        
        # If the combined content is too short, don't respond
        if len(combined_content) < 15:
            logger.info(f"Combined message content is too short ({len(combined_content)} chars), will not respond")
            return False
            
        # Check if the user is asking a question in any of their messages
        question_indicators = ["?", "how", "what", "why", "where", "when", "who", "is", "can", "could", "would", "should", "help"]
        
        has_question = "?" in combined_content.lower()
        has_question_word = any(word in combined_content.lower().split() for word in question_indicators)
        
        logger.debug(f"Combined message has question mark: {has_question}")
        logger.debug(f"Combined message has question words: {has_question_word}")
        
        if has_question or has_question_word:
            logger.info("Combined messages appear to be a question, will respond")
            return True
            
        logger.info("Combined messages do not appear to be a question, will not respond")
        return False
    
    async def should_respond(self, messages: List[Dict[str, Any]], channel_id: str = None) -> bool:
        """Determine if the AI should respond based on the message history"""
        logger.debug(f"Checking if AI should respond to messages in channel {channel_id}: {messages}")
        
        # Check if AI is enabled
        if not self.ai_config.get("enabled", False):
            logger.info("AI is not enabled in config, will not respond")
            return False
            
        # Get the initial message content
        if not messages or len(messages) == 0:
            logger.info("No messages to respond to")
            return False
            
        initial_message = messages[0].get("content", "")
        logger.debug(f"Initial message: '{initial_message}'")
        
        # If there are no messages or the initial message is too short, don't respond
        if not initial_message:
            logger.info("Initial message is empty, will not respond")
            return False
            
        if len(initial_message) < 15:
            logger.info(f"Initial message is too short ({len(initial_message)} chars), will not respond")
            return False
            
        # Check if the user is asking a question
        question_indicators = ["?", "how", "what", "why", "where", "when", "who", "is", "can", "could", "would", "should", "help"]
        
        has_question = "?" in initial_message.lower()
        has_question_word = any(word in initial_message.lower().split() for word in question_indicators)
        
        logger.debug(f"Message has question mark: {has_question}")
        logger.debug(f"Message has question words: {has_question_word}")
        
        # Simple heuristic: if the message contains a question mark or question words, respond
        if has_question or has_question_word:
            # Additional check: if there are multiple messages and the last one is from the bot, don't respond
            if len(messages) > 1 and messages[-1].get("author", {}).get("bot", False):
                logger.info("Last message is from bot, will not respond")
                return False
                
            logger.info("Message appears to be a question, will respond")
            return True
            
        logger.info("Message does not appear to be a question, will not respond")
        return False
    
    def _format_messages_for_openai(self, messages: List[Dict[str, Any]], channel_id: str = None) -> List[Dict[str, str]]:
        """Format messages for OpenAI API"""
        formatted_messages = []
        
        # Add system message with the appropriate instruction for this channel
        system_instruction = self._get_system_instruction(channel_id)
        formatted_messages.append({
            "role": "system", 
            "content": system_instruction
        })
        
        # Add conversation history
        for msg in messages:
            role = "assistant" if msg.get("author", {}).get("bot", False) else "user"
            content = msg.get("content", "")
            
            # Skip empty messages
            if not content:
                continue
                
            formatted_messages.append({
                "role": role,
                "content": content
            })
            
        return formatted_messages
    
    def _format_messages_for_gemini(self, messages: List[Dict[str, Any]], channel_id: str = None) -> List[Dict[str, Any]]:
        """Format messages for Gemini API"""
        formatted_messages = []
        
        # Get the appropriate system instruction for this channel
        system_instruction = self._get_system_instruction(channel_id)
        
        # For Gemini API, we need to add system instruction as the first user message
        first_user_message = True
        
        # Add conversation history
        for msg in messages:
            role = "model" if msg.get("author", {}).get("bot", False) else "user"
            content = msg.get("content", "")
            
            # Skip empty messages
            if not content:
                continue
                
            # Add system instruction to first user message
            if role == "user" and first_user_message:
                first_user_message = False
                content = system_instruction + "\n\nUser question: " + content
                
            formatted_messages.append({
                "role": role,
                "parts": [{"text": content}]
            })
            
        # If no user messages were added, add a dummy system message
        if first_user_message:
            formatted_messages.append({
                "role": "user",
                "parts": [{"text": system_instruction + "\n\nPlease introduce yourself briefly."}]
            })
            
        return formatted_messages

    def _format_messages_for_ollama(self, messages: List[Dict[str, Any]], channel_id: str = None) -> List[Dict[str, Any]]:
        """Format messages for Ollama API"""
        formatted_messages = []
        
        # Add system message with the appropriate instruction for this channel
        system_instruction = self._get_system_instruction(channel_id)
        formatted_messages.append({
            "role": "system",
            "content": system_instruction
        })
        
        # Add conversation history
        for msg in messages:
            role = "assistant" if msg.get("author", {}).get("bot", False) else "user"
            content = msg.get("content", "")
            
            # Skip empty messages
            if not content:
                continue
                
            formatted_messages.append({
                "role": role,
                "content": content
            })
            
        return formatted_messages
    
    async def get_ai_response(self, messages: List[Dict[str, Any]], channel_id: str = None) -> Union[str, None]:
        """Get AI response based on the configured AI service"""
        service = self.ai_config.get("service", "NONE").upper()
        logger.info(f"Getting AI response using service: {service} for channel: {channel_id}")
        
        if service == "OPENAI":
            return await self._get_openai_response(messages, channel_id)
        elif service == "GEMINI":
            return await self._get_gemini_response(messages, channel_id)
        elif service == "OLLAMA":
            return await self._get_ollama_response(messages, channel_id)
        else:
            logger.warning(f"Unsupported AI service: {service}")
            return "I'm currently under maintenance. Please wait for a human to assist you."
    
    async def _get_openai_response(self, messages: List[Dict[str, Any]], channel_id: str = None) -> Union[str, None]:
        """Get response from OpenAI API"""
        try:
            api_key = self.ai_config.get("api_key", "")
            model = self.ai_config.get("model", "gpt-3.5-turbo")
            temperature = self.ai_config.get("temperature", 0.7)
            max_tokens = self.ai_config.get("max_tokens", 1000)
            
            if not api_key:
                logger.error("OpenAI API key not configured")
                return None
                
            # Format messages for OpenAI
            formatted_messages = self._format_messages_for_openai(messages, channel_id)
            
            # Prepare request data
            request_data = {
                "model": model,
                "messages": formatted_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Make request to OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            logger.debug(f"Sending request to OpenAI API with data: {json.dumps(request_data)}")
            
            async with self.http.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=request_data
            ) as response:
                response_text = await response.text()
                logger.debug(f"OpenAI API response: {response_text}")
                
                if response.status != 200:
                    logger.error(f"OpenAI API returned status {response.status}")
                    return None
                    
                response_data = json.loads(response_text)
                return response_data["choices"][0]["message"]["content"]
                
        except Exception as e:
            logger.exception(f"Error getting response from OpenAI: {e}")
            return None
    
    async def _get_gemini_response(self, messages: List[Dict[str, Any]], channel_id: str = None) -> Union[str, None]:
        """Get response from Gemini API"""
        try:
            api_key = self.ai_config.get("api_key", "")
            model = self.ai_config.get("model", "gemini-2.5-flash")
            temperature = self.ai_config.get("temperature", 0.7)
            max_tokens = self.ai_config.get("max_tokens", 1000)
            
            if not api_key:
                logger.error("Gemini API key not configured")
                return None
                
            # Format messages for Gemini
            formatted_messages = self._format_messages_for_gemini(messages, channel_id)
            
            # Prepare request data
            request_data = {
                "contents": formatted_messages,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            # Make request to Gemini API
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            
            # Log request data for debugging
            logger.info(f"Sending request to Gemini API: {api_url}")
            logger.debug(f"Request data: {json.dumps(request_data)}")
            
            try:
                async with self.http.post(
                    api_url,
                    json=request_data
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Gemini API response status: {response.status}")
                    logger.debug(f"Gemini API raw response: {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Gemini API returned error status {response.status}")
                        return None
                    
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Gemini API response as JSON: {e}")
                        return None
                    
                    # Extract the response text from the Gemini API response
                    if "candidates" in response_data and len(response_data["candidates"]) > 0:
                        candidate = response_data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                    
                    logger.error(f"Unexpected response format from Gemini: {response_data}")
                    return None
            except aiohttp.ClientError as e:
                logger.error(f"HTTP client error when calling Gemini API: {e}")
                return None
                
        except Exception as e:
            logger.exception(f"Error getting response from Gemini: {e}")
            return None
    
    async def _get_ollama_response(self, messages: List[Dict[str, Any]], channel_id: str = None) -> Union[str, None]:
        """Get response from Ollama API"""
        try:
            api_url = self.ai_config.get("api_url", "http://localhost:11434/api/chat")
            model = self.ai_config.get("model", "llama2")
            temperature = self.ai_config.get("temperature", 0.7)
            
            if not api_url:
                logger.error("Ollama API URL not configured")
                return None
                
            # Format messages for Ollama
            formatted_messages = self._format_messages_for_ollama(messages, channel_id)
            
            # Prepare request data
            request_data = {
                "model": model,
                "messages": formatted_messages,
                "options": {
                    "temperature": temperature
                },
                "stream": False
            }
            
            logger.debug(f"Sending request to Ollama API with data: {json.dumps(request_data)}")
            
            # Make request to Ollama API
            async with self.http.post(
                api_url,
                json=request_data
            ) as response:
                response_text = await response.text()
                logger.debug(f"Ollama API response: {response_text}")
                
                if response.status != 200:
                    logger.error(f"Ollama API returned status {response.status}")
                    return None
                    
                response_data = json.loads(response_text)
                return response_data["message"]["content"]
                
        except Exception as e:
            logger.exception(f"Error getting response from Ollama: {e}")
            return None
            
    async def close(self):
        """Close the HTTP session"""
        await self.http.close()