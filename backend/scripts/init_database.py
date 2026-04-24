#!/usr/bin/env python3
"""
Database initialization script for Freelance Lead Scraper.

This script creates the database schema, tables, and indexes required
for the lead scraper system. It can be run multiple times safely as it
uses IF NOT EXISTS clauses.

Usage:
    python scripts/init_database.py --config config.json
    python scripts/init_database.py --database-url postgresql://user:pass@localhost/db
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import lead_scraper modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2 import sql
from lead_scraper.models.system_config import SystemConfig


def load_schema_sql() -> str:
    """Load the schema SQL file.
    
    Returns:
        SQL schema as string
    """
    schema_path = Path(__file__).parent.parent / "lead_scraper" / "database" / "schema.sql"
    
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    with open(schema_path, 'r') as f:
        return f.read()


def init_database(database_url: str) -> None:
    """Initialize the database with schema and indexes.
    
    Args:
        database_url: PostgreSQL connection string
    
    Raises:
        psycopg2.Error: If database connection or execution fails
    """
    print(f"Connecting to database...")
    
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Loading schema SQL...")
        schema_sql = load_schema_sql()
        
        print("Executing schema creation...")
        cursor.execute(schema_sql)
        
        print("✓ Database schema initialized successfully")
        print("✓ Tables created")
        print("✓ Indexes created")
        print("✓ Extensions enabled (pg_trgm)")
        
        # Verify table creation
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'leads'
        """)
        
        if cursor.fetchone():
            print("✓ Verified: 'leads' table exists")
        else:
            print("⚠ Warning: 'leads' table not found after creation")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for database initialization script."""
    parser = argparse.ArgumentParser(
        description="Initialize Freelance Lead Scraper database"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (config.json)"
    )
    group.add_argument(
        "--database-url",
        type=str,
        help="PostgreSQL connection string (postgresql://user:pass@host:port/db)"
    )
    
    args = parser.parse_args()
    
    # Get database URL from config or command line
    if args.config:
        try:
            config = SystemConfig.from_file(args.config)
            database_url = config.database_url
            print(f"Loaded configuration from: {args.config}")
        except Exception as e:
            print(f"✗ Failed to load config: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        database_url = args.database_url
    
    print(f"Database URL: {database_url.split('@')[1] if '@' in database_url else database_url}")
    print()
    
    init_database(database_url)
    
    print()
    print("Database initialization complete!")
    print("You can now start the FastMCP server.")


if __name__ == "__main__":
    main()
