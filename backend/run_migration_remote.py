#!/usr/bin/env python3
"""
Remote Database Migration Runner
Connects to Railway PostgreSQL and runs the progress_percent migration
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Run the add_progress_column migration on Railway database"""
    
    # Get DATABASE_URL from environment or prompt user
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("=" * 70)
        print("DATABASE_URL not found in .env file")
        print("=" * 70)
        print("\nPlease get your Railway PostgreSQL connection string:")
        print("1. Go to https://railway.app")
        print("2. Select your project")
        print("3. Click on PostgreSQL database")
        print("4. Click 'Variables' tab")
        print("5. Copy the DATABASE_URL value")
        print("\nPaste it here (it will be hidden):")
        database_url = input().strip()
    
    if not database_url or not database_url.startswith("postgresql://"):
        print("❌ Invalid DATABASE_URL. Must start with postgresql://")
        sys.exit(1)
    
    # Hide password in output
    safe_url = database_url.split("@")[1] if "@" in database_url else database_url
    print(f"\n📊 Connecting to database: ...@{safe_url}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✓ Connected successfully!")
        
        # Check if column already exists
        print("\n🔍 Checking if progress_percent column exists...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'progress_percent';
        """)
        
        if cursor.fetchone():
            print("✓ Column 'progress_percent' already exists! No migration needed.")
            cursor.close()
            conn.close()
            return
        
        print("⚠️  Column 'progress_percent' NOT found. Running migration...")
        
        # Run migration
        migration_sql = """
        -- Add progress_percent column
        ALTER TABLE jobs ADD COLUMN progress_percent INTEGER DEFAULT 0;
        
        -- Update existing jobs
        UPDATE jobs SET progress_percent = 0 WHERE progress_percent IS NULL;
        """
        
        cursor.execute(migration_sql)
        print("✓ Migration executed successfully!")
        
        # Verify
        print("\n🔍 Verifying column was created...")
        cursor.execute("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'jobs' AND column_name = 'progress_percent';
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"✓ Verified! Column: {result[0]}, Type: {result[1]}, Default: {result[2]}")
        else:
            print("❌ Verification failed - column not found after migration")
            sys.exit(1)
        
        # Show sample data
        print("\n📊 Sample jobs with progress_percent:")
        cursor.execute("""
            SELECT id, status, current_step, progress_percent 
            FROM jobs 
            ORDER BY created_at DESC 
            LIMIT 5;
        """)
        
        jobs = cursor.fetchall()
        if jobs:
            print("\nID | Status    | Current Step           | Progress")
            print("-" * 60)
            for job in jobs:
                print(f"{job[0]:3d} | {job[1]:9s} | {str(job[2])[:20]:20s} | {job[3] or 0}%")
        else:
            print("No jobs found in database")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\n📝 Next steps:")
        print("1. Your backend should auto-redeploy from GitHub")
        print("2. Wait 1-2 minutes for deployment to complete")
        print("3. Try generating a dataset again")
        print("4. It should work now! 🎉")
        
    except psycopg2.Error as e:
        print(f"\n❌ Database Error: {e}")
        print("\nCommon issues:")
        print("- Wrong DATABASE_URL")
        print("- Database is not accessible")
        print("- Connection refused (check Railway status)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 SynthGen Database Migration Runner")
    print("=" * 70)
    print("\nThis script will add the 'progress_percent' column to your Railway database.")
    print("This is safe and will not affect existing data.\n")
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Migration cancelled.")
        sys.exit(0)
    
    print("\nStarting migration...\n")
    run_migration()
