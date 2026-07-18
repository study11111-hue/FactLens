from agency_swarm import Agent
from .tools.extract_claims import ExtractClaims


class ClaimExtractorAgent(Agent):
    """
    The Claim Extractor analyzes raw transcript text and
    identifies verifiable factual claims using NLP.
    """

    def __init__(self):
        super().__init__(
            name="ClaimExtractor",
            description=(
                "Analyzes raw transcript text from Google Meet conversations "
                "and extracts verifiable factual claims. Filters out opinions, "
                "greetings, questions, and non-factual statements."
            ),
            instructions="./instructions.md",
            tools=[ExtractClaims],
            temperature=0.1,
        )
