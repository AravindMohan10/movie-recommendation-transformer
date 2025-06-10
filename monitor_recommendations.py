#!/usr/bin/env python3
"""
Production monitoring script for recommendation quality.
Tracks CTR, user ratings, engagement metrics, and model performance.
"""
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationMonitor:
    """
    Monitor recommendation quality in production.
    Tracks metrics like CTR, ratings, engagement, etc.
    """
    
    def __init__(self, db_path: str = "cineai.db"):
        """Initialize monitor with database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_monitoring_tables()
    
    def _create_monitoring_tables(self):
        """Create monitoring tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # Recommendation events (impressions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                recommendation_id TEXT,
                position INTEGER,
                shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User interactions (clicks, ratings)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                movie_id INTEGER NOT NULL,
                interaction_type TEXT,  -- 'click', 'rating', 'watch', 'dismiss'
                rating REAL,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # Model performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_type TEXT,  -- 'precision', 'recall', 'ctr', 'engagement'
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
        logger.info("Monitoring tables created/verified")
    
    def record_recommendation_shown(self, user_id: int, movie_id: int, 
                                    recommendation_id: str, position: int):
        """Record that a recommendation was shown to a user."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO recommendation_events 
            (user_id, movie_id, recommendation_id, position)
            VALUES (?, ?, ?, ?)
        """, (user_id, movie_id, recommendation_id, position))
        self.conn.commit()
    
    def record_interaction(self, user_id: int, movie_id: int, 
                          interaction_type: str, rating: float = None):
        """Record user interaction with a recommendation."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO recommendation_interactions 
            (user_id, movie_id, interaction_type, rating)
            VALUES (?, ?, ?, ?)
        """, (user_id, movie_id, interaction_type, rating))
        self.conn.commit()
    
    def calculate_ctr(self, days: int = 7) -> Dict[str, float]:
        """Calculate Click-Through Rate for the last N days."""
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Total recommendations shown
        cursor.execute("""
            SELECT COUNT(*) FROM recommendation_events
            WHERE shown_at >= ?
        """, (cutoff_date,))
        total_shown = cursor.fetchone()[0]
        
        # Total clicks
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id || '-' || movie_id) 
            FROM recommendation_interactions
            WHERE interaction_type = 'click' AND clicked_at >= ?
        """, (cutoff_date,))
        total_clicks = cursor.fetchone()[0]
        
        # CTR by position
        cursor.execute("""
            SELECT 
                e.position,
                COUNT(DISTINCT e.id) as shown,
                COUNT(DISTINCT i.id) as clicked
            FROM recommendation_events e
            LEFT JOIN recommendation_interactions i 
                ON e.user_id = i.user_id 
                AND e.movie_id = i.movie_id
                AND i.interaction_type = 'click'
                AND i.clicked_at >= e.shown_at
            WHERE e.shown_at >= ?
            GROUP BY e.position
            ORDER BY e.position
        """, (cutoff_date,))
        
        position_ctr = {}
        for row in cursor.fetchall():
            position, shown, clicked = row
            if shown > 0:
                position_ctr[f'position_{position}'] = clicked / shown
        
        overall_ctr = total_clicks / total_shown if total_shown > 0 else 0.0
        
        return {
            'overall_ctr': overall_ctr,
            'total_shown': total_shown,
            'total_clicks': total_clicks,
            'position_ctr': position_ctr
        }
    
    def calculate_average_rating(self, days: int = 7) -> Dict[str, float]:
        """Calculate average rating of recommended movies."""
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT AVG(rating), COUNT(*)
            FROM recommendation_interactions
            WHERE interaction_type = 'rating' 
            AND rating IS NOT NULL
            AND clicked_at >= ?
        """, (cutoff_date,))
        
        result = cursor.fetchone()
        avg_rating = result[0] if result[0] else 0.0
        count = result[1] if result[1] else 0
        
        return {
            'average_rating': avg_rating,
            'rating_count': count
        }
    
    def calculate_engagement_metrics(self, days: int = 7) -> Dict[str, float]:
        """Calculate engagement metrics."""
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Users who received recommendations
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM recommendation_events
            WHERE shown_at >= ?
        """, (cutoff_date,))
        unique_users = cursor.fetchone()[0]
        
        # Interactions per user
        cursor.execute("""
            SELECT 
                user_id,
                COUNT(*) as interaction_count
            FROM recommendation_interactions
            WHERE clicked_at >= ?
            GROUP BY user_id
        """, (cutoff_date,))
        
        interactions_per_user = [row[1] for row in cursor.fetchall()]
        avg_interactions = (sum(interactions_per_user) / len(interactions_per_user) 
                          if interactions_per_user else 0.0)
        
        # Engagement rate (% of users who interacted)
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM recommendation_interactions
            WHERE clicked_at >= ?
        """, (cutoff_date,))
        engaged_users = cursor.fetchone()[0]
        
        engagement_rate = engaged_users / unique_users if unique_users > 0 else 0.0
        
        return {
            'unique_users': unique_users,
            'engaged_users': engaged_users,
            'engagement_rate': engagement_rate,
            'avg_interactions_per_user': avg_interactions
        }
    
    def get_recommendation_diversity(self, days: int = 7) -> Dict[str, float]:
        """Calculate recommendation diversity."""
        cursor = self.conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Total unique movies recommended
        cursor.execute("""
            SELECT COUNT(DISTINCT movie_id)
            FROM recommendation_events
            WHERE shown_at >= ?
        """, (cutoff_date,))
        unique_movies_recommended = cursor.fetchone()[0]
        
        # Most recommended movies
        cursor.execute("""
            SELECT movie_id, COUNT(*) as count
            FROM recommendation_events
            WHERE shown_at >= ?
            GROUP BY movie_id
            ORDER BY count DESC
            LIMIT 10
        """, (cutoff_date,))
        
        top_movies = cursor.fetchall()
        
        # Concentration (Gini coefficient approximation)
        cursor.execute("""
            SELECT COUNT(*) as recommendation_count
            FROM recommendation_events
            WHERE shown_at >= ?
            GROUP BY movie_id
        """, (cutoff_date,))
        
        counts = [row[0] for row in cursor.fetchall()]
        if counts:
            sorted_counts = sorted(counts)
            n = len(sorted_counts)
            gini = (2 * sum((i + 1) * count for i, count in enumerate(sorted_counts))) / (
                n * sum(sorted_counts)
            ) - (n + 1) / n
        else:
            gini = 0.0
        
        return {
            'unique_movies_recommended': unique_movies_recommended,
            'top_recommended_movies': top_movies[:5],
            'concentration_index': gini  # Higher = less diverse
        }
    
    def generate_report(self, days: int = 7) -> Dict:
        """Generate comprehensive monitoring report."""
        print(f"\n{'=' * 70}")
        print(f"📊 Recommendation Quality Report (Last {days} Days)")
        print(f"{'=' * 70}\n")
        
        # CTR
        ctr_metrics = self.calculate_ctr(days)
        print("🎯 Click-Through Rate (CTR):")
        print(f"   Overall CTR: {ctr_metrics['overall_ctr']:.2%}")
        print(f"   Total Shown: {ctr_metrics['total_shown']:,}")
        print(f"   Total Clicks: {ctr_metrics['total_clicks']:,}")
        if ctr_metrics['position_ctr']:
            print("   CTR by Position:")
            for pos, ctr in ctr_metrics['position_ctr'].items():
                print(f"      {pos}: {ctr:.2%}")
        
        # Ratings
        rating_metrics = self.calculate_average_rating(days)
        print(f"\n⭐ Average Rating:")
        print(f"   Average: {rating_metrics['average_rating']:.2f}/10")
        print(f"   Total Ratings: {rating_metrics['rating_count']:,}")
        
        # Engagement
        engagement = self.calculate_engagement_metrics(days)
        print(f"\n👥 Engagement:")
        print(f"   Unique Users: {engagement['unique_users']:,}")
        print(f"   Engaged Users: {engagement['engaged_users']:,}")
        print(f"   Engagement Rate: {engagement['engagement_rate']:.2%}")
        print(f"   Avg Interactions/User: {engagement['avg_interactions_per_user']:.2f}")
        
        # Diversity
        diversity = self.get_recommendation_diversity(days)
        print(f"\n🌈 Diversity:")
        print(f"   Unique Movies Recommended: {diversity['unique_movies_recommended']:,}")
        print(f"   Concentration Index: {diversity['concentration_index']:.3f}")
        print("   (Lower = more diverse)")
        
        # Compile report
        report = {
            'period_days': days,
            'generated_at': datetime.now().isoformat(),
            'ctr': ctr_metrics,
            'ratings': rating_metrics,
            'engagement': engagement,
            'diversity': diversity
        }
        
        print(f"\n{'=' * 70}\n")
        
        return report
    
    def save_metrics(self, metrics: Dict):
        """Save computed metrics to database for historical tracking."""
        cursor = self.conn.cursor()
        
        for metric_name, value in metrics.items():
            if isinstance(value, dict):
                # Flatten nested dicts
                for sub_name, sub_value in value.items():
                    if isinstance(sub_value, (int, float)):
                        cursor.execute("""
                            INSERT INTO model_metrics (metric_name, metric_value, metric_type)
                            VALUES (?, ?, ?)
                        """, (f"{metric_name}.{sub_name}", sub_value, metric_name))
            elif isinstance(value, (int, float)):
                cursor.execute("""
                    INSERT INTO model_metrics (metric_name, metric_value, metric_type)
                    VALUES (?, ?, ?)
                """, (metric_name, value, 'general'))
        
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main monitoring function."""
    monitor = RecommendationMonitor()
    
    try:
        # Generate report
        report = monitor.generate_report(days=7)
        
        # Save metrics
        monitor.save_metrics({
            'ctr': report['ctr']['overall_ctr'],
            'avg_rating': report['ratings']['average_rating'],
            'engagement_rate': report['engagement']['engagement_rate']
        })
        
        # Save full report
        report_path = project_root / "monitoring_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"💾 Report saved to: {report_path}\n")
        
    finally:
        monitor.close()


if __name__ == "__main__":
    main()

