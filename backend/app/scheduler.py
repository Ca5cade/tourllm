import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scraper import search_web, scrape_url, extract_related_topics
from app.rag import RAGEngine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContinuousLearner:
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
        self.scheduler = AsyncIOScheduler()
        self.topic_queue = [
            "hidden gems in Tunisia",
            "Tunisian street food guide",
            "historical sites in Tunisia beyond Carthage",
            "Tunisia desert camping guide",
            "scuba diving spots Tunisia"
        ]
        self.visited_topics = set()
        self.is_running = False

    def start(self):
        """Starts the background scheduler."""
        if not self.is_running:
            # Run every 4 hours (adjust as needed for quota)
            self.scheduler.add_job(self.learning_cycle, 'interval', hours=4, id='learning_job')
            self.scheduler.start()
            self.is_running = True
            logger.info("🚀 Continuous Learner Scheduler Started!")
            
            # Run one cycle immediately in the background
            asyncio.create_task(self.learning_cycle())

    def stop(self):
        """Stops the background scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Continuous Learner Scheduler Stopped.")

    async def learning_cycle(self):
        """Main loop: Pick topic -> Search -> Scrape -> Learn -> Explore New Topics."""
        if not self.topic_queue:
            logger.info("💤 No topics in queue. waiting for new manual inputs or restart.")
            return

        # 1. Pick next topic
        current_topic = self.topic_queue.pop(0)
        if current_topic in self.visited_topics:
            logger.info(f"⏭️ Skipping already visited topic: {current_topic}")
            return
        
        self.visited_topics.add(current_topic)
        logger.info(f"🧠 LEARNING CYCLE: Studying '{current_topic}'")

        try:
            # 2. Search Web
            search_results = search_web(current_topic + " tourism blog review", max_results=3)
            
            # 3. Scrape & Ingest & Extract New Topics
            new_topics_found = set()
            
            for result in search_results:
                url = result['href']
                logger.info(f"   📖 Reading: {url}")
                
                content = await scrape_url(url)
                if content:
                    # Ingest to RAG
                    self.rag_engine.ingest(content, source=url)
                    
                    # Extract new topics from this content
                    extracted = extract_related_topics(content)
                    new_topics_found.update(extracted)
            
            # 4. Update Queue
            # Filter out known topics
            unique_new_topics = [t for t in new_topics_found if t not in self.visited_topics and t not in self.topic_queue]
            
            # Add a few interesting ones to the front/back
            if unique_new_topics:
                logger.info(f"   💡 Discovered {len(unique_new_topics)} new potential topics: {unique_new_topics[:3]}...")
                self.topic_queue.extend(unique_new_topics[:5]) # consistent expansion
                
            logger.info(f"✅ Finished learning cycle for '{current_topic}'. Knowledge base updated.")

        except Exception as e:
            logger.error(f"❌ Error in learning cycle for {current_topic}: {e}")
