"""
ExtractClaims Tool
Parses transcript text and extracts verifiable factual claims using Groq.
"""

import json
import os

from pydantic import BaseModel, Field
from groq import Groq


EXTRACTION_PROMPT = """You are a fact-claim extraction engine. Analyze the following transcript text and extract ALL verifiable factual claims.

For each claim, provide:
- "claim_text": The exact factual assertion (rewrite for clarity if needed)
- "speaker": Who said it (if identifiable from the text, otherwise "Unknown")
- "category": One of: "statistics", "historical", "scientific", "current_events", "attribution", "geographical", "general"

Rules:
- ONLY extract verifiable factual claims (things that can be proven true or false)
- DO NOT extract opinions, predictions, questions, greetings, or subjective statements
- Keep claim_text concise and focused on the core assertion
- If no verifiable claims exist, return an empty array

Return ONLY a valid JSON array. No other text.

Transcript:
\"\"\"
{transcript}
\"\"\"
"""


class ExtractClaims(BaseModel):
    """
    Extracts verifiable factual claims from raw transcript text.
    Uses Groq LLM to parse and identify claims that can be fact-checked.
    """

    transcript_text: str = Field(
        ...,
        description="The raw transcript text from Google Meet to extract claims from.",
    )
    speaker: str = Field(
        default="Unknown",
        description="The speaker who said this text, if known.",
    )

    def run(self) -> str:
        """Extract factual claims from the transcript text."""
        client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

        try:
            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise fact-claim extraction engine. Return only valid JSON arrays.",
                    },
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(
                            transcript=self.transcript_text
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()

            # Parse and validate the response
            parsed = json.loads(content)

            # Handle both {"claims": [...]} and [...] formats
            if isinstance(parsed, dict) and "claims" in parsed:
                claims = parsed["claims"]
            elif isinstance(parsed, list):
                claims = parsed
            else:
                claims = []

            # Add default speaker if not specified per claim
            for claim in claims:
                if not claim.get("speaker") or claim["speaker"] == "Unknown":
                    claim["speaker"] = self.speaker

            return json.dumps(claims, indent=2)

        except json.JSONDecodeError:
            return "[]"
        except Exception as e:
            return json.dumps({"error": str(e), "claims": []})
