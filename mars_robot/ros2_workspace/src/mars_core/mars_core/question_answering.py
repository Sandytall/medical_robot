#!/usr/bin/env python3
"""
Question Answering System for Mars Robot
Handles "Hey mars i have a question" functionality with LLM API integration
"""
import os
import time
import json
import threading
from typing import Dict, Any, Optional, List

import rclpy
from rclpy.node import Node

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("OpenAI library not available. Install with: pip install openai")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Requests library not available. Install with: pip install requests")


class QuestionAnswering(Node):
    """Question answering handler using LLM APIs"""

    def __init__(self, hardware_manager, config: Dict[str, Any]):
        super().__init__('question_answering')

        self.hardware = hardware_manager
        self.config = config

        # Q&A state
        self.qa_active = False
        self.waiting_for_question = False
        self.processing_question = False
        self.current_question = ""
        self.conversation_history = []

        # LLM API configuration
        self.llm_config = self.config.get('llm_api', {})
        self.provider = self.llm_config.get('provider', 'openai')
        self.model = self.llm_config.get('model', 'gpt-3.5-turbo')
        self.max_tokens = self.llm_config.get('max_tokens', 150)
        self.temperature = self.llm_config.get('temperature', 0.7)

        # API credentials
        self.api_key = os.getenv(self.llm_config.get('api_key_env', 'OPENAI_API_KEY'))

        # System prompts
        self.prompts = self.llm_config.get('prompts', {})
        self.general_prompt = self.prompts.get('general',
            "You are MARS, a helpful hospital robot. Give brief, clear answers in 5 lines or less. "
            "Be friendly and professional. Focus on being helpful to patients and staff.")

        # Initialize API client
        self._initialize_llm_client()

        # Timeouts
        self.response_timeout = self.config.get('commands', {}).get('question_mode', {}).get('response_timeout', 60.0)
        self.api_timeout = 10.0  # API request timeout

        self.get_logger().info(f"Question Answering system initialized (Provider: {self.provider})")

    def _initialize_llm_client(self):
        """Initialize LLM API client"""
        try:
            if self.provider == 'openai' and OPENAI_AVAILABLE:
                if self.api_key:
                    openai.api_key = self.api_key
                    self.get_logger().info("OpenAI API client initialized")
                else:
                    self.get_logger().warning("OpenAI API key not found in environment")

            elif self.provider == 'anthropic':
                # TODO: Add Anthropic Claude API support
                self.get_logger().warning("Anthropic API not yet implemented")

            elif self.provider == 'local':
                # For local LLM endpoints
                self.get_logger().info("Local LLM endpoint configured")

        except Exception as e:
            self.get_logger().error(f"LLM client initialization error: {e}")

    def start_question_mode(self) -> bool:
        """Start question answering mode"""
        try:
            if self.qa_active:
                self.get_logger().warning("Question mode already active")
                return False

            self.qa_active = True
            self.waiting_for_question = True
            self.processing_question = False
            self.current_question = ""

            # Check if API is available
            if not self._check_api_availability():
                if self.hardware.audio:
                    self.hardware.audio.play_text("I'm sorry, but I cannot access the knowledge system right now. Please try again later.")
                self.qa_active = False
                return False

            # Set display to question mode
            if self.hardware.display:
                self.hardware.display.show_question_mode()

            # Announce question mode activation
            if self.hardware.audio:
                self.hardware.audio.play_text("I'm listening. What would you like to know?")

            # Start question processing thread
            threading.Thread(target=self._question_processing_loop, daemon=True).start()

            self.get_logger().info("Question answering mode started")
            return True

        except Exception as e:
            self.get_logger().error(f"Question mode start error: {e}")
            return False

    def stop_question_mode(self):
        """Stop question answering mode"""
        try:
            if not self.qa_active:
                return

            self.qa_active = False
            self.waiting_for_question = False
            self.processing_question = False

            # Announce mode exit
            if self.hardware.audio:
                self.hardware.audio.play_text("Question mode ended. How else can I help you?")

            self.get_logger().info("Question answering mode stopped")

        except Exception as e:
            self.get_logger().error(f"Question mode stop error: {e}")

    def process_question(self, question: str) -> bool:
        """Process a question from voice input"""
        try:
            if not self.qa_active or not self.waiting_for_question or self.processing_question:
                return False

            self.current_question = question.strip()
            self.waiting_for_question = False
            self.processing_question = True

            self.get_logger().info(f"Processing question: '{question}'")

            if self.hardware.audio:
                self.hardware.audio.play_text("Let me think about that...")

            if self.hardware.display:
                self.hardware.display.show_emotion(self.hardware.display.EmotionType.THINKING)

            return True

        except Exception as e:
            self.get_logger().error(f"Question processing error: {e}")
            return False

    def _question_processing_loop(self):
        """Question processing loop"""
        try:
            start_time = time.time()

            while self.qa_active:
                try:
                    # Check for timeout
                    if time.time() - start_time > self.response_timeout:
                        self.get_logger().info("Question mode timeout")
                        if self.hardware.audio:
                            self.hardware.audio.play_text("Question time expired. Exiting question mode.")
                        self.stop_question_mode()
                        break

                    # Process question if available
                    if self.processing_question and self.current_question:
                        answer = self._get_llm_response(self.current_question)

                        if answer:
                            self._deliver_answer(answer)
                        else:
                            self._deliver_error_response()

                        # Reset for next question
                        self.current_question = ""
                        self.processing_question = False
                        self.waiting_for_question = True
                        start_time = time.time()  # Reset timeout

                    time.sleep(0.5)

                except Exception as e:
                    self.get_logger().error(f"Question processing loop error: {e}")
                    time.sleep(1.0)

        except Exception as e:
            self.get_logger().error(f"Question thread error: {e}")

    def _check_api_availability(self) -> bool:
        """Check if LLM API is available"""
        try:
            if self.provider == 'openai' and OPENAI_AVAILABLE and self.api_key:
                return True
            elif self.provider == 'local':
                # TODO: Check local endpoint availability
                return True
            else:
                return False

        except Exception as e:
            self.get_logger().error(f"API availability check error: {e}")
            return False

    def _get_llm_response(self, question: str) -> Optional[str]:
        """Get response from LLM API"""
        try:
            if self.provider == 'openai':
                return self._get_openai_response(question)
            elif self.provider == 'local':
                return self._get_local_llm_response(question)
            else:
                self.get_logger().error(f"Unsupported LLM provider: {self.provider}")
                return None

        except Exception as e:
            self.get_logger().error(f"LLM response error: {e}")
            return None

    def _get_openai_response(self, question: str) -> Optional[str]:
        """Get response from OpenAI API"""
        try:
            if not OPENAI_AVAILABLE or not self.api_key:
                return None

            # Build conversation context
            messages = [
                {"role": "system", "content": self.general_prompt}
            ]

            # Add recent conversation history
            for entry in self.conversation_history[-5:]:  # Last 5 exchanges
                messages.append({"role": "user", "content": entry['question']})
                messages.append({"role": "assistant", "content": entry['answer']})

            # Add current question
            messages.append({"role": "user", "content": question})

            # Make API call
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                timeout=self.api_timeout
            )

            answer = response.choices[0].message.content.strip()

            # Store in conversation history
            self.conversation_history.append({
                'question': question,
                'answer': answer,
                'timestamp': time.time()
            })

            # Keep history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

            return answer

        except openai.error.RateLimitError:
            self.get_logger().warning("OpenAI API rate limit exceeded")
            return "I'm getting too many questions right now. Please wait a moment and try again."

        except openai.error.APIConnectionError:
            self.get_logger().warning("OpenAI API connection error")
            return "I'm having trouble connecting to my knowledge base. Please try again later."

        except openai.error.Timeout:
            self.get_logger().warning("OpenAI API timeout")
            return "That question is taking too long to process. Please try a simpler question."

        except Exception as e:
            self.get_logger().error(f"OpenAI API error: {e}")
            return None

    def _get_local_llm_response(self, question: str) -> Optional[str]:
        """Get response from local LLM endpoint"""
        try:
            # Example local LLM endpoint integration
            if not REQUESTS_AVAILABLE:
                return None

            # TODO: Implement local LLM endpoint call
            local_endpoint = self.llm_config.get('local_endpoint', 'http://localhost:8080/v1/chat/completions')

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.general_prompt},
                    {"role": "user", "content": question}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }

            response = requests.post(
                local_endpoint,
                json=payload,
                timeout=self.api_timeout,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content'].strip()
                return answer
            else:
                self.get_logger().error(f"Local LLM API error: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            self.get_logger().warning("Local LLM timeout")
            return "That question is taking too long to process."

        except requests.exceptions.ConnectionError:
            self.get_logger().warning("Local LLM connection error")
            return "I cannot connect to my knowledge system right now."

        except Exception as e:
            self.get_logger().error(f"Local LLM error: {e}")
            return None

    def _deliver_answer(self, answer: str):
        """Deliver answer to user"""
        try:
            # Ensure answer length is reasonable for TTS
            if len(answer) > 500:
                answer = answer[:500] + "..."

            # Log the Q&A exchange
            self.get_logger().info(f"Answer: {answer}")

            # Show happy emotion
            if self.hardware.display:
                self.hardware.display.show_emotion(self.hardware.display.EmotionType.HAPPY, 2.0)

            # Speak the answer
            if self.hardware.audio:
                self.hardware.audio.play_text(answer)

            # Show answer on display
            if self.hardware.display:
                self.hardware.display.show_text(f"Q&A\n{answer[:100]}{'...' if len(answer) > 100 else ''}")

            # Ask for follow-up
            time.sleep(1)
            if self.qa_active and self.hardware.audio:
                self.hardware.audio.play_text("Do you have any other questions?")

        except Exception as e:
            self.get_logger().error(f"Answer delivery error: {e}")

    def _deliver_error_response(self):
        """Deliver error response when LLM fails"""
        try:
            error_responses = [
                "I'm sorry, I couldn't process that question. Could you try rephrasing it?",
                "I'm having trouble understanding. Could you ask that in a different way?",
                "Let me get a human to help you with that question."
            ]

            import random
            error_message = random.choice(error_responses)

            if self.hardware.display:
                self.hardware.display.show_emotion(self.hardware.display.EmotionType.CONFUSED, 2.0)

            if self.hardware.audio:
                self.hardware.audio.play_text(error_message)

        except Exception as e:
            self.get_logger().error(f"Error response delivery error: {e}")

    def handle_voice_input(self, transcript: str) -> bool:
        """Handle voice input during Q&A mode"""
        try:
            if not self.qa_active:
                return False

            # Check for exit commands
            exit_phrases = ['exit', 'stop', 'no more questions', 'that\'s all', 'goodbye', 'never mind']
            if any(phrase in transcript.lower() for phrase in exit_phrases):
                self.stop_question_mode()
                return True

            # Process as a question
            if self.waiting_for_question:
                return self.process_question(transcript)

            return False

        except Exception as e:
            self.get_logger().error(f"Voice input handling error: {e}")
            return False

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.get_logger().info("Conversation history cleared")

    def is_qa_active(self) -> bool:
        """Check if Q&A mode is currently active"""
        return self.qa_active

    def get_qa_status(self) -> Dict[str, Any]:
        """Get current Q&A status"""
        return {
            'active': self.qa_active,
            'waiting_for_question': self.waiting_for_question,
            'processing_question': self.processing_question,
            'current_question': self.current_question,
            'conversation_length': len(self.conversation_history),
            'provider': self.provider,
            'model': self.model,
            'api_available': self._check_api_availability()
        }

    def cleanup(self):
        """Cleanup Q&A resources"""
        try:
            if self.qa_active:
                self.stop_question_mode()

            self.clear_conversation_history()

        except Exception as e:
            self.get_logger().error(f"Q&A cleanup error: {e}")