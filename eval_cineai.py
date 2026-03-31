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

user_preferences = """User's favorite movies and reviews:
- Interstellar (favorited, 9/10) — loves emotionally driven sci-fi
- The Dark Knight (favorited 9/10, reviewed) — "One of Christopher Nolan's best work, Heath Ledger's performance as JOKER is one of the greatest"
- Spider-Man: Into the Spider-Verse (favorited 9/10, reviewed) — "the colours in this movie made me feel like I am eating the most delicious food"
- Schindler's List (favorited 9/10, reviewed) — "Masterpiece, accurate depiction of hardships, must watch"
- The Green Mile (favorited 9/10, reviewed) — "Beautiful movie, made me cry"
- Black Panther (favorited 9/10)
- Captain America: Civil War (favorited 9/10)
- A Quiet Place Part II (favorited 9/10)
- Also likes: Inception, Fight Club, The Matrix, Gladiator, Shutter Island, Parasite, Oldboy

Dislikes: Aladdin, Velvet Goldmine, Selena Gomez documentary"""

faithfulness_metric = DiscreteMetric(
    name="explanation_faithfulness",
    allowed_values=["faithful", "unfaithful"],
    prompt="""Check if every specific claim in the explanation can be directly verified in the movie overview.
Be strict — do not accept inferences or assumptions not explicitly stated.

Movie overview:
{context}

Explanation:
{response}

Answer with only 'faithful' or 'unfaithful'."""
)

preference_metric = DiscreteMetric(
    name="preference_alignment",
    allowed_values=["aligned", "not_aligned"],
    prompt="""Based on the user's movie history and preferences, evaluate if the recommended movie is a good fit.

User preferences and history:
{user_preferences}

Recommended movie:
Title: {title}
Overview: {context}
Explanation: {response}

Consider: Does this match the genres, themes, and emotional qualities the user enjoys?
Answer with only 'aligned' or 'not_aligned'."""
)

samples = [
    {
        "title": "Mission: Impossible III",
        "context": "Retired from active duty, and training recruits for the Impossible Mission Force, agent Ethan Hunt faces the toughest foe of his career: Owen Davian, an international broker of arms and information.",
        "ai_reason": "This action-packed film features a thrilling plot with a skilled agent facing off against a cunning foe."
    },
    {
        "title": "A Million Miles Away",
        "context": "The life of engineer and former NASA astronaut José M. Hernández, the first migrant farmworker to go to space.",
        "ai_reason": "This biographical drama tells the inspiring story of a NASA astronaut who overcame incredible obstacles to achieve his dreams."
    },
    {
        "title": "I Am Dragon",
        "context": "In the midst of the wedding princess Miroslava is kidnapped by a dragon and carried away into his castle on the remote island. Mira left everything behind in the past - family, friends and groom.",
        "ai_reason": "This fantasy romance film features a beautiful princess who must navigate a treacherous world filled with dragons."
    }
]

async def main():
    print("CineAI RAG Evaluation — Faithfulness + Preference Alignment")
    print("="*60)
    for sample in samples:
        print(f"\nMovie: {sample['title']}")
        print(f"Explanation: {sample['ai_reason']}")

        f_score = await faithfulness_metric.ascore(
            llm=llm,
            context=sample["context"],
            response=sample["ai_reason"]
        )

        p_score = await preference_metric.ascore(
            llm=llm,
            user_preferences=user_preferences,
            title=sample["title"],
            context=sample["context"],
            response=sample["ai_reason"]
        )

        print(f"Faithfulness: {f_score.value} — {f_score.reason}")
        print(f"Preference Alignment: {p_score.value} — {p_score.reason}")

asyncio.run(main())