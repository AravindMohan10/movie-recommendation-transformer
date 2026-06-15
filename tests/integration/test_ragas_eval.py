"""
Optional RAGAS / Groq evaluation script. Skipped unless GROQ_API_KEY is set.

Run: pytest tests/integration/test_ragas_eval.py -m integration
"""
from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
def test_ragas_faithfulness_metric_smoke():
    import asyncio

    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.metrics import DiscreteMetric

    client = AsyncOpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )
    llm = llm_factory("llama-3.3-70b-versatile", provider="openai", client=client)
    metric = DiscreteMetric(
        name="faithfulness_check",
        allowed_values=["faithful", "unfaithful"],
        prompt=(
            "Check if the response is faithful to the context.\n"
            "Context: {context}\nResponse: {response}\n"
            "Answer with only 'faithful' or 'unfaithful'."
        ),
    )

    async def run():
        return await metric.ascore(
            llm=llm,
            context="Interstellar is a 2014 sci-fi film by Christopher Nolan.",
            response="Interstellar has emotional storytelling and stunning visuals.",
        )

    score = asyncio.run(run())
    assert score.value in ("faithful", "unfaithful")
