import uuid
import time
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any

# MongoDB driver
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    print("[WARN] pymongo not installed. MongoDB logging disabled.")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

MONGO_URI = "mongodb://localhost:27017"
MONGO_DATABASE = "ai_shell_logs"
MONGO_COLLECTION_INTERACTIONS = "interactions"  # Main logging collection
MONGO_COLLECTION_SESSIONS = "sessions"          # Session metadata
MONGO_TIMEOUT_MS = 3000  # Connection timeout (3 seconds)


# ==============================================================================
# GLOBAL STATE
# ==============================================================================

# MongoDB client (initialized once at startup)
_mongo_client: Optional[MongoClient] = None
_mongo_db = None
_mongo_available = False

# Current session ID (unique per shell run)
_session_id: str = str(uuid.uuid4())
_session_start_time: datetime = datetime.now(timezone.utc)


# ==============================================================================
# CONNECTION MANAGEMENT
# ==============================================================================

def initialize_mongodb() -> bool:
    """
    Initialize MongoDB connection at application startup.
    
    DESIGN DECISION:
    - Connection is established once and reused throughout the session
    - Failure to connect does not crash the application
    - MongoDB is optional - the shell works without it
    
    Returns:
        True if connection successful, False otherwise
    """
    global _mongo_client, _mongo_db, _mongo_available
    
    if not PYMONGO_AVAILABLE:
        return False
    
    try:
        # Create MongoDB client with timeout
        _mongo_client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=MONGO_TIMEOUT_MS
        )
        
        # Test connection by issuing a ping command
        _mongo_client.admin.command('ping')
        
        # Select database (created automatically if doesn't exist)
        _mongo_db = _mongo_client[MONGO_DATABASE]
        
        # Create indexes for efficient querying
        _create_indexes()
        
        # Log session start
        _log_session_start()
        
        _mongo_available = True
        return True
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        _mongo_available = False
        print(f"[WARN] MongoDB connection failed: {e}")
        print("[WARN] Continuing without MongoDB logging.")
        return False
    except Exception as e:
        _mongo_available = False
        print(f"[WARN] MongoDB initialization error: {e}")
        return False


def _create_indexes():
    """
    Create indexes for efficient querying of log data.
    
    MONGODB CONCEPTS:
    - Indexes improve query performance on large collections
    - session_id index: Fast lookup of all logs for a session
    - timestamp index: Efficient time-range queries
    - Compound index: Optimizes queries filtering by both fields
    """
    global _mongo_db
    
    if _mongo_db is None:
        return
    
    interactions = _mongo_db[MONGO_COLLECTION_INTERACTIONS]
    
    # Index on session_id for filtering by session
    interactions.create_index("session_id")
    
    # Index on timestamp for time-based queries
    interactions.create_index("timestamp")
    
    # Compound index for session + time queries
    interactions.create_index([("session_id", 1), ("timestamp", -1)])


def close_mongodb():
    """
    Close MongoDB connection gracefully at application shutdown.
    Logs session end before closing.
    """
    global _mongo_client, _mongo_available
    
    if _mongo_available and _mongo_client:
        _log_session_end()
        _mongo_client.close()
        _mongo_available = False


def is_mongodb_available() -> bool:
    """Check if MongoDB is available for logging."""
    return _mongo_available


def get_session_id() -> str:
    """Get the current session ID."""
    return _session_id


# ==============================================================================
# SESSION LOGGING
# ==============================================================================

def _log_session_start():
    """
    Log the start of a new shell session.
    
    DOCUMENT STRUCTURE:
    Sessions collection stores metadata about each shell run,
    enabling analysis of usage patterns over time.
    """
    global _mongo_db, _session_id, _session_start_time
    
    if _mongo_db is None:
        return
    
    sessions = _mongo_db[MONGO_COLLECTION_SESSIONS]
    
    session_doc = {
        "session_id": _session_id,
        "start_time": _session_start_time,
        "end_time": None,
        "status": "active",
        "hostname": _get_hostname(),
        "platform": "Windows",
        "shell": "PowerShell",
        "interaction_count": 0
    }
    
    try:
        sessions.insert_one(session_doc)
    except Exception as e:
        print(f"[WARN] Failed to log session start: {e}")


def _log_session_end():
    """
    Update session document when shell exits.
    Records session duration and final statistics.
    """
    global _mongo_db, _session_id
    
    if _mongo_db is None:
        return
    
    sessions = _mongo_db[MONGO_COLLECTION_SESSIONS]
    interactions = _mongo_db[MONGO_COLLECTION_INTERACTIONS]
    
    try:
        # Count interactions for this session
        interaction_count = interactions.count_documents({"session_id": _session_id})
        
        # Update session document
        sessions.update_one(
            {"session_id": _session_id},
            {
                "$set": {
                    "end_time": datetime.now(timezone.utc),
                    "status": "completed",
                    "interaction_count": interaction_count
                }
            }
        )
    except Exception as e:
        print(f"[WARN] Failed to log session end: {e}")


def _get_hostname() -> str:
    """Get the hostname for logging context."""
    import socket
    try:
        return socket.gethostname()
    except:
        return "unknown"


# ==============================================================================
# INTERACTION LOGGING (MAIN LOGGING FUNCTION)
# ==============================================================================

def log_interaction(
    user_input: str,
    generated_command: Optional[str] = None,
    risk_level: Optional[int] = None,
    risk_label: Optional[str] = None,
    is_blocked: bool = False,
    user_approved: bool = False,
    was_executed: bool = False,
    execution_error: Optional[str] = None,
    execution_duration_ms: Optional[float] = None,
    used_template: bool = False,
    template_name: Optional[str] = None,
    ai_response_raw: Optional[str] = None,
    extra_metadata: Optional[Dict] = None
) -> Optional[str]:
    """
    Log a single user interaction to MongoDB.
    
    THIS IS THE PRIMARY LOGGING FUNCTION.
    
    DOCUMENT SCHEMA (Flexible):
    ===========================
    {
        "_id": ObjectId (auto-generated),
        "session_id": "uuid-string",
        "timestamp": ISODate,
        "user_input": "show me all files",
        "generated_command": "Get-ChildItem",
        "risk_level": 1,
        "risk_label": "Very Low",
        "is_blocked": false,
        "user_approved": true,
        "was_executed": true,
        "execution_error": null,
        "execution_duration_ms": 150.5,
        "used_template": false,
        "template_name": null,
        "ai_response_raw": "...",
        "metadata": { ... }  // Additional context
    }
    
    WHY THIS STRUCTURE:
    - Captures complete interaction lifecycle
    - Enables analysis of user behavior patterns
    - Supports debugging and audit requirements
    - Flexible schema allows adding new fields later
    
    Args:
        user_input: Original natural language request
        generated_command: Command generated by AI
        risk_level: Risk level from SQLite (1-5)
        risk_label: Human-readable risk label
        is_blocked: Whether command was blocked by policy
        user_approved: Whether user approved execution
        was_executed: Whether command was actually run
        execution_error: Error message if execution failed
        execution_duration_ms: Time taken to execute
        used_template: Whether approved template was used
        template_name: Name of template if used
        ai_response_raw: Raw response from Gemini
        extra_metadata: Any additional context
    
    Returns:
        The inserted document's ID as string, or None if failed
    """
    global _mongo_db, _session_id, _mongo_available
    
    # Silently skip if MongoDB unavailable
    if not _mongo_available or _mongo_db is None:
        return None
    
    interactions = _mongo_db[MONGO_COLLECTION_INTERACTIONS]
    
    # Build the document
    document = {
        "session_id": _session_id,
        "timestamp": datetime.now(timezone.utc),
        "user_input": user_input,
        "generated_command": generated_command,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "is_blocked": is_blocked,
        "user_approved": user_approved,
        "was_executed": was_executed,
        "execution_error": execution_error,
        "execution_duration_ms": execution_duration_ms,
        "used_template": used_template,
        "template_name": template_name,
    }
    
    # Add AI response if provided (can be large)
    if ai_response_raw:
        document["ai_response_raw"] = ai_response_raw
    
    # Add any extra metadata
    if extra_metadata:
        document["metadata"] = extra_metadata
    
    try:
        result = interactions.insert_one(document)
        return str(result.inserted_id)
    except Exception as e:
        # Log error but don't crash the application
        print(f"[WARN] MongoDB logging failed: {e}")
        return None


# ==============================================================================
# QUERY FUNCTIONS
# ==============================================================================

def get_session_interactions(limit: int = 20) -> List[Dict]:
    """
    Retrieve recent interactions from the current session.
    
    MONGODB QUERY:
    - Filters by session_id (uses index)
    - Sorts by timestamp descending (most recent first)
    - Limits results for performance
    
    Returns:
        List of interaction documents
    """
    global _mongo_db, _session_id, _mongo_available
    
    if not _mongo_available or _mongo_db is None:
        return []
    
    interactions = _mongo_db[MONGO_COLLECTION_INTERACTIONS]
    
    try:
        cursor = interactions.find(
            {"session_id": _session_id}
        ).sort("timestamp", -1).limit(limit)
        
        return list(cursor)
    except Exception as e:
        print(f"[WARN] Failed to query interactions: {e}")
        return []


def get_all_interactions(limit: int = 20) -> List[Dict]:
    """
    Retrieve recent interactions from ALL sessions.
    
    Unlike get_session_interactions(), this returns logs across all sessions,
    useful for viewing historical data when the current session has no logs.
    
    Returns:
        List of interaction documents from all sessions
    """
    global _mongo_db, _mongo_available
    
    if not _mongo_available or _mongo_db is None:
        return []
    
    interactions = _mongo_db[MONGO_COLLECTION_INTERACTIONS]
    
    try:
        cursor = interactions.find().sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[WARN] Failed to query all interactions: {e}")
        return []


def get_all_sessions(limit: int = 10) -> List[Dict]:
    """
    Retrieve recent session metadata.
    
    Useful for analyzing usage patterns across multiple shell runs.
    """
    global _mongo_db, _mongo_available
    
    if not _mongo_available or _mongo_db is None:
        return []
    
    sessions = _mongo_db[MONGO_COLLECTION_SESSIONS]
    
    try:
        cursor = sessions.find().sort("start_time", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[WARN] Failed to query sessions: {e}")
        return []


def get_interaction_statistics() -> Dict:
    """
    Get aggregate statistics from MongoDB using aggregation pipeline.
    
    MONGODB AGGREGATION:
    - $match: Filter by session
    - $group: Aggregate counts and averages
    - $count: Count documents
    
    Returns:
        Dictionary with statistics
    """
    global _mongo_db, _session_id, _mongo_available
    
    if not _mongo_available or _mongo_db is None:
        return {"mongodb_available": False}
    
    interactions = _mongo_db[MONGO_COLLECTION_INTERACTIONS]
    
    try:
        # Total count for session
        total = interactions.count_documents({"session_id": _session_id})
        
        # Executed count
        executed = interactions.count_documents({
            "session_id": _session_id,
            "was_executed": True
        })
        
        # Blocked count
        blocked = interactions.count_documents({
            "session_id": _session_id,
            "is_blocked": True
        })
        
        # Cancelled count (approved=False, not blocked)
        cancelled = interactions.count_documents({
            "session_id": _session_id,
            "user_approved": False,
            "is_blocked": False
        })
        
        # Risk level distribution using aggregation
        pipeline = [
            {"$match": {"session_id": _session_id, "risk_level": {"$ne": None}}},
            {"$group": {"_id": "$risk_level", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        risk_dist = {}
        for doc in interactions.aggregate(pipeline):
            risk_dist[doc["_id"]] = doc["count"]
        
        return {
            "mongodb_available": True,
            "session_id": _session_id[:8] + "...",
            "total_interactions": total,
            "executed": executed,
            "blocked": blocked,
            "cancelled": cancelled,
            "risk_distribution": risk_dist
        }
        
    except Exception as e:
        print(f"[WARN] Failed to get statistics: {e}")
        return {"mongodb_available": True, "error": str(e)}


# ==============================================================================
# UTILITY: EXECUTION TIMER CONTEXT MANAGER
# ==============================================================================

class ExecutionTimer:
    """
    Context manager to measure command execution time.
    
    Usage:
        with ExecutionTimer() as timer:
            subprocess.run(...)
        duration = timer.duration_ms
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration_ms = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000


# ==============================================================================
# EXAMPLE DOCUMENT (FOR DOCUMENTATION)
# ==============================================================================
"""
EXAMPLE MONGODB DOCUMENT:
=========================

{
    "_id": ObjectId("64a1b2c3d4e5f6g7h8i9j0k1"),
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": ISODate("2026-01-22T10:30:45.123Z"),
    "user_input": "delete all temp files",
    "generated_command": "Remove-Item -Path $env:TEMP\\* -Recurse",
    "risk_level": 5,
    "risk_label": "Critical",
    "is_blocked": false,
    "user_approved": true,
    "was_executed": true,
    "execution_error": null,
    "execution_duration_ms": 2345.67,
    "used_template": false,
    "template_name": null,
    "metadata": {
        "ai_model": "gemini-2.0-flash-exp",
        "validation_rules_matched": 2
    }
}

COLLECTIONS STRUCTURE:
======================

1. interactions (main logging collection)
   - Stores every command attempt
   - Schema-flexible for varying metadata
   - Indexed by session_id and timestamp

2. sessions (session metadata)
   - One document per shell run
   - Tracks session lifecycle
   - Stores aggregate statistics
"""


# ==============================================================================
# TEST FUNCTION
# ==============================================================================

def test_mongodb():
    """Test MongoDB connection and logging."""
    print("\n" + "=" * 60)
    print("MONGODB CONNECTION TEST")
    print("=" * 60)
    
    if not PYMONGO_AVAILABLE:
        print("[ERROR] pymongo not installed")
        return
    
    print(f"URI: {MONGO_URI}")
    print(f"Database: {MONGO_DATABASE}")
    
    success = initialize_mongodb()
    
    if success:
        print("[OK] MongoDB connected successfully")
        print(f"[OK] Session ID: {_session_id}")
        
        # Test logging
        doc_id = log_interaction(
            user_input="test command",
            generated_command="Get-ChildItem",
            risk_level=1,
            risk_label="Very Low",
            user_approved=True,
            was_executed=True
        )
        
        if doc_id:
            print(f"[OK] Test document inserted: {doc_id}")
        
        # Get statistics
        stats = get_interaction_statistics()
        print(f"[OK] Statistics: {stats}")
        
        close_mongodb()
        print("[OK] Connection closed")
    else:
        print("[WARN] MongoDB not available")
    
    print("=" * 60)


if __name__ == "__main__":
    test_mongodb()
