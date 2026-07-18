"""
GenerateVerdict Tool
Evaluates a claim against evidence and produces a structured verdict.
"""

import json
import os

from agency_swarm.tools import BaseTool
from pydantic import Field
from groq import Groq


VERDICT_PROMPT = """You are a rigorous fact-checking engine. Evaluate the following claim against the provided evidence and produce a verdict.

CLAIM: "{claim}"

EVIDENCE:
{evidence}

Evaluate the claim and return a JSON object with these fields:
- "verdict": One of "TRUE", "FALSE", "MISLEADING", or "UNVERIFIED"
- "confidence": A float between 0.0 and 1.0 indicating your confidence
- "explanation": A clear, concise explanation (2-3 sentences) of why you reached this verdict
- "reasoning": A detailed reasoning chain showing how you evaluated the evidence
- "sources": An array of source URLs that support your verdict

Scoring guidelines:
- 0.9-1.0: Multiple authoritative sources agree strongly
- 0.7-0.89: Strong evidence, minor gaps
- 0.5-0.69: Mixed or limited evidence
- 0.3-0.49: Weak evidence, conflicting sources
- 0.0-0.29: No reliable evidence found

Return ONLY a valid JSON object. No other text.
"""


class GenerateVerdict(BaseTool):
    """
    Evaluates a factual claim against retrieved evidence
    and produces a structured verdict with confidence score,
    explanation, and source citations.
    """

    claim_text: str = Field(
        ...,
        description="The factual claim to evaluate.",
    )
    evidence_json: str = Field(
        ...,
        description=(
            "JSON string containing evidence chunks to evaluate "
            "the claim against. Should include text, source_url, "
            "and source_title fields."
        ),
    )
    speaker: str = Field(
        default="Unknown",
        description="The speaker who made the claim.",
    )

    def run(self) -> str:
        """Generate a fact-check verdict."""
        client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))

        # Format evidence for the prompt
        try:
            evidence_data = json.loads(self.evidence_json)
            if isinstance(evidence_data, dict):
                evidence_list = evidence_data.get("evidence", [])
            elif isinstance(evidence_data, list):
                evidence_list = evidence_data
            else:
                evidence_list = []
        except (json.JSONDecodeError, TypeError):
            evidence_list = []

        if not evidence_list:
            return json.dumps({
                "claim_text": self.claim_text,
                "verdict": "UNVERIFIED",
                "confidence": 0.2,
                "explanation": "No evidence could be found to verify or refute this claim.",
                "reasoning": "The evidence retrieval returned no relevant results.",
                "sources": [],
                "speaker": self.speaker,
            })

        evidence_text = ""
        for i, e in enumerate(evidence_list, 1):
            text = e.get("text", "")
            url = e.get("source_url", "")
            title = e.get("source_title", "")
            score = e.get("similarity_score", 0.0)
            evidence_text += (
                f"\n[{i}] (Relevance: {score})\n"
                f"Source: {title} ({url})\n"
                f"Content: {text}\n"
            )

        try:
            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise, objective fact-checking engine. "
                            "Return only valid JSON objects."
                        ),
                    },
                    {
                        "role": "user",
                        "content": VERDICT_PROMPT.format(
                            claim=self.claim_text,
                            evidence=evidence_text,
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content.strip()
            verdict_data = json.loads(content)

            # Ensure required fields
            verdict_data["claim_text"] = self.claim_text
            verdict_data["speaker"] = self.speaker
            verdict_data.setdefault("verdict", "UNVERIFIED")
            verdict_data.setdefault("confidence", 0.5)
            verdict_data.setdefault("explanation", "")
            verdict_data.setdefault("reasoning", "")
            verdict_data.setdefault("sources", [])

            # Clamp confidence
            verdict_data["confidence"] = max(
                0.0, min(1.0, float(verdict_data["confidence"]))
            )

            return json.dumps(verdict_data, indent=2)

        except json.JSONDecodeError:
            return json.dumps({
                "claim_text": self.claim_text,
                "verdict": "UNVERIFIED",
                "confidence": 0.3,
                "explanation": "Error parsing the verdict response.",
                "reasoning": "LLM response was not valid JSON.",
                "sources": [],
                "speaker": self.speaker,
            })
        except Exception as e:
            return json.dumps({
                "claim_text": self.claim_text,
                "verdict": "UNVERIFIED",
                "confidence": 0.0,
                "explanation": f"Error generating verdict: {str(e)}",
                "reasoning": "",
                "sources": [],
                "speaker": self.speaker,
            })
