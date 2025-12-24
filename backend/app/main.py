from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from app.scraper import search_web, scrape_url
from app.rag import RAGEngine
from app.video_processor import VideoProcessor
from app.scheduler import ContinuousLearner # Import the new scheduler
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Tunisia Tourism LLM")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_engine = RAGEngine()
video_processor = VideoProcessor()
# Initialize the learner with our RAG engine
learner = ContinuousLearner(rag_engine)

@app.on_event("startup")
async def startup_event():
    """Start the continuous learning scheduler on app startup."""
    print("\n" + "="*60)
    print("🚀 AUTOMATION: Starting Continuous Learning Scheduler...")
    print("="*60 + "\n")
    learner.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler on shutdown."""
    learner.stop()

# --- New Management Endpoints ---
@app.get("/learner/status")
def get_learner_status():
    """Check if the background learner is running and view the topic queue."""
    return {
        "is_running": learner.is_running,
        "queue_length": len(learner.topic_queue),
        "next_topics": learner.topic_queue[:5],
        "visited_topics_count": len(learner.visited_topics)
    }

@app.post("/learner/start")
def start_learner():
    learner.start()
    return {"message": "Continuous learner started."}

@app.post("/learner/stop")
def stop_learner():
    learner.stop()
    return {"message": "Continuous learner stopped."}

@app.post("/learner/add-topic")
def add_topic(topic: str):
    """Manually add a high-priority topic to the learning queue."""
    # Add to front of queue
    learner.topic_queue.insert(0, topic)
    return {"message": f"Added '{topic}' to the front of the learning queue.", "queue": learner.topic_queue}


class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]

@app.post("/ask", response_model=QueryResponse)
async def ask(request: QueryRequest):
    """Query the RAG engine with existing knowledge base (no web scraping)."""
    try:
        print(f"--- Query: {request.question} ---")
        response = rag_engine.query(request.question)
        print("--- Done ---")
        return QueryResponse(answer=response["answer"], sources=response["sources"])
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class IndexRequest(BaseModel):
    topic: str
    max_results: Optional[int] = 5

class IndexResponse(BaseModel):
    message: str
    urls_indexed: List[str]

@app.post("/index", response_model=IndexResponse)
async def index(request: IndexRequest):
    """Scrape web and populate knowledge base for a specific topic."""
    try:
        print(f"--- Indexing Topic: {request.topic} ---")
        
        # 1. Search web
        print("1. Searching web...")
        search_results = search_web(request.topic + " tourism Tunisia reviews", max_results=request.max_results)
        print(f"   Found {len(search_results)} results.")
        
        # 2. Scrape URLs
        print("2. Scraping URLs...")
        tasks = [scrape_url(r['href']) for r in search_results]
        scraped_texts = await asyncio.gather(*tasks)
        print("   Scraping complete.")
        
        # 3. Ingest into RAG
        print("3. Ingesting content...")
        indexed_urls = []
        for i, text in enumerate(scraped_texts):
            if text:
                url = search_results[i]['href']
                rag_engine.ingest(text, source=url)
                indexed_urls.append(url)
        print(f"   Indexed {len(indexed_urls)} URLs.")
        print("--- Done ---")
        
        return IndexResponse(
            message=f"Successfully indexed {len(indexed_urls)} pages for topic: {request.topic}",
            urls_indexed=indexed_urls
        )
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Tourism LLM API is running"}

class VideoAnalysisRequest(BaseModel):
    video_url: str
    prompt: Optional[str] = "Describe this video in detail."

class VideoAnalysisResponse(BaseModel):
    analysis: str

@app.post("/analyze-video", response_model=VideoAnalysisResponse)
async def analyze_video(request: VideoAnalysisRequest):
    """Downloads a video from a URL and analyzes it using Gemini."""
    try:
        print(f"--- Analyzing Video: {request.video_url} ---")
        
        # 1. Download
        print("1. Downloading video...")
        video_path = video_processor.download_video(request.video_url)
        print(f"   Downloaded to: {video_path}")
        
        # 2. Analyze
        print("2. Analyzing with Gemini...")
        analysis_result = video_processor.analyze_video(video_path, request.prompt)
        print("   Analysis complete.")
        
        # 3. Return
        return VideoAnalysisResponse(analysis=analysis_result)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class VideoBatchRequest(BaseModel):
    query: str
    count: Optional[int] = 3

class VideoBatchResponse(BaseModel):
    message: str
    videos: List[dict]

@app.post("/index-videos", response_model=VideoBatchResponse)
async def index_videos(request: VideoBatchRequest):
    """Searches YouTube, watches videos, and adds knowledge to RAG."""
    try:
        print(f"--- Indexing Videos: {request.query} ({request.count}) ---")
        
        # Call video processor batch
        # We pass the global rag_engine instance
        results = await video_processor.process_batch(request.query, request.count, rag_engine)
        
        print(f"--- Processed {len(results)} videos ---")
        
        return VideoBatchResponse(
            message=f"Successfully processed {len(results)} videos for '{request.query}'",
            videos=results
        )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
