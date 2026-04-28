import os
import logging
import httpx
import json
from fastapi import HTTPException

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

# Fast, cheap model — perfect for translation
TRANSLATION_MODEL = "llama-3.1-8b-instant"


async def detect_and_translate(text: str) -> dict:
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — skipping translation, using text as-is.")
        return {
            "original_text": text,
            "translated_text": text,
            "detected_language": "Unknown",
            "was_translated": False,
        }

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Text for translation cannot be empty.")

    system_prompt = (
        "You are a language detection and translation assistant. "
        "Your job is to analyze input text, detect its language, and if it is not English, "
        "translate it into clear, descriptive English suitable for an AI image generation prompt. "
        "Preserve the meaning, imagery, and descriptive details as faithfully as possible. "
        "Respond ONLY with a valid JSON object — no markdown, no extra text, no backticks.\n\n"
        "JSON format:\n"
        "{\n"
        '  "detected_language": "<language name in English, e.g. Hindi, Marathi, French>",\n'
        '  "is_english": <true or false>,\n'
        '  "translated_text": "<English translation, or the original text if already English>"\n'
        "}"
    )

    user_message = f'Detect the language and translate this text if needed:\n\n"{text}"'

    payload = {
        "model": TRANSLATION_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.2,   # Low temperature for deterministic translation
        "max_tokens": 512,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code != 200:
            logger.error("Groq translation API error %d: %s", response.status_code, response.text)
            # Graceful fallback: don't crash the whole pipeline
            logger.warning("Translation failed — using original transcript as image prompt.")
            return {
                "original_text": text,
                "translated_text": text,
                "detected_language": "Unknown",
                "was_translated": False,
            }

        result = response.json()
        raw_content = result["choices"][0]["message"]["content"].strip()

        # Strip markdown code fences if LLM includes them despite instructions
        if raw_content.startswith("```"):
            raw_content = raw_content.strip("`").strip()
            if raw_content.startswith("json"):
                raw_content = raw_content[4:].strip()

        parsed = json.loads(raw_content)

        detected_language = parsed.get("detected_language", "Unknown")
        is_english = parsed.get("is_english", False)
        translated_text = parsed.get("translated_text", text).strip()

        # Safety: if translation came back empty, fall back to original
        if not translated_text:
            translated_text = text

        was_translated = not is_english

        if was_translated:
            logger.info(
                "Translated from %s: %r → %r",
                detected_language,
                text[:80],
                translated_text[:80],
            )
        else:
            logger.info("Text is already English (%s) — no translation needed.", detected_language)

        return {
            "original_text": text,
            "translated_text": translated_text,
            "detected_language": detected_language,
            "was_translated": was_translated,
        }

    except json.JSONDecodeError as e:
        logger.error("Failed to parse translation response as JSON: %s | Raw: %s", e, raw_content)
        # Graceful fallback
        return {
            "original_text": text,
            "translated_text": text,
            "detected_language": "Unknown",
            "was_translated": False,
        }
    except httpx.TimeoutException:
        logger.error("Translation request timed out.")
        return {
            "original_text": text,
            "translated_text": text,
            "detected_language": "Unknown",
            "was_translated": False,
        }
    except httpx.RequestError as exc:
        logger.error("Network error calling Groq for translation: %s", exc)
        return {
            "original_text": text,
            "translated_text": text,
            "detected_language": "Unknown",
            "was_translated": False,
        }