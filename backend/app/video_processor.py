import os
import time
import glob
import logging
from typing import Optional
import yt_dlp
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
# Ensure you have GOOGLE_API_KEY in your .env
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("GOOGLE_API_KEY not found in environment variables.")

class VideoProcessor:
    def __init__(self, download_dir: str = "temp_videos"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def download_video(self, url: str) -> str:
        """
        Downloads a video from a URL using yt-dlp.
        Returns the absolute path to the downloaded file.
        """
        logger.info(f"Downloading video from: {url}")
        
        # Clean up old files in temp dir to save space
        self._cleanup_temp_dir()

        ydl_opts = {
            'format': 'best[ext=mp4]',  # Prefer mp4 for compatibility
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'overwrites': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            # yt-dlp might change the filename (sanitization), so we get the filename from info
            filename = ydl.prepare_filename(info_dict)
            
            # Absolute path
            abs_path = os.path.abspath(filename)
            logger.info(f"Video downloaded to: {abs_path}")
            return abs_path

    def upload_to_gemini(self, file_path: str):
        """Uploads the file to Gemini File API."""
        logger.info(f"Uploading file to Gemini: {file_path}")
        video_file = genai.upload_file(path=file_path)
        logger.info(f"Uploaded file: {video_file.name}")
        return video_file

    def wait_for_processing(self, video_file):
        """Waits for the video to be processed by Gemini."""
        logger.info("Waiting for video processing...")
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            raise ValueError("Video processing failed.")
        
        logger.info("Video processing complete.")
        return video_file

    def analyze_video(self, video_path: str, user_prompt: Optional[str] = None) -> str:
        """
        Orchestrates the full analysis flow: Upload -> Wait -> Generate Content.
        """
        try:
            # Upload
            video_file = self.upload_to_gemini(video_path)
            
            # Wait for processing
            video_file = self.wait_for_processing(video_file)
            
            # Try to report available models if possible (for debugging)
            # models = genai.list_models()
            # for m in models:
            #     if 'generateContent' in m.supported_generation_methods:
            #         print(m.name)

            # Construct prompt
            base_prompt = "Watch this video and describe it in detail."
            final_prompt = [video_file, user_prompt if user_prompt else base_prompt]

            # List of models to try in order of preference (Flash for speed, Pro for quality)
            # The user appears to have access to 2.x and preview models, but not 1.5.
            candidate_models = [
                "gemini-2.0-flash",
                "gemini-2.0-flash-exp",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash-001",
                "gemini-2.0-flash-lite",
                "gemini-1.5-flash", # keeping as fallback
                "gemini-1.5-pro",
            ]

            model = None
            last_exception = None

            for model_name in candidate_models:
                try:
                    logger.info(f"Attempting to use model: {model_name}")
                    model = genai.GenerativeModel(model_name=model_name)
                    # Simple test generation to check if model exists/is accessible
                    # Note: We can't easily "test" without sending data, but init is usually safe.
                    # However, the error comes at generate_content time. 
                    # So we will try to generate content with the first one that works.
                    
                    response = model.generate_content(final_prompt)
                    return response.text
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    last_exception = e
                    # If it's a 404 or specific API error, we continue.
                    # If it interprets as "video not processed yet", we might need to wait more? 
                    # But the error reported was "404 models/... not found".
                    continue
            
            # If we reach here, all failed
            raise last_exception or ValueError("No suitable Gemini model found.")
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            raise e

    async def process_batch(self, query: str, count: int, rag_engine):
        """
        Searches for videos, downloads them, analyzes them, and ingests into RAG.
        Returns a summary list of processed videos.
        """
        processed_videos = []
        
        try:
            # 1. Search and Download
            search_query = f"ytsearch{count}:{query}"
            logger.info(f"Searching and downloading: {search_query}")
            
            # Use a separate directory for each batch or cleanup heavily
            # For simplicity, we use the shared temp dir but ensure clean filenames
            
            self._cleanup_temp_dir()

            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
                # 'max_downloads': count, # ytsearchN limits it already
            }

            downloaded_files = []

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # This might download all entries in the search result
                result = ydl.extract_info(search_query, download=True)
                
                if 'entries' in result:
                    for entry in result['entries']:
                        if entry:
                            filename = ydl.prepare_filename(entry)
                            abs_path = os.path.abspath(filename)
                            title = entry.get('title', 'Unknown Video')
                            url = entry.get('webpage_url', 'Unknown URL')
                            downloaded_files.append({"path": abs_path, "title": title, "url": url})
                else:
                    # Single video result (unlikely for ytsearch but possible)
                    filename = ydl.prepare_filename(result)
                    abs_path = os.path.abspath(filename)
                    title = result.get('title', 'Unknown Video')
                    url = result.get('webpage_url', 'Unknown URL')
                    downloaded_files.append({"path": abs_path, "title": title, "url": url})

            logger.info(f"Downloaded {len(downloaded_files)} videos.")

            # 2. Analyze and Ingest
            for video_info in downloaded_files:
                path = video_info["path"]
                title = video_info["title"]
                url = video_info["url"]
                
                if not os.path.exists(path):
                    logger.warning(f"File not found: {path}")
                    continue
                
                try:
                    logger.info(f"Analyzing: {title}")
                    # Analyze
                    analysis = self.analyze_video(path, user_prompt=f"Analyze this video about '{query}'. Provide a comprehensive summary of the key information presented.")
                    
                    # Ingest
                    logger.info(f"Ingesting into RAG: {title}")
                    rag_text = f"Video Title: {title}\nVideo URL: {url}\n\nAnalysis:\n{analysis}"
                    rag_engine.ingest(rag_text, source=url)
                    
                    processed_videos.append({"title": title, "url": url, "status": "Indexed"})
                    
                except Exception as e:
                    logger.error(f"Failed to process {title}: {e}")
                    processed_videos.append({"title": title, "url": url, "status": f"Failed: {str(e)}"})
            
            return processed_videos

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            raise e
        finally:
            self._cleanup_temp_dir()

    def _cleanup_temp_dir(self):
        """Removes all files in the temporary directory."""
        if os.path.exists(self.download_dir):
            files = glob.glob(os.path.join(self.download_dir, '*'))
            for f in files:
                try:
                    os.remove(f)
                except Exception as e:
                    logger.warning(f"Failed to delete {f}: {e}")
