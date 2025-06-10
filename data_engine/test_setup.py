"""
Test script for CineAI Data Engine setup

This script verifies that all components are properly configured and can connect to TMDB API.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from data_engine.config import TMDB_CONFIG, DATA_CONFIG, BASE_DIR, DATA_DIR
from data_engine.tmdb_client import TMDBClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_tmdb_connection():
    """Test TMDB API connection."""
    logger.info("Testing TMDB API connection...")
    
    if not TMDB_CONFIG["api_key"]:
        logger.error("❌ TMDB API key is not set!")
        logger.info("Please set your TMDB API key:")
        logger.info("export TMDB_API_KEY='your_api_key_here'")
        return False
    
    try:
        async with TMDBClient() as client:
            # Test a simple API call
            logger.info("Making test API call...")
            popular_movies = await client.get_popular_movies(page=1)
            
            if popular_movies:
                logger.info(f"✅ Successfully fetched {len(popular_movies)} popular movies")
                logger.info(f"   Sample movie: {popular_movies[0].title}")
                return True
            else:
                logger.error("❌ No movies returned from API")
                return False
                
    except Exception as e:
        logger.error(f"❌ TMDB API connection failed: {e}")
        return False


def test_directory_structure():
    """Test that required directories exist."""
    logger.info("Testing directory structure...")
    
    required_dirs = [
        DATA_DIR,
        DATA_DIR / "raw",
        DATA_DIR / "processed",
        BASE_DIR / "cache",
        BASE_DIR / "logs"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if dir_path.exists():
            logger.info(f"✅ {dir_path} exists")
        else:
            logger.warning(f"⚠️  {dir_path} does not exist, creating...")
            dir_path.mkdir(parents=True, exist_ok=True)
            all_exist = False
    
    return all_exist


def test_configuration():
    """Test configuration settings."""
    logger.info("Testing configuration...")
    
    # Test TMDB config
    required_tmdb_fields = ["api_key", "base_url", "timeout", "max_retries"]
    for field in required_tmdb_fields:
        if field in TMDB_CONFIG:
            logger.info(f"✅ TMDB config: {field} is set")
        else:
            logger.error(f"❌ TMDB config: {field} is missing")
            return False
    
    # Test data config
    required_data_fields = ["batch_size", "max_workers", "chunk_size"]
    for field in required_data_fields:
        if field in DATA_CONFIG:
            logger.info(f"✅ Data config: {field} is set")
        else:
            logger.error(f"❌ Data config: {field} is missing")
            return False
    
    return True


async def main():
    """Run all tests."""
    logger.info("🧪 Running CineAI Data Engine Setup Tests")
    logger.info("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Configuration
    logger.info("\n1. Testing Configuration...")
    if test_configuration():
        tests_passed += 1
        logger.info("✅ Configuration test passed")
    else:
        logger.error("❌ Configuration test failed")
    
    # Test 2: Directory Structure
    logger.info("\n2. Testing Directory Structure...")
    if test_directory_structure():
        tests_passed += 1
        logger.info("✅ Directory structure test passed")
    else:
        logger.info("⚠️  Directory structure test had warnings (directories created)")
        tests_passed += 1  # Count as passed since we created missing dirs
    
    # Test 3: TMDB Connection
    logger.info("\n3. Testing TMDB API Connection...")
    if await test_tmdb_connection():
        tests_passed += 1
        logger.info("✅ TMDB connection test passed")
    else:
        logger.error("❌ TMDB connection test failed")
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        logger.info("🎉 All tests passed! Your data engine is ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Run data extraction: python data_engine/extract_data.py")
        logger.info("2. Run ETL pipeline: python data_engine/etl_pipeline.py")
    else:
        logger.error("❌ Some tests failed. Please fix the issues above.")
        logger.info("\nCommon fixes:")
        logger.info("1. Set TMDB API key: export TMDB_API_KEY='your_key'")
        logger.info("2. Install missing packages: pip install pandas tqdm aiohttp")
        logger.info("3. Check your internet connection")
    
    return tests_passed == total_tests


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 