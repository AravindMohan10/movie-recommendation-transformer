import torch
import torch.nn as nn
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import time
import threading
from pathlib import Path

# Optional imports - these may not be available in all environments
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("Warning: 'schedule' module not available. Scheduled retraining disabled.")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: 'redis' module not available. Redis caching disabled.")

logger = logging.getLogger(__name__)

class ModelRetrainingService:
    def __init__(self):
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
        self.model_path = "../Checkpoints/best_performer_mf_regularized.pt"
        self.backup_path = "../Checkpoints/model_backup.pt"
        self.retraining_interval_hours = 168  # 1 week
        self.min_interactions_for_retraining = 100
        
    def start_scheduled_retraining(self):
        """Start the scheduled retraining service"""
        if not SCHEDULE_AVAILABLE:
            logger.info("Scheduled retraining disabled - 'schedule' module not available")
            return
        
        # Schedule retraining every week
        schedule.every(self.retraining_interval_hours).hours.do(self.retrain_model_if_needed)
        
        # Run the scheduler in a separate thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(3600)  # Check every hour
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Model retraining scheduler started")
    
    def retrain_model_if_needed(self):
        """Check if retraining is needed and perform it"""
        try:
            # Check if we have enough new interactions
            total_interactions = self._get_total_user_interactions()
            
            if total_interactions < self.min_interactions_for_retraining:
                logger.info(f"Not enough interactions for retraining: {total_interactions}/{self.min_interactions_for_retraining}")
                return
            
            # Check if enough time has passed since last retraining
            last_retraining = self._get_last_retraining_time()
            if last_retraining and datetime.now() - last_retraining < timedelta(hours=self.retraining_interval_hours):
                logger.info("Not enough time has passed since last retraining")
                return
            
            logger.info("Starting model retraining...")
            self._perform_retraining()
            
        except Exception as e:
            logger.error(f"Error in retraining check: {e}")
    
    def _get_total_user_interactions(self) -> int:
        """Get total number of user interactions since last retraining"""
        try:
            # Get all user interaction keys
            pattern = "user_interaction:*"
            keys = self.redis_client.keys(pattern)
            
            # Filter interactions since last retraining
            last_retraining = self._get_last_retraining_time()
            if last_retraining:
                recent_interactions = 0
                for key in keys:
                    data = self.redis_client.get(key)
                    if data:
                        interaction = json.loads(data)
                        interaction_time = datetime.fromisoformat(interaction["timestamp"])
                        if interaction_time > last_retraining:
                            recent_interactions += 1
                return recent_interactions
            
            return len(keys)
            
        except Exception as e:
            logger.error(f"Error getting total interactions: {e}")
            return 0
    
    def _get_last_retraining_time(self) -> datetime:
        """Get the timestamp of the last model retraining"""
        if not self.redis_client:
            return None
        try:
            last_retraining = self.redis_client.get("last_model_retraining")
            if last_retraining:
                return datetime.fromisoformat(last_retraining)
            return None
        except Exception as e:
            logger.error(f"Error getting last retraining time: {e}")
            return None
    
    def _perform_retraining(self):
        """Perform the actual model retraining"""
        try:
            # Backup current model
            self._backup_current_model()
            
            # Collect new training data
            new_training_data = self._collect_new_training_data()
            
            if not new_training_data:
                logger.info("No new training data available")
                return
            
            # Retrain the model
            self._retrain_model(new_training_data)
            
            # Update retraining timestamp
            if self.redis_client:
                self.redis_client.set("last_model_retraining", datetime.now().isoformat())
            
            # Clear old interaction data (keep last 30 days)
            self._cleanup_old_interactions()
            
            logger.info("Model retraining completed successfully")
            
        except Exception as e:
            logger.error(f"Error during retraining: {e}")
            # Restore backup if retraining failed
            self._restore_backup()
    
    def _backup_current_model(self):
        """Create a backup of the current model"""
        try:
            import shutil
            shutil.copy2(self.model_path, self.backup_path)
            logger.info("Model backup created")
        except Exception as e:
            logger.error(f"Error creating model backup: {e}")
    
    def _restore_backup(self):
        """Restore model from backup"""
        try:
            import shutil
            if Path(self.backup_path).exists():
                shutil.copy2(self.backup_path, self.model_path)
                logger.info("Model restored from backup")
        except Exception as e:
            logger.error(f"Error restoring model backup: {e}")
    
    def _collect_new_training_data(self) -> List[Dict]:
        """Collect new training data from user interactions"""
        try:
            new_training_data = []
            pattern = "user_interaction:*"
            keys = self.redis_client.keys(pattern)
            
            last_retraining = self._get_last_retraining_time()
            
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    interaction = json.loads(data)
                    interaction_time = datetime.fromisoformat(interaction["timestamp"])
                    
                    # Only include interactions since last retraining
                    if not last_retraining or interaction_time > last_retraining:
                        # Parse user_id and movie_id from key
                        parts = key.split(":")
                        if len(parts) >= 3:
                            user_id = int(parts[1])
                            movie_id = int(parts[2])
                            
                            training_sample = {
                                "user_id": user_id,
                                "movie_id": movie_id,
                                "rating": interaction["rating"],
                                "action": interaction["action"],
                                "timestamp": interaction["timestamp"]
                            }
                            new_training_data.append(training_sample)
            
            return new_training_data
            
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return []
    
    def _retrain_model(self, new_training_data: List[Dict]):
        """Retrain the model with new data"""
        try:
            # Load current model
            checkpoint = torch.load(self.model_path, map_location='cpu')
            model = checkpoint['model'] if 'model' in checkpoint else checkpoint
            
            # Convert new data to tensors
            user_ids = torch.tensor([sample["user_id"] for sample in new_training_data])
            movie_ids = torch.tensor([sample["movie_id"] for sample in new_training_data])
            ratings = torch.tensor([sample["rating"] for sample in new_training_data])
            
            # Fine-tune the model
            model.train()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            # Training loop
            num_epochs = 5
            batch_size = 32
            
            for epoch in range(num_epochs):
                total_loss = 0
                num_batches = 0
                
                for i in range(0, len(new_training_data), batch_size):
                    batch_user_ids = user_ids[i:i+batch_size]
                    batch_movie_ids = movie_ids[i:i+batch_size]
                    batch_ratings = ratings[i:i+batch_size]
                    
                    optimizer.zero_grad()
                    
                    # Forward pass
                    predictions = model(batch_user_ids, batch_movie_ids)
                    loss = criterion(predictions, batch_ratings)
                    
                    # Backward pass
                    loss.backward()
                    optimizer.step()
                    
                    total_loss += loss.item()
                    num_batches += 1
                
                avg_loss = total_loss / num_batches
                logger.info(f"Epoch {epoch+1}/{num_epochs}, Average Loss: {avg_loss:.4f}")
            
            # Save retrained model
            model.eval()
            torch.save({
                'model': model,
                'retrained_at': datetime.now().isoformat(),
                'training_samples': len(new_training_data)
            }, self.model_path)
            
            logger.info(f"Model retrained with {len(new_training_data)} new samples")
            
        except Exception as e:
            logger.error(f"Error during model retraining: {e}")
            raise
    
    def _cleanup_old_interactions(self):
        """Clean up old interaction data (keep last 30 days)"""
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            pattern = "user_interaction:*"
            keys = self.redis_client.keys(pattern)
            
            deleted_count = 0
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    interaction = json.loads(data)
                    interaction_time = datetime.fromisoformat(interaction["timestamp"])
                    
                    if interaction_time < cutoff_date:
                        self.redis_client.delete(key)
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old interactions")
            
        except Exception as e:
            logger.error(f"Error cleaning up old interactions: {e}")
    
    def force_retraining(self):
        """Force immediate model retraining"""
        logger.info("Forcing immediate model retraining...")
        self._perform_retraining()

# Global retraining service instance
retraining_service = ModelRetrainingService() 