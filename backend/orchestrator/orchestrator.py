from agency_swarm import Agent


class OrchestratorAgent(Agent):
    """
    The Orchestrator coordinates the fact-checking pipeline.
    It routes transcript chunks to specialist agents and
    aggregates their results. It never answers directly.
    """

    def __init__(self):
        super().__init__(
            name="Orchestrator",
            description=(
                "Coordinates the FactLens fact-checking pipeline. "
                "Routes transcript text to Claim Extractor, then sends "
                "each claim through Evidence Hunter and Verdict Generator. "
                "Never performs fact-checking itself."
            ),
            instructions="./instructions.md",
            tools=[],
            temperature=0.2,
        )
