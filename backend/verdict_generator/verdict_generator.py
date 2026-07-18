from agency_swarm import Agent
from .tools.generate_verdict import GenerateVerdict
from .tools.retrieve_evidence import RetrieveEvidence


class VerdictGeneratorAgent(Agent):
    """
    The Verdict Generator evaluates factual claims against
    retrieved evidence and produces structured verdicts with
    confidence scores and source citations.
    """

    def __init__(self):
        super().__init__(
            name="VerdictGenerator",
            description=(
                "Evaluates factual claims against retrieved evidence. "
                "Produces structured verdicts (TRUE/FALSE/MISLEADING/UNVERIFIED) "
                "with confidence scores, explanations, and source citations."
            ),
            instructions="./instructions.md",
            tools=[RetrieveEvidence, GenerateVerdict],
            temperature=0.1,
        )
