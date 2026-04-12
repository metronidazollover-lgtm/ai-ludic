"""
Services Module - Streamlined for Crypto Sniper
"""

from typing import Optional, Dict
from database import get_db_connection

def _get_agent_by_token(token: str) -> Optional[Dict]:
    """Get agent by token."""
    if not token:
        return None
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agents WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# All marketplace, social, and subscription services have been purged.
# The bot directly uses internal analysis and market_intel modules.
