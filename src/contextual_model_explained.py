#!/usr/bin/env python3
"""
Contextual Model - Theory and Implementation
This is the most sophisticated part - using review text to understand WHY people like movies!

WHAT IS CONTEXTUAL FILTERING?
=============================
Instead of just knowing "User A liked Movie X", we understand WHY:
- "The special effects were amazing!" → User likes visual spectacle
- "The story was boring" → User dislikes weak plots  
- "Great acting by Tom Hanks" → User appreciates good performances

KEY INSIGHT: Reviews contain rich information about user preferences
that ratings alone can't capture!
"""

import torch
import torch.nn as nn
import numpy as np
from transformers import AutoTokenizer, AutoModel
from textblob import TextBlob
import re
from typing import Dict, List, Tuple

class ContextualModelExplained:
    """
    CONTEXTUAL MODEL COMPONENTS:
    
    1. REVIEW SENTIMENT ANALYSIS
       - Positive reviews → User likes this type of movie
       - Negative reviews → User dislikes this type of movie
    
    2. REVIEW CONTENT UNDERSTANDING  
       - What aspects do users mention? (plot, acting, effects)
       - Which aspects drive positive/negative sentiment?
    
    3. USER PREFERENCE MODELING
       - Build user profiles based on review patterns
       - "This user loves action scenes but hates bad dialogue"
    
    4. MOVIE APPEAL MODELING
       - Understand what makes movies appealing
       - "This movie appeals to users who value cinematography"
    """
    
    def __init__(self):
        print("🎭 LEARNING: Contextual Recommendation with Reviews")
        print("="*60)
        print("CONCEPT: Use review text to understand user preferences")
        print("STRENGTH: Rich understanding of WHY users like movies")
        print("CHALLENGE: Only works for movies with reviews")
        print("DATA: 18,917 reviews across 7,439 movies (50.3% coverage)")
        print()
    
    def explain_sentiment_analysis(self):
        """
        Explain how sentiment analysis works
        """
        print("😊 SENTIMENT ANALYSIS EXPLAINED:")
        print("="*40)
        
        print("GOAL: Determine if a review is positive, negative, or neutral")
        print()
        
        # Example reviews with different sentiments
        reviews = [
            "This movie is absolutely fantastic! The acting is superb and the plot is engaging.",
            "Boring and predictable. Waste of time. Poor acting throughout.",
            "It was okay. Some good parts, some bad parts. Average movie overall.",
            "AMAZING special effects! Though the story could be better.",
            "Terrible dialogue but beautiful cinematography."
        ]
        
        print("EXAMPLE REVIEWS:")
        for i, review in enumerate(reviews, 1):
            # Simple sentiment analysis using TextBlob
            blob = TextBlob(review)
            sentiment = blob.sentiment.polarity  # -1 (negative) to 1 (positive)
            
            if sentiment > 0.1:
                sentiment_label = "POSITIVE"
            elif sentiment < -0.1:
                sentiment_label = "NEGATIVE"
            else:
                sentiment_label = "NEUTRAL"
            
            print(f"{i}. '{review[:50]}...'")
            print(f"   → Sentiment: {sentiment_label} (score: {sentiment:.2f})")
            print()
        
        print("💡 KEY INSIGHTS:")
        print("• Positive reviews indicate user enjoyed this type of content")
        print("• Negative reviews show what users want to avoid")
        print("• Mixed reviews reveal specific preferences (effects vs story)")
    
    def explain_aspect_extraction(self):
        """
        Explain how we extract specific aspects from reviews
        """
        print("\n🔍 ASPECT-BASED SENTIMENT ANALYSIS:")
        print("="*45)
        
        print("GOAL: Understand WHAT aspects users like/dislike")
        print()
        
        # Define movie aspects we care about
        aspects = {
            'plot': ['story', 'plot', 'narrative', 'script', 'screenplay'],
            'acting': ['acting', 'performance', 'actor', 'actress', 'cast'],
            'effects': ['effects', 'cgi', 'visual', 'graphics', 'animation'],
            'music': ['music', 'soundtrack', 'score', 'song'],
            'direction': ['director', 'direction', 'directing', 'filmmaker'],
            'cinematography': ['camera', 'shot', 'visual', 'photography', 'cinematography']
        }
        
        review = "The plot was weak but the visual effects were absolutely stunning. The acting felt wooden but the soundtrack was beautiful."
        
        print(f"EXAMPLE REVIEW: '{review}'")
        print()
        print("ASPECT EXTRACTION:")
        
        for aspect, keywords in aspects.items():
            # Check if any keywords appear in the review
            mentions = [word for word in keywords if word in review.lower()]
            if mentions:
                # Extract surrounding context
                for keyword in mentions:
                    context = self._extract_context(review, keyword)
                    sentiment = TextBlob(context).sentiment.polarity
                    
                    sentiment_label = "positive" if sentiment > 0 else "negative" if sentiment < 0 else "neutral"
                    print(f"• {aspect.upper()}: '{context}' → {sentiment_label} ({sentiment:.2f})")
        
        print("\n💡 USER PREFERENCE INSIGHTS:")
        print("This user values:")
        print("✅ Visual effects (positive)")
        print("✅ Music/soundtrack (positive)")
        print("❌ Weak plots (negative)")
        print("❌ Poor acting (negative)")
    
    def _extract_context(self, text: str, keyword: str, window: int = 10) -> str:
        """Extract context around a keyword"""
        words = text.lower().split()
        try:
            idx = words.index(keyword.lower())
            start = max(0, idx - window)
            end = min(len(words), idx + window + 1)
            return ' '.join(words[start:end])
        except ValueError:
            return ""
    
    def explain_user_profiling(self):
        """
        Explain how we build user profiles from reviews
        """
        print("\n👤 USER PROFILING FROM REVIEWS:")
        print("="*40)
        
        print("GOAL: Build detailed user preference profiles")
        print()
        
        # Simulate user review history
        user_reviews = [
            ("Action Movie A", 9, "Incredible action sequences! Non-stop thrills."),
            ("Romance Movie B", 3, "Too slow paced. Boring romantic subplot."),
            ("Sci-Fi Movie C", 8, "Amazing special effects and great world-building."),
            ("Drama Movie D", 4, "Well acted but the story dragged on."),
            ("Action Movie E", 9, "Spectacular stunts and perfect pacing!")
        ]
        
        print("USER'S REVIEW HISTORY:")
        for movie, rating, review in user_reviews:
            print(f"• {movie} (★{rating}/10): '{review}'")
        
        print("\nPROFILE ANALYSIS:")
        
        # Analyze patterns
        action_ratings = [r for m, r, rev in user_reviews if 'action' in m.lower()]
        romance_ratings = [r for m, r, rev in user_reviews if 'romance' in m.lower()]
        
        print(f"Action movies average: {np.mean(action_ratings):.1f}/10")
        print(f"Romance movies average: {np.mean(romance_ratings):.1f}/10")
        
        # Extract preference keywords
        high_rated_words = []
        low_rated_words = []
        
        for movie, rating, review in user_reviews:
            words = review.lower().split()
            if rating >= 7:
                high_rated_words.extend(words)
            elif rating <= 4:
                low_rated_words.extend(words)
        
        print(f"\nWORDS IN HIGH-RATED REVIEWS: {set(high_rated_words)}")
        print(f"WORDS IN LOW-RATED REVIEWS: {set(low_rated_words)}")
        
        print("\n🎯 USER PREFERENCE PROFILE:")
        print("LOVES: Action, special effects, pacing, stunts")
        print("DISLIKES: Slow pace, romantic subplots, dragging stories")
        print("GENRE PREFERENCE: Action > Sci-Fi > Drama > Romance")
    
    def explain_contextual_embedding(self):
        """
        Explain how we create contextual embeddings
        """
        print("\n🧠 CONTEXTUAL EMBEDDINGS:")
        print("="*35)
        
        print("GOAL: Create movie representations that include review insights")
        print()
        
        print("TRADITIONAL CONTENT EMBEDDING:")
        print("Movie → [Title + Overview + Genres] → BERT → Embedding")
        print()
        print("CONTEXTUAL EMBEDDING:")
        print("Movie → [Content + Review Summaries + Sentiment] → BERT → Richer Embedding")
        
        print("\nEXAMPLE:")
        movie_content = "Star Wars: A space epic about rebels fighting an empire"
        review_summary = "Users love: amazing effects, epic story, great characters. Users dislike: some pacing issues"
        
        print(f"Content: '{movie_content}'")
        print(f"Review insights: '{review_summary}'")
        print(f"Combined text: '{movie_content} {review_summary}'")
        
        print("\n💡 ADVANTAGES:")
        print("• Captures user perspectives, not just official descriptions")
        print("• Includes emotional reactions and subjective opinions")
        print("• Helps with nuanced recommendations")
        print("• Explains WHY movies are recommended")
    
    def explain_hybrid_integration(self):
        """
        Explain how contextual model integrates with others
        """
        print("\n🔄 INTEGRATION WITH OTHER MODELS:")
        print("="*45)
        
        print("ENSEMBLE APPROACH:")
        print()
        print("1. CONTENT MODEL:")
        print("   Input: Movie metadata")
        print("   Output: Content similarity score")
        print("   Strength: Works for all movies")
        print()
        print("2. COLLABORATIVE MODEL:")
        print("   Input: User-movie interactions") 
        print("   Output: Preference-based score")
        print("   Strength: Learns user patterns")
        print()
        print("3. CONTEXTUAL MODEL:")
        print("   Input: Review text and sentiment")
        print("   Output: Context-aware score")
        print("   Strength: Understands user reasoning")
        print()
        print("FINAL PREDICTION:")
        print("Score = α×Content + β×Collaborative + γ×Contextual")
        print()
        print("ADAPTIVE WEIGHTING:")
        print("• New user: High content weight, low collaborative weight")
        print("• User with history: Balanced content + collaborative")
        print("• Movie with reviews: Add contextual component")
        print("• Movie without reviews: Zero contextual weight")
    
    def explain_training_challenges(self):
        """
        Explain the computational challenges
        """
        print("\n⚡ COMPUTATIONAL REQUIREMENTS:")
        print("="*40)
        
        print("MEMORY INTENSIVE OPERATIONS:")
        print("• Processing 18,917 reviews through BERT")
        print("• Each review → 768-dimensional embedding")
        print("• Batch processing for efficiency")
        print()
        print("ESTIMATED REQUIREMENTS:")
        print("• GPU Memory: 4-8GB (with batching)")
        print("• Training Time: 1-2 hours")
        print("• CPU Memory: 8-16GB")
        print()
        print("OPTIMIZATION STRATEGIES:")
        print("• Use DistilBERT (smaller, faster)")
        print("• Process reviews in batches")
        print("• Cache embeddings to disk")
        print("• Use gradient checkpointing")
        print()
        print("MACBOOK M2 PRO ASSESSMENT:")
        print("• Should work with careful memory management")
        print("• Might be slow without GPU acceleration")
        print("• Consider Colab for faster training")

def main():
    """
    Educational walkthrough of contextual modeling
    """
    print("🎬 CONTEXTUAL RECOMMENDATION SYSTEM")
    print("🎓 EDUCATIONAL MODE - Understanding Review-Based Recommendations")
    print("="*75)
    
    explainer = ContextualModelExplained()
    
    # Teach concepts step by step
    explainer.explain_sentiment_analysis()
    explainer.explain_aspect_extraction()
    explainer.explain_user_profiling()
    explainer.explain_contextual_embedding()
    explainer.explain_hybrid_integration()
    explainer.explain_training_challenges()
    
    print("\n🎯 KEY TAKEAWAYS:")
    print("1. Reviews provide rich preference insights")
    print("2. Sentiment analysis reveals user emotions")
    print("3. Aspect extraction identifies specific preferences")
    print("4. Contextual embeddings enhance content understanding")
    print("5. Integration with other models creates powerful hybrid system")
    print("6. Computationally intensive but manageable with right approach")
    
    print("\n🚀 NEXT: Ensemble Model Integration")
    print("Learn how to combine all three models intelligently!")

if __name__ == "__main__":
    main()

