#!/usr/bin/env python3
"""
Standalone worker process for processing generation jobs.
Run this separately from the API server to process background jobs.

Usage:
    python3 run_worker.py
"""

import time
import signal
import sys
from datetime import datetime, timezone
from app.db.database import SessionLocal
from app.models.job import Job, JobStatus
from app.workers.graph_worker import run_generation_job
from app.core.logging import logger

# Global flag for graceful shutdown
shutdown_requested = False

def signal_handler(sig, frame):
    global shutdown_requested
    logger.info("\n🛑 Shutdown signal received. Finishing current job and exiting...")
    shutdown_requested = True

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def process_pending_jobs():
    """Find and process all pending jobs"""
    db = SessionLocal()
    try:
        # Find all pending jobs
        pending_jobs = db.query(Job).filter(
            Job.status == JobStatus.PENDING
        ).order_by(Job.created_at).all()
        
        if pending_jobs:
            logger.info(f"Found {len(pending_jobs)} pending jobs")
            for job in pending_jobs:
                if shutdown_requested:
                    logger.info("Shutdown requested, stopping job processing")
                    break
                    
                logger.info(f"Processing job {job.id}...")
                run_generation_job(job.id)
        
        return len(pending_jobs)
    finally:
        db.close()

def main():
    logger.info("=" * 80)
    logger.info("🚀 SYNTHETIC DATA GENERATOR WORKER")
    logger.info("=" * 80)
    logger.info("Worker started. Polling for jobs every 5 seconds...")
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("=" * 80)
    
    poll_interval = 5  # seconds
    
    while not shutdown_requested:
        try:
            jobs_processed = process_pending_jobs()
            
            if jobs_processed == 0:
                # No jobs found, wait before next poll
                time.sleep(poll_interval)
            else:
                # Jobs were found, check again immediately
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}", exc_info=True)
            time.sleep(poll_interval)
    
    logger.info("=" * 80)
    logger.info("✓ Worker stopped gracefully")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
