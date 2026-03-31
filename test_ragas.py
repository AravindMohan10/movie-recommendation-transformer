import asyncio
import os
from openai import AsyncOpenAI
from ragas.metrics import DiscreteMetric
from ragas.llms import llm_factory

client = AsyncOpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)
llm = llm_factory("llama-3.3-70b-versatile", provider="openai", client=client)

metric = DiscreteMetric(
    name="faithfulness_check",
    allowed_values=["faithful", "unfaithful"],
    prompt="""Check if the response is faithful to the context provided.
Context: {context}
Response: {response}
Answer with only 'faithful' or 'unfaithful'."""
)

async def main():
    score = await metric.ascore(
        llm=llm,
        context="Interstellar is a 2014 sci-fi film by Christopher Nolan about love, time, and survival.",
        response="You should watch Interstellar for its emotional storytelling and stunning visuals."
    )
    print(f"Score: {score.value}")
    print(f"Reason: {score.reason}")

asyncio.run(main())