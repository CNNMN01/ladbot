"""
Simple database connection test
"""
import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

# Simple logging setup
logging.basicConfig(level=logging.INFO)


async def test_database():
    """Test database connection without Discord dependencies"""
    try:
        import asyncpg
        import json
        from datetime import datetime

        # Get database URL
        database_url = os.getenv('DATABASE_URL')

        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            print("💡 Make sure you have a .env file or set DATABASE_URL")
            return False

        print(f"🔗 Connecting to database...")
        print(f"🔗 URL starts with: {database_url[:20]}...")

        # Test connection
        pool = await asyncpg.create_pool(
            database_url,
            min_size=1,
            max_size=2,
            command_timeout=30
        )

        print("✅ Connection pool created successfully!")

        # Test table creation
        create_sql = """
                     CREATE TABLE IF NOT EXISTS guild_settings \
                     ( \
                         guild_id \
                         BIGINT \
                         PRIMARY \
                         KEY, \
                         settings \
                         JSONB \
                         NOT \
                         NULL \
                         DEFAULT \
                         '{}', \
                         created_at \
                         TIMESTAMP \
                         DEFAULT \
                         CURRENT_TIMESTAMP, \
                         updated_at \
                         TIMESTAMP \
                         DEFAULT \
                         CURRENT_TIMESTAMP
                     ); \
                     """

        async with pool.acquire() as conn:
            await conn.execute(create_sql)
            print("✅ Table created/verified successfully!")

            # Test insert/select
            test_guild_id = 123456789
            test_settings = {"test": True, "created": datetime.now().isoformat()}

            await conn.execute("""
                               INSERT INTO guild_settings (guild_id, settings)
                               VALUES ($1, $2) ON CONFLICT (guild_id) 
                DO
                               UPDATE SET settings = $2
                               """, test_guild_id, json.dumps(test_settings))

            # Test retrieval
            row = await conn.fetchrow(
                "SELECT settings FROM guild_settings WHERE guild_id = $1",
                test_guild_id
            )

            if row:
                retrieved_settings = dict(row['settings'])
                print(f"✅ Data test successful! Retrieved: {retrieved_settings.get('test')}")
            else:
                print("❌ Data retrieval failed")
                return False

        await pool.close()
        print("✅ Database test completed successfully!")
        return True

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install asyncpg")
        return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print(f"💡 Check your DATABASE_URL and network connection")
        return False


if __name__ == "__main__":
    # Load environment variables if .env exists
    env_file = Path(".env")
    if env_file.exists():
        print("📄 Loading .env file...")
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    # Run the test
    success = asyncio.run(test_database())
    if success:
        print("\n🎉 All database tests passed! Ready for Phase 2.")
    else:
        print("\n💥 Database test failed. Please fix issues before continuing.")