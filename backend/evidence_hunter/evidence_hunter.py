from agency_swarm import Agent
from .tools.web_search import WebSearch
from .tools.store_evidence import StoreEvidence
from .tools.retrieve_evidence import RetrieveEvidence


class EvidenceHunterAgent(Agent):
    """
    The Evidence Hunter searches the web for evidence,
    stores results in a vector database (ChromaDB), and
    retrieves relevant context for fact-checking claims.
    """

    def __init__(self):
        super().__init__(
            name="EvidenceHunter",
            description=(
                "Searches the web for evidence about factual claims using "
                "Tavily AI, chunks and stores results in ChromaDB vector "
                "database, and retrieves the most relevant evidence for "
                "fact-checking."
            ),
            instructions="./instructions.md",
            tools=[WebSearch, StoreEvidence, RetrieveEvidence],
            temperature=0.3,
        )
