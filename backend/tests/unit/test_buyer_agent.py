"""
Tests for buyer agent.

WHAT: Test buyer agent behavior and output
WHY: Ensure buyer operates correctly with constraints
HOW: Use mock provider and assert results
"""

import pytest
from tests.fixtures.mock_llm import MockLLMProvider
from app.agents.buyer_agent import BuyerAgent
from app.models.negotiation import (
    NegotiationRoomState,
    BuyerConstraints,
    SellerProfile,
    Message
)


@pytest.mark.phase2
@pytest.mark.unit
class TestBuyerAgent:
    """Test buyer agent functionality."""
    
    @pytest.mark.asyncio
    async def test_basic_turn_execution(self):
        """Test buyer can execute a basic turn."""
        provider = MockLLMProvider(responses=["I need 100 widgets at $8 per unit."])
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={
                "s1": SellerProfile(seller_id="s1", display_name="Seller1")
            },
            active_sellers=["s1"]
        )
        
        result = await agent.run_turn(room_state)
        
        assert result.message == "I need 100 widgets at $8 per unit."
        assert isinstance(result.mentioned_sellers, list)
        assert result.raw_text is not None
    
    @pytest.mark.asyncio
    async def test_mention_parsing(self):
        """Test that buyer correctly parses @mentions."""
        provider = MockLLMProvider(
            responses=["@Seller1 and @Seller2, please send offers."]
        )
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={
                "s1": SellerProfile(seller_id="s1", display_name="Seller1"),
                "s2": SellerProfile(seller_id="s2", display_name="Seller2"),
                "s3": SellerProfile(seller_id="s3", display_name="Seller3")
            },
            active_sellers=["s1", "s2", "s3"]
        )
        
        result = await agent.run_turn(room_state)
        
        assert "s1" in result.mentioned_sellers
        assert "s2" in result.mentioned_sellers
        assert "s3" not in result.mentioned_sellers
    
    @pytest.mark.asyncio
    async def test_sanitization_of_forbidden_terms(self):
        """Test that forbidden internal terms are sanitized."""
        provider = MockLLMProvider(
            responses=["I know your cost price is $5, offer me the least price."]
        )
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            active_sellers=[]
        )
        
        result = await agent.run_turn(room_state)
        
        # Should have sanitized
        assert result.sanitized is True
        assert "cost price" not in result.message.lower()
        assert "least price" not in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_profanity_filtering(self):
        """Test that profanity is filtered."""
        provider = MockLLMProvider(
            responses=["This is fucking ridiculous, damn it!"]
        )
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            active_sellers=[]
        )
        
        result = await agent.run_turn(room_state)
        
        # Should have filtered profanity
        assert result.sanitized is True
        assert "fuck" not in result.message.lower()
        assert "damn" not in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_length_truncation(self):
        """Test that overly long output is truncated."""
        long_text = "word " * 500  # Very long response
        provider = MockLLMProvider(responses=[long_text])
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            active_sellers=[]
        )
        
        result = await agent.run_turn(room_state)
        
        # Should be truncated to reasonable length
        assert len(result.message) <= 2005  # 2000 + "..."
    
    @pytest.mark.asyncio
    async def test_conversation_history_included(self):
        """Test that conversation history is included in prompts."""
        provider = MockLLMProvider(responses=["Thanks for the offer."])
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        history = [
            Message(
                sender_id="buyer1",
                sender_type="buyer",
                content="Hello sellers",
                round_number=0,
                visible_to=["all"]
            ),
            Message(
                sender_id="s1",
                sender_type="seller",
                content="$9 per unit",
                round_number=0,
                visible_to=["all"]
            )
        ]
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            seller_profiles={
                "s1": SellerProfile(seller_id="s1", display_name="Seller1")
            },
            message_history=history,
            active_sellers=["s1"]
        )
        
        result = await agent.run_turn(room_state)
        
        # Provider should have been called with history
        assert len(provider.calls) == 1
        assert len(provider.calls[0]["messages"]) > 1  # System + history
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test that provider errors are handled gracefully."""
        from app.utils.exceptions import BuyerAgentError
        
        provider = MockLLMProvider(should_fail=True)
        
        constraints = BuyerConstraints(
            item_id="widget",
            item_name="Widget",
            quantity_needed=100,
            min_price_per_unit=5.0,
            max_price_per_unit=10.0
        )
        
        agent = BuyerAgent(provider, constraints)
        
        room_state = NegotiationRoomState(
            buyer_id="buyer1",
            buyer_constraints=constraints,
            room_id="test_room",
            current_round=5,
            active_sellers=[]
        )
        
        with pytest.raises(BuyerAgentError) as exc_info:
            await agent.run_turn(room_state)
        
        # Should wrap provider error with context
        assert exc_info.value.room_id == "test_room"
        assert exc_info.value.round_number == 5

