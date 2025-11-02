"""
RAG (Retrieval-Augmented Generation) + NLP Voice Interface
Multi-language voice assistant for cemetery navigation and information
Supports: Arabic, English, Urdu, Persian (Farsi)
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import openai
import json
import re

# Speech recognition and TTS
import speech_recognition as sr
from gtts import gTTS
import io

# For local LLM (optional)
# from langchain.llms import Ollama
# from langchain.embeddings import HuggingFaceEmbeddings
# from langchain.vectorstores import FAISS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class VoiceQuery:
    """Structured voice query"""
    original_text: str
    language: str
    intent: str  # search_person, get_directions, find_company, general_info
    entities: Dict[str, any]
    confidence: float


@dataclass
class VoiceResponse:
    """Structured voice response"""
    text: str
    audio_data: bytes
    language: str
    context: Dict
    success: bool


class MultilingualSpeechRecognizer:
    """
    Speech-to-text for multiple languages
    """
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
        # Language codes for speech recognition
        self.language_codes = {
            'arabic': 'ar-SA',
            'english': 'en-US',
            'urdu': 'ur-PK',
            'persian': 'fa-IR'
        }
    
    def recognize_from_audio_file(
        self,
        audio_file_path: str,
        language: str = 'arabic'
    ) -> Optional[str]:
        """Recognize speech from audio file"""
        
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
            
            # Try Google Speech Recognition
            lang_code = self.language_codes.get(language, 'ar-SA')
            text = self.recognizer.recognize_google(audio, language=lang_code)
            
            logger.info(f"Recognized ({language}): {text}")
            return text
            
        except sr.UnknownValueError:
            logger.error("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return None
    
    def recognize_from_microphone(
        self,
        language: str = 'arabic',
        timeout: int = 5
    ) -> Optional[str]:
        """Recognize speech from microphone"""
        
        try:
            with sr.Microphone() as source:
                logger.info("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout)
            
            lang_code = self.language_codes.get(language, 'ar-SA')
            text = self.recognizer.recognize_google(audio, language=lang_code)
            
            logger.info(f"Recognized ({language}): {text}")
            return text
            
        except Exception as e:
            logger.error(f"Microphone recognition error: {e}")
            return None
    
    def detect_language(self, text: str) -> str:
        """Detect language of text"""
        
        # Simple heuristic - check for Arabic characters
        if re.search(r'[\u0600-\u06FF]', text):
            # Check if it's Persian (has specific characters)
            if any(char in text for char in ['گ', 'چ', 'پ', 'ژ']):
                return 'persian'
            return 'arabic'
        
        # Check for Urdu (has specific characters)
        if re.search(r'[\u0600-\u06FF]', text) and any(char in text for char in ['ٹ', 'ڈ', 'ڑ']):
            return 'urdu'
        
        return 'english'


class NLPIntentClassifier:
    """
    Natural Language Understanding for intent classification
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        if openai_api_key:
            openai.api_key = openai_api_key
        
        # Intent patterns for different languages
        self.intent_patterns = {
            'search_person': {
                'arabic': [
                    r'أين.*قبر',
                    r'ابحث عن',
                    r'موقع.*المتوفى',
                    r'قبر.*شخص'
                ],
                'english': [
                    r'where.*grave',
                    r'find.*person',
                    r'locate.*burial',
                    r'search.*deceased'
                ]
            },
            'get_directions': {
                'arabic': [
                    r'كيف.*أصل',
                    r'الطريق.*إلى',
                    r'اشرح.*المسار',
                    r'وجهني'
                ],
                'english': [
                    r'how.*get',
                    r'directions.*to',
                    r'navigate.*to',
                    r'route.*to'
                ]
            },
            'find_company': {
                'arabic': [
                    r'شركة.*دفن',
                    r'مكتب.*جنائز'
                ],
                'english': [
                    r'burial.*company',
                    r'funeral.*service'
                ]
            }
        }
    
    def classify_intent(
        self,
        text: str,
        language: str = 'arabic'
    ) -> Tuple[str, float]:
        """
        Classify user intent from text
        
        Returns:
            Tuple of (intent, confidence)
        """
        
        # Try pattern matching first (fast)
        for intent, patterns in self.intent_patterns.items():
            lang_patterns = patterns.get(language, patterns.get('english', []))
            for pattern in lang_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return intent, 0.9
        
        # Use LLM for complex queries
        if self.openai_api_key:
            return self._classify_with_llm(text, language)
        
        # Default fallback
        return 'general_info', 0.5
    
    def _classify_with_llm(
        self,
        text: str,
        language: str
    ) -> Tuple[str, float]:
        """Use LLM (GPT) for intent classification"""
        
        prompt = f"""Classify the following cemetery-related query into one of these intents:
- search_person: Looking for a specific deceased person's grave
- get_directions: Asking for navigation/directions to a grave
- find_company: Looking for burial company information
- general_info: General information about the cemetery

Query: {text}
Language: {language}

Respond with just the intent name and confidence (0-1), format: intent,confidence
"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a cemetery information assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            intent, confidence = result.split(',')
            return intent.strip(), float(confidence.strip())
            
        except Exception as e:
            logger.error(f"LLM classification error: {e}")
            return 'general_info', 0.5
    
    def extract_entities(
        self,
        text: str,
        intent: str,
        language: str
    ) -> Dict:
        """Extract named entities from query"""
        
        entities = {}
        
        if intent == 'search_person':
            # Extract person name
            # For Arabic: typically after words like "قبر" or before "المتوفى"
            if language == 'arabic':
                # Simple extraction - in production use NER model
                name_match = re.search(r'(?:قبر|عن)\s+([\u0600-\u06FF\s]+)', text)
                if name_match:
                    entities['person_name'] = name_match.group(1).strip()
            else:
                # For English
                name_match = re.search(r'(?:grave of|find|person named)\s+([A-Za-z\s]+)', text, re.IGNORECASE)
                if name_match:
                    entities['person_name'] = name_match.group(1).strip()
        
        elif intent == 'find_company':
            # Extract company name
            entities['company_name'] = text  # Simplified
        
        return entities


class RAGCemeteryAssistant:
    """
    RAG (Retrieval-Augmented Generation) assistant for cemetery information
    Combines search results with LLM-generated responses
    """
    
    def __init__(
        self,
        search_engine,
        routing_engine,
        rules_engine,
        openai_api_key: Optional[str] = None
    ):
        self.search_engine = search_engine
        self.routing_engine = routing_engine
        self.rules_engine = rules_engine
        self.openai_api_key = openai_api_key
        
        if openai_api_key:
            openai.api_key = openai_api_key
    
    def generate_response(
        self,
        query: VoiceQuery,
        search_results: List = None,
        route_info: Dict = None
    ) -> str:
        """
        Generate natural language response using RAG
        Combines retrieved information with LLM generation
        """
        
        # Build context from retrieved information
        context_parts = []
        
        if search_results:
            context_parts.append("Search Results:")
            for i, result in enumerate(search_results[:3], 1):
                context_parts.append(
                    f"{i}. {result.deceased_name} - "
                    f"Buried: {result.burial_date}, "
                    f"Section: {result.section}, "
                    f"Location: {result.coordinates}"
                )
        
        if route_info:
            context_parts.append(f"\nRoute Information:")
            context_parts.append(f"Distance: {route_info.get('distance', 'N/A')}")
            context_parts.append(f"Duration: {route_info.get('duration', 'N/A')}")
        
        context = "\n".join(context_parts)
        
        # Generate response with LLM
        if self.openai_api_key and context:
            return self._generate_with_llm(query, context)
        else:
            return self._generate_template_response(query, search_results, route_info)
    
    def _generate_with_llm(
        self,
        query: VoiceQuery,
        context: str
    ) -> str:
        """Generate response using GPT"""
        
        system_prompt = self._get_system_prompt(query.language)
        
        user_prompt = f"""User Query: {query.original_text}
Intent: {query.intent}

Available Information:
{context}

Please provide a helpful, concise response in {query.language}.
"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return self._generate_template_response(query, None, None)
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt in appropriate language"""
        
        prompts = {
            'arabic': """أنت مساعد افتراضي لمقبرة النجف الأشرف. 
ساعد الزوار في العثور على القبور والتنقل في المقبرة.
كن محترمًا ومتعاطفًا ودقيقًا في معلوماتك.""",
            
            'english': """You are a virtual assistant for Najaf Cemetery.
Help visitors find graves and navigate the cemetery.
Be respectful, empathetic, and accurate in your information.""",
            
            'urdu': """آپ نجف کے قبرستان کے لیے ورچوئل اسسٹنٹ ہیں۔
زائرین کو قبریں تلاش کرنے اور قبرستان میں راستہ معلوم کرنے میں مدد کریں۔
معلومات میں احترام، ہمدردی اور درستگی کا خیال رکھیں۔""",
            
            'persian': """شما دستیار مجازی آرامستان نجف هستید.
به بازدیدکنندگان در یافتن مقابر و مسیریابی در آرامستان کمک کنید.
با احترام، همدلی و دقت در اطلاعات خود باشید."""
        }
        
        return prompts.get(language, prompts['english'])
    
    def _generate_template_response(
        self,
        query: VoiceQuery,
        search_results: List,
        route_info: Dict
    ) -> str:
        """Generate template-based response (fallback)"""
        
        templates = {
            'arabic': {
                'search_person': """وجدت {count} نتيجة لـ {name}.
أقرب قبر في القسم {section}، الصف {row}، المقبرة {plot}.""",
                'get_directions': """المسافة إلى القبر: {distance} متر.
الوقت المقدر: {duration} دقيقة.""",
                'no_results': """عذراً، لم أتمكن من العثور على نتائج لهذا الاستعلام."""
            },
            'english': {
                'search_person': """Found {count} result(s) for {name}.
Nearest grave in Section {section}, Row {row}, Plot {plot}.""",
                'get_directions': """Distance to grave: {distance} meters.
Estimated time: {duration} minutes.""",
                'no_results': """Sorry, I couldn't find any results for this query."""
            }
        }
        
        lang_templates = templates.get(query.language, templates['english'])
        
        if not search_results:
            return lang_templates['no_results']
        
        if query.intent == 'search_person':
            result = search_results[0]
            return lang_templates['search_person'].format(
                count=len(search_results),
                name=query.entities.get('person_name', ''),
                section=result.section or 'N/A',
                row=result.row_number or 'N/A',
                plot=result.plot_number or 'N/A'
            )
        
        return lang_templates['no_results']


class TextToSpeech:
    """Text-to-speech for multiple languages"""
    
    def __init__(self):
        self.language_codes = {
            'arabic': 'ar',
            'english': 'en',
            'urdu': 'ur',
            'persian': 'fa'
        }
    
    def generate_speech(
        self,
        text: str,
        language: str = 'arabic'
    ) -> bytes:
        """Generate speech audio from text"""
        
        lang_code = self.language_codes.get(language, 'ar')
        
        try:
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            # Convert to bytes
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            return audio_buffer.read()
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return b''


class VoiceAssistant:
    """
    Complete voice assistant integrating all components
    """
    
    def __init__(
        self,
        search_engine,
        routing_engine,
        rules_engine,
        openai_api_key: Optional[str] = None
    ):
        self.speech_recognizer = MultilingualSpeechRecognizer()
        self.intent_classifier = NLPIntentClassifier(openai_api_key)
        self.rag_assistant = RAGCemeteryAssistant(
            search_engine,
            routing_engine,
            rules_engine,
            openai_api_key
        )
        self.tts = TextToSpeech()
    
    def process_voice_query(
        self,
        audio_file_path: Optional[str] = None,
        text_query: Optional[str] = None,
        language: str = 'arabic'
    ) -> VoiceResponse:
        """
        Process complete voice query and return voice response
        
        Args:
            audio_file_path: Path to audio file (if not using text)
            text_query: Text query (if not using audio)
            language: Expected language
            
        Returns:
            VoiceResponse with text and audio
        """
        
        # Step 1: Speech to Text
        if audio_file_path:
            query_text = self.speech_recognizer.recognize_from_audio_file(
                audio_file_path,
                language
            )
        elif text_query:
            query_text = text_query
            language = self.speech_recognizer.detect_language(query_text)
        else:
            return VoiceResponse(
                text="No input provided",
                audio_data=b'',
                language=language,
                context={},
                success=False
            )
        
        if not query_text:
            return VoiceResponse(
                text="Could not understand audio",
                audio_data=b'',
                language=language,
                context={},
                success=False
            )
        
        # Step 2: Intent Classification
        intent, confidence = self.intent_classifier.classify_intent(
            query_text,
            language
        )
        
        # Step 3: Entity Extraction
        entities = self.intent_classifier.extract_entities(
            query_text,
            intent,
            language
        )
        
        voice_query = VoiceQuery(
            original_text=query_text,
            language=language,
            intent=intent,
            entities=entities,
            confidence=confidence
        )
        
        # Step 4: Execute appropriate action
        search_results = None
        route_info = None
        
        if intent == 'search_person' and 'person_name' in entities:
            from search_engine import SearchQuery
            search_query = SearchQuery(
                query=entities['person_name'],
                language=language,
                fuzzy=True
            )
            search_results = self.rag_assistant.search_engine.search_by_name(
                search_query
            )
        
        elif intent == 'get_directions' and search_results:
            # Get route to first result
            first_result = search_results[0]
            route = self.rag_assistant.routing_engine.get_route_to_grave(
                first_result.record_id
            )
            if route:
                route_info = {
                    'distance': f"{route.total_distance_meters:.0f}m",
                    'duration': f"{route.total_duration_seconds / 60:.0f}min"
                }
        
        # Step 5: Generate response
        response_text = self.rag_assistant.generate_response(
            voice_query,
            search_results,
            route_info
        )
        
        # Step 6: Text to Speech
        audio_data = self.tts.generate_speech(response_text, language)
        
        return VoiceResponse(
            text=response_text,
            audio_data=audio_data,
            language=language,
            context={
                'intent': intent,
                'entities': entities,
                'results_count': len(search_results) if search_results else 0
            },
            success=True
        )


def main():
    """Test the voice assistant"""
    
    # Would need to initialize all engines
    assistant = VoiceAssistant(
        search_engine=None,  # Initialize with actual search engine
        routing_engine=None,  # Initialize with actual routing engine
        rules_engine=None,  # Initialize with actual rules engine
        openai_api_key="your-api-key"
    )
    
    # Test with text query
    response = assistant.process_voice_query(
        text_query="أين قبر محمد علي حسن؟",
        language='arabic'
    )
    
    print(f"Response: {response.text}")
    print(f"Language: {response.language}")
    print(f"Success: {response.success}")


if __name__ == "__main__":
    main()
