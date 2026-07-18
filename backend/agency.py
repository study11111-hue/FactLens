"""
FactLens Agency Definition
Configures the multi-agent swarm using Agency Swarm framework.
"""

# ── Pydantic Monkeypatch ────────────────────────────────
try:
    from openai.types.responses.response_usage import InputTokensDetails
    original_init = InputTokensDetails.__init__
    def patched_init(self, *args, **kwargs):
        kwargs.setdefault('cache_write_tokens', 0)
        kwargs.setdefault('cached_tokens', 0)
        original_init(self, *args, **kwargs)
    InputTokensDetails.__init__ = patched_init
except ImportError:
    pass

import os
from agency_swarm import Agency, set_openai_key

from orchestrator import OrchestratorAgent
from claim_extractor import ClaimExtractorAgent
from evidence_hunter import EvidenceHunterAgent
from verdict_generator import VerdictGeneratorAgent

from config import GROQ_API_KEY, GROQ_MODEL


def create_agency() -> Agency:
    """
    Create and configure the FactLens fact-checking agency.

    The agency has 4 specialized agents:
    - Orchestrator: Routes tasks, coordinates the pipeline
    - ClaimExtractor: Identifies verifiable claims from transcript
    - EvidenceHunter: Web search + RAG storage/retrieval
    - VerdictGenerator: Evaluates claims against evidence
    """

    # Configure Groq as the LLM provider via OpenAI-compatible API
    set_openai_key(GROQ_API_KEY)
    os.environ["OPENAI_API_KEY"] = GROQ_API_KEY
    os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"

    # Initialize agents
    orchestrator = OrchestratorAgent()
    claim_extractor = ClaimExtractorAgent()
    evidence_hunter = EvidenceHunterAgent()
    verdict_generator = VerdictGeneratorAgent()

    # Define the agency with communication flows
    # The list structure defines who can communicate with whom:
    # - Top-level list = user-facing agents (Orchestrator)
    # - Nested lists = communication pairs [sender, receiver]
    agency = Agency(
        agency_chart=[
            orchestrator,  # Orchestrator is the entry point
            [orchestrator, claim_extractor],
            [orchestrator, evidence_hunter],
            [orchestrator, verdict_generator],
            [evidence_hunter, verdict_generator],
        ],
        shared_instructions="./agency_manifesto.md",
        max_prompt_tokens=4096,
        temperature=0.2,
    )

    return agency


# Create a module-level agency instance
_agency = None


def get_agency() -> Agency:
    """Get or create the singleton agency instance."""
    global _agency
    if _agency is None:
        _agency = create_agency()
    return _agency


if __name__ == "__main__":
    agency = create_agency()
    agency.run_demo()
