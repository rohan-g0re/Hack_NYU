"""
Tests for visibility filtering.

WHAT: Test conversation filtering by agent role
WHY: Ensure proper information asymmetry in negotiations
HOW: Test various visibility scopes and agent types
"""

import pytest
from app.services.visibility_filter import (
    calculate_visible_scope,
    is_visible,
    filter_conversation,
    filter_for_buyer,
    filter_for_seller
)
from app.models.negotiation import Message


@pytest.mark.phase2
@pytest.mark.unit
class TestVisibleScopeCalculation:
    """Test visibility scope calculation."""
    
    def test_buyer_scope(self):
        """Test buyer visibility scope."""
        scope = calculate_visible_scope("buyer1", "buyer")
        
        assert "all" in scope
        assert "buyer" in scope
        assert "buyer:buyer1" in scope
        assert "seller" not in scope
    
    def test_seller_scope(self):
        """Test seller visibility scope."""
        scope = calculate_visible_scope("seller1", "seller")
        
        assert "all" in scope
        assert "seller" in scope
        assert "seller:seller1" in scope
        assert "buyer" not in scope
    
    def test_system_scope(self):
        """Test system visibility scope (sees everything)."""
        scope = calculate_visible_scope("system", "system")
        
        assert "all" in scope
        assert "system" in scope
        assert "buyer" in scope
        assert "seller" in scope


@pytest.mark.phase2
@pytest.mark.unit
class TestMessageVisibility:
    """Test individual message visibility checks."""
    
    def test_all_visible_to_everyone(self):
        """Test that 'all' messages are visible to everyone."""
        msg = Message(
            sender_id="buyer1",
            sender_type="buyer",
            content="Hello",
            round_number=0,
            visible_to=["all"]
        )
        
        buyer_scope = ["all", "buyer", "buyer:buyer1"]
        seller_scope = ["all", "seller", "seller:seller1"]
        
        assert is_visible(msg, buyer_scope) is True
        assert is_visible(msg, seller_scope) is True
    
    def test_buyer_only_message(self):
        """Test buyer-only message visibility."""
        msg = Message(
            sender_id="system",
            sender_type="system",
            content="Internal buyer note",
            round_number=0,
            visible_to=["buyer"]
        )
        
        buyer_scope = ["all", "buyer", "buyer:buyer1"]
        seller_scope = ["all", "seller", "seller:seller1"]
        
        assert is_visible(msg, buyer_scope) is True
        assert is_visible(msg, seller_scope) is False
    
    def test_seller_specific_message(self):
        """Test seller-specific message visibility."""
        msg = Message(
            sender_id="seller1",
            sender_type="seller",
            content="Internal note",
            round_number=0,
            visible_to=["seller:seller1"]
        )
        
        buyer_scope = ["all", "buyer"]
        seller1_scope = ["all", "seller", "seller:seller1"]
        seller2_scope = ["all", "seller", "seller:seller2"]
        
        assert is_visible(msg, buyer_scope) is False
        assert is_visible(msg, seller1_scope) is True
        assert is_visible(msg, seller2_scope) is False
    
    def test_multiple_visibility_tokens(self):
        """Test message with multiple visibility tokens."""
        msg = Message(
            sender_id="seller1",
            sender_type="seller",
            content="Offer details",
            round_number=0,
            visible_to=["buyer", "seller:seller1"]
        )
        
        buyer_scope = ["all", "buyer"]
        seller1_scope = ["all", "seller", "seller:seller1"]
        seller2_scope = ["all", "seller", "seller:seller2"]
        
        assert is_visible(msg, buyer_scope) is True
        assert is_visible(msg, seller1_scope) is True
        assert is_visible(msg, seller2_scope) is False
    
    def test_empty_visible_to_defaults_to_all(self):
        """Test that empty visible_to defaults to visible."""
        msg = Message(
            sender_id="buyer1",
            sender_type="buyer",
            content="Hello",
            round_number=0,
            visible_to=[]
        )
        
        buyer_scope = ["all", "buyer"]
        seller_scope = ["all", "seller"]
        
        # Empty should default to visible
        assert is_visible(msg, buyer_scope) is True
        assert is_visible(msg, seller_scope) is True


@pytest.mark.phase2
@pytest.mark.unit
class TestConversationFiltering:
    """Test full conversation filtering."""
    
    def test_buyer_sees_public_messages(self):
        """Test that buyer sees all public messages."""
        history = [
            Message(
                sender_id="buyer1",
                sender_type="buyer",
                content="Buyer message",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Seller response",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="seller2",
                sender_type="seller",
                content="Another seller",
                round_number=0,
                visible_to=["all"]
            )
        ]
        
        filtered = filter_for_buyer(history, "buyer1")
        
        assert len(filtered) == 3
    
    def test_buyer_does_not_see_seller_private(self):
        """Test that buyer doesn't see seller-private messages."""
        history = [
            Message(
                sender_id="buyer1",
                sender_type="buyer",
                content="Public message",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Private seller note",
                round_number=0,
                visible_to=["seller:seller1"]
            ),
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Public response",
                round_number=0,
                visible_to=["all"]
            )
        ]
        
        filtered = filter_for_buyer(history, "buyer1")
        
        assert len(filtered) == 2
        assert "Private seller note" not in [m.content for m in filtered]
    
    def test_seller_sees_own_and_buyer_messages(self):
        """Test that seller sees buyer and own messages."""
        history = [
            Message(
                sender_id="buyer1",
                sender_type="buyer",
                content="Buyer to all",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Seller1 response",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="seller2",
                sender_type="seller",
                content="Seller2 private",
                round_number=0,
                visible_to=["seller:seller2"]
            )
        ]
        
        filtered = filter_for_seller(history, "seller1")
        
        assert len(filtered) == 2
        assert "Seller2 private" not in [m.content for m in filtered]
    
    def test_seller_does_not_see_other_seller_private(self):
        """Test that sellers don't see each other's private messages."""
        history = [
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Seller1 private",
                round_number=0,
                visible_to=["seller:seller1"]
            ),
            Message(
                sender_id="seller2",
                sender_type="seller",
                content="Seller2 private",
                round_number=0,
                visible_to=["seller:seller2"]
            )
        ]
        
        filtered_seller1 = filter_for_seller(history, "seller1")
        filtered_seller2 = filter_for_seller(history, "seller2")
        
        assert len(filtered_seller1) == 1
        assert filtered_seller1[0].content == "Seller1 private"
        
        assert len(filtered_seller2) == 1
        assert filtered_seller2[0].content == "Seller2 private"
    
    def test_system_sees_everything(self):
        """Test that system agent sees all messages."""
        history = [
            Message(
                sender_id="buyer1",
                sender_type="buyer",
                content="Buyer message",
                round_number=0,
                visible_to=["buyer"]
            ),
            Message(
                sender_id="seller1",
                sender_type="seller",
                content="Seller private",
                round_number=0,
                visible_to=["seller:seller1"]
            ),
            Message(
                sender_id="system",
                sender_type="system",
                content="System note",
                round_number=0,
                visible_to=["system"]
            )
        ]
        
        filtered = filter_conversation(history, "system", "system")
        
        assert len(filtered) == 3
    
    def test_empty_history(self):
        """Test filtering empty history."""
        filtered = filter_for_buyer([], "buyer1")
        assert filtered == []

