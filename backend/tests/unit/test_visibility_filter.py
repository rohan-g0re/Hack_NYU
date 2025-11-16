"""
Unit tests for conversation visibility filtering.

WHAT: Test message filtering based on agent visibility rules
WHY: Ensure opaque negotiation model works correctly
HOW: Test buyer and seller visibility filters
"""

import pytest
from datetime import datetime
from app.services.visibility_filter import filter_conversation
from app.models.message import Message


@pytest.fixture
def sample_messages():
    """Sample conversation history."""
    return [
        {
            "message_id": "msg1",
            "turn_number": 1,
            "timestamp": datetime.now(),
            "sender_id": "buyer1",
            "sender_type": "buyer",
            "sender_name": "Buyer",
            "content": "Hello, I need widgets",
            "mentioned_sellers": ["seller1"],
            "visibility": ["buyer1", "seller1", "seller2"]
        },
        {
            "message_id": "msg2",
            "turn_number": 1,
            "timestamp": datetime.now(),
            "sender_id": "seller1",
            "sender_type": "seller",
            "sender_name": "Seller1",
            "content": "I can help",
            "mentioned_sellers": [],
            "visibility": ["buyer1", "seller1"]  # Only buyer and seller1
        },
        {
            "message_id": "msg3",
            "turn_number": 1,
            "timestamp": datetime.now(),
            "sender_id": "seller2",
            "sender_type": "seller",
            "sender_name": "Seller2",
            "content": "I also have widgets",
            "mentioned_sellers": [],
            "visibility": ["buyer1", "seller2"]  # Only buyer and seller2
        },
        {
            "message_id": "msg4",
            "turn_number": 2,
            "timestamp": datetime.now(),
            "sender_id": "buyer1",
            "sender_type": "buyer",
            "sender_name": "Buyer",
            "content": "Thanks both",
            "mentioned_sellers": [],
            "visibility": ["buyer1", "seller1", "seller2"]
        }
    ]


def test_filter_conversation_buyer_sees_all_buyer_messages(sample_messages):
    """Test buyer sees all buyer messages."""
    filtered = filter_conversation(
        sample_messages,
        agent_id="buyer1",
        agent_type="buyer"
    )
    
    buyer_messages = [m for m in filtered if m["sender_type"] == "buyer"]
    assert len(buyer_messages) == 2  # Both buyer messages visible


def test_filter_conversation_buyer_sees_visible_seller_messages(sample_messages):
    """Test buyer sees seller messages where buyer is in visibility."""
    filtered = filter_conversation(
        sample_messages,
        agent_id="buyer1",
        agent_type="buyer"
    )
    
    seller_messages = [m for m in filtered if m["sender_type"] == "seller"]
    assert len(seller_messages) == 2  # Both seller messages visible to buyer


def test_filter_conversation_buyer_hides_private_seller_messages():
    """Test buyer doesn't see seller messages where buyer not in visibility."""
    messages = [
        {
            "message_id": "msg1",
            "turn_number": 1,
            "timestamp": datetime.now(),
            "sender_id": "seller1",
            "sender_type": "seller",
            "sender_name": "Seller1",
            "content": "Private message",
            "mentioned_sellers": [],
            "visibility": ["seller1", "seller2"]  # Buyer NOT in visibility
        }
    ]
    
    filtered = filter_conversation(
        messages,
        agent_id="buyer1",
        agent_type="buyer"
    )
    
    assert len(filtered) == 0  # Buyer shouldn't see this


def test_filter_conversation_seller_sees_all_messages(sample_messages):
    """Test seller sees all messages."""
    filtered = filter_conversation(
        sample_messages,
        agent_id="seller1",
        agent_type="seller"
    )
    
    assert len(filtered) == len(sample_messages)  # Seller sees everything


def test_filter_conversation_empty_history():
    """Test filtering empty history."""
    filtered = filter_conversation([], agent_id="buyer1", agent_type="buyer")
    assert len(filtered) == 0


def test_filter_conversation_buyer_sees_mentioned_seller_message():
    """Test buyer sees seller message when buyer is mentioned."""
    messages = [
        {
            "message_id": "msg1",
            "turn_number": 1,
            "timestamp": datetime.now(),
            "sender_id": "seller1",
            "sender_type": "seller",
            "sender_name": "Seller1",
            "content": "Hello buyer",
            "mentioned_sellers": [],
            "visibility": ["buyer1", "seller1"]  # Buyer in visibility
        }
    ]
    
    filtered = filter_conversation(
        messages,
        agent_id="buyer1",
        agent_type="buyer"
    )
    
    assert len(filtered) == 1  # Buyer should see this

