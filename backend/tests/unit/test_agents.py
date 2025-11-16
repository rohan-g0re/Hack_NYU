"""
Unit tests for buyer and seller agents with mock LLM provider.

WHAT: Test agent logic with controlled LLM responses
WHY: Verify agent behavior without real LLM calls
HOW: Mock provider returns predetermined responses
"""

import pytest
from app.llm.types import LLMResult, ProviderStatus
from app.agents.buyer_agent import BuyerAgent
from app.agents.seller_agent import SellerAgent
from app.models.agent import BuyerConstraints, Seller, SellerProfile, InventoryItem
from app.models.negotiation import NegotiationRoomState


class MockLLMProvider:
    """Mock LLM provider with controllable responses."""
    
    def __init__(self, responses: list[str]):
        """
        Initialize mock provider with predetermined responses.
        
        Args:
            responses: List of text responses to return in order
        """
        self.responses = responses
        self.call_count = 0
        self.last_messages = None
    
    async def generate(self, messages, *, temperature, max_tokens, stop=None):
        """Return next predetermined response."""
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        self.last_messages = messages
        return LLMResult(text=response, usage={"tokens": len(response)}, model="mock")
    
    async def ping(self):
        """Return available status."""
        return ProviderStatus(available=True, base_url="mock://localhost")
    
    async def stream(self, messages, *, temperature, max_tokens, stop=None):
        """Not used in Phase 2."""
        pass


@pytest.fixture
def mock_provider():
    """Create mock provider with default responses."""
    return MockLLMProvider(["I'd like to buy some items."])


@pytest.fixture
def sample_buyer_constraints():
    """Sample buyer constraints."""
    return BuyerConstraints(
        item_id="item1",
        item_name="Widget",
        quantity_needed=5,
        min_price_per_unit=10.0,
        max_price_per_unit=20.0
    )


@pytest.fixture
def sample_seller():
    """Sample seller configuration."""
    return Seller(
        seller_id="seller1",
        name="Alice",
        profile=SellerProfile(
            priority="customer_retention",
            speaking_style="very_sweet"
        ),
        inventory=[
            InventoryItem(
                item_id="item1",
                item_name="Widget",
                cost_price=8.0,
                selling_price=18.0,
                least_price=12.0,
                quantity_available=10
            )
        ]
    )


@pytest.fixture
def sample_room_state(sample_buyer_constraints, sample_seller):
    """Sample negotiation room state."""
    return NegotiationRoomState(
        room_id="room1",
        buyer_id="buyer1",
        buyer_name="Bob",
        buyer_constraints=sample_buyer_constraints,
        sellers=[sample_seller],
        conversation_history=[],
        current_round=1,
        max_rounds=5
    )


# Buyer Agent Tests

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_generates_valid_message_structure():
    """Test buyer agent generates dict with message and mentioned_sellers."""
    mock = MockLLMProvider(["Hello sellers!"])
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
        inventory=[]
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    buyer_agent = BuyerAgent(provider=mock, constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    assert "message" in result
    assert "mentioned_sellers" in result
    assert isinstance(result["message"], str)
    assert isinstance(result["mentioned_sellers"], list)
    assert len(result["message"]) > 0


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_extracts_mentions_from_message():
    """Test buyer agent extracts @mentions correctly."""
    mock = MockLLMProvider(["Hi @Alice and @Bob, I need widgets."])
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    sellers = [
        Seller(seller_id="s1", name="Alice", profile=SellerProfile(priority="maximize_profit", speaking_style="rude"), inventory=[]),
        Seller(seller_id="s2", name="Bob", profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"), inventory=[])
    ]
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Buyer",
        buyer_constraints=constraints, sellers=sellers
    )
    
    buyer_agent = BuyerAgent(provider=mock, constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    assert len(result["mentioned_sellers"]) == 2
    assert "s1" in result["mentioned_sellers"]
    assert "s2" in result["mentioned_sellers"]


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_sanitizes_output():
    """Test buyer agent sanitizes LLM output."""
    mock = MockLLMProvider(["```\nCode block\n```\nActual message"])
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[]
    )
    
    buyer_agent = BuyerAgent(provider=mock, constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    # Code blocks should be removed
    assert "```" not in result["message"]
    assert "Actual message" in result["message"]


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_limits_message_length():
    """Test buyer agent limits message length for safety."""
    # Create very long message
    long_message = "A" * 1000
    mock = MockLLMProvider([long_message])
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[]
    )
    
    buyer_agent = BuyerAgent(provider=mock, constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    # Should be truncated
    assert len(result["message"]) <= 500


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_buyer_agent_handles_provider_error():
    """Test buyer agent handles provider errors gracefully."""
    class ErrorProvider:
        async def generate(self, messages, *, temperature, max_tokens, stop=None):
            raise Exception("Provider error")
    
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[]
    )
    
    buyer_agent = BuyerAgent(provider=ErrorProvider(), constraints=constraints)
    result = await buyer_agent.run_turn(room_state)
    
    # Should return fallback message
    assert "message" in result
    assert len(result["message"]) > 0
    assert result["mentioned_sellers"] == []


# Seller Agent Tests

@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_generates_valid_response_structure():
    """Test seller agent generates dict with message and offer."""
    mock = MockLLMProvider(["I can help with that!"])
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    assert "message" in result
    assert "offer" in result
    assert isinstance(result["message"], str)
    assert len(result["message"]) > 0


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_parses_offer_json():
    """Test seller agent parses offer JSON from response."""
    mock = MockLLMProvider(['I can offer this: {"offer": {"price": 15.0, "quantity": 5}}'])
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    assert result["offer"] is not None
    assert result["offer"]["price"] == 15.0
    assert result["offer"]["quantity"] == 5


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_clamps_price_to_bounds():
    """Test seller agent clamps out-of-bounds prices."""
    # Price way too high (above selling_price)
    mock = MockLLMProvider(['{"offer": {"price": 999.0, "quantity": 5}}'])
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # Price should be clamped or rejected
    if result["offer"]:
        assert result["offer"]["price"] <= 18.0


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_rejects_below_minimum_offer():
    """Test seller agent rejects offers below least_price."""
    # Price below least_price
    mock = MockLLMProvider(['{"offer": {"price": 5.0, "quantity": 10}}'])
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # Offer should be None (rejected) or clamped to least_price
    if result["offer"]:
        assert result["offer"]["price"] >= 12.0
    else:
        assert result["offer"] is None


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_clamps_quantity_to_available():
    """Test seller agent clamps quantity to available stock."""
    # Quantity exceeds available
    mock = MockLLMProvider(['{"offer": {"price": 15.0, "quantity": 100}}'])
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # Quantity should be clamped to available (10)
    if result["offer"]:
        assert result["offer"]["quantity"] <= 10


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_handles_provider_error():
    """Test seller agent handles provider errors gracefully."""
    class ErrorProvider:
        async def generate(self, messages, *, temperature, max_tokens, stop=None):
            raise Exception("Provider error")
    
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="customer_retention", speaking_style="very_sweet"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=ErrorProvider(), seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # Should return fallback message
    assert "message" in result
    assert len(result["message"]) > 0
    assert result["offer"] is None


@pytest.mark.phase2
@pytest.mark.unit
@pytest.mark.asyncio
async def test_seller_agent_no_offer_is_valid():
    """Test seller agent can respond without making an offer."""
    mock = MockLLMProvider(["Let me think about it."])
    seller = Seller(
        seller_id="s1", name="Alice",
        profile=SellerProfile(priority="maximize_profit", speaking_style="rude"),
        inventory=[InventoryItem(
            item_id="item1", item_name="Widget",
            cost_price=8.0, selling_price=18.0, least_price=12.0, quantity_available=10
        )]
    )
    inventory_item = seller.inventory[0]
    constraints = BuyerConstraints(
        item_id="item1", item_name="Widget",
        quantity_needed=5, min_price_per_unit=10.0, max_price_per_unit=20.0
    )
    room_state = NegotiationRoomState(
        room_id="r1", buyer_id="b1", buyer_name="Bob",
        buyer_constraints=constraints, sellers=[seller]
    )
    
    seller_agent = SellerAgent(provider=mock, seller=seller, inventory_item=inventory_item)
    result = await seller_agent.respond(room_state, "Bob", constraints)
    
    # No offer is valid
    assert result["message"] == "Let me think about it."
    assert result["offer"] is None

