"""
Negotiation graph builder - LangGraph-style orchestration.

WHAT: Async state machine for multi-round negotiations
WHY: Orchestrate buyer turns, parallel seller responses, and decision logic
HOW: Async generator with nodes: BuyerTurn → Routing → ParallelSellers → DecisionCheck → loop
"""

import asyncio
import random
from typing import AsyncIterator, Optional
from datetime import datetime

from ..llm.provider import LLMProvider
from ..models.negotiation import NegotiationRoomState, NegotiationEvent
from ..models.message import Message
from ..models.agent import BuyerConstraints
from ..agents.buyer_agent import BuyerAgent
from ..agents.seller_agent import SellerAgent
from ..services.message_router import parse_mentions
from ..services.visibility_filter import filter_conversation
from ..core.config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NegotiationGraph:
    """Negotiation graph orchestrator."""
    
    def __init__(self, provider: LLMProvider):
        """
        Initialize negotiation graph.
        
        Args:
            provider: LLM provider instance
        """
        self.provider = provider
        self.max_rounds = settings.MAX_NEGOTIATION_ROUNDS
        self.parallel_limit = settings.PARALLEL_SELLER_LIMIT
        self.temperature = settings.LLM_DEFAULT_TEMPERATURE
        self.max_tokens = settings.LLM_DEFAULT_MAX_TOKENS
    
    async def run(
        self,
        room_state: NegotiationRoomState
    ) -> AsyncIterator[NegotiationEvent]:
        """
        Run negotiation graph to completion.
        
        WHAT: Execute negotiation rounds until decision or max rounds
        WHY: Orchestrate multi-agent negotiation flow
        HOW: Async generator emitting events for each step
        
        Args:
            room_state: Initial negotiation room state
            
        Yields:
            NegotiationEvent for each step (buyer_message, seller_response, etc.)
        """
        # Set seed for determinism if provided
        if room_state.seed is not None:
            random.seed(room_state.seed)
        
        room_state.status = "active"
        
        # Emit connected event
        yield {
            "type": "heartbeat",
            "data": {"message": "Negotiation started", "round": room_state.current_round},
            "timestamp": datetime.now()
        }
        
        try:
            while room_state.current_round < self.max_rounds:
                room_state.current_round += 1
                logger.info(f"Starting round {room_state.current_round}/{self.max_rounds}")
                
                # Node 1: Buyer Turn
                buyer_result = await self._buyer_turn_node(room_state)
                if not buyer_result:
                    break
                
                yield {
                    "type": "buyer_message",
                    "data": {
                        "message": buyer_result["message"],
                        "mentioned_sellers": buyer_result["mentioned_sellers"],
                        "round": room_state.current_round
                    },
                    "timestamp": datetime.now()
                }
                
                # Node 2: Message Routing (determine which sellers respond)
                responding_sellers = self._message_routing_node(
                    buyer_result["mentioned_sellers"],
                    room_state.sellers
                )
                
                if not responding_sellers:
                    logger.info("No sellers to respond, ending negotiation")
                    break
                
                # Node 3: Parallel Seller Responses
                seller_results = await self._parallel_seller_responses_node(
                    room_state,
                    responding_sellers
                )
                
                # Emit seller responses
                for seller_id, result in seller_results.items():
                    if result:
                        yield {
                            "type": "seller_response",
                            "data": {
                                "seller_id": seller_id,
                                "message": result["message"],
                                "offer": result.get("offer"),
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                
                # Node 4: Decision Check
                decision = self._decision_check_node(room_state, seller_results)
                
                if decision:
                    room_state.status = "completed"
                    room_state.selected_seller_id = decision["seller_id"]
                    room_state.final_offer = decision["offer"]
                    room_state.decision_reason = decision.get("reason", "Best offer selected")
                    
                    yield {
                        "type": "negotiation_complete",
                        "data": {
                            "selected_seller_id": decision["seller_id"],
                            "final_offer": decision["offer"],
                            "reason": decision.get("reason"),
                            "rounds": room_state.current_round
                        },
                        "timestamp": datetime.now()
                    }
                    break
                
                # Emit heartbeat
                yield {
                    "type": "heartbeat",
                    "data": {"message": f"Round {room_state.current_round} complete", "round": room_state.current_round},
                    "timestamp": datetime.now()
                }
            
            # Max rounds reached
            if room_state.current_round >= self.max_rounds and room_state.status != "completed":
                room_state.status = "aborted"
                yield {
                    "type": "negotiation_complete",
                    "data": {
                        "selected_seller_id": None,
                        "final_offer": None,
                        "reason": "Max rounds reached",
                        "rounds": room_state.current_round
                    },
                    "timestamp": datetime.now()
                }
        
        except Exception as e:
            logger.error(f"Negotiation graph error: {e}")
            room_state.status = "aborted"
            yield {
                "type": "error",
                "data": {"error": str(e), "round": room_state.current_round},
                "timestamp": datetime.now()
            }
    
    async def _buyer_turn_node(
        self,
        room_state: NegotiationRoomState
    ) -> Optional[dict]:
        """
        Buyer turn node - generate buyer message.
        
        WHAT: Create buyer agent and generate message
        WHY: Buyer needs to communicate with sellers
        HOW: Instantiate BuyerAgent, call run_turn, record message
        """
        try:
            buyer_agent = BuyerAgent(
                provider=self.provider,
                constraints=room_state.buyer_constraints,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            result = await buyer_agent.run_turn(room_state)
            
            # Record message in history
            message: Message = {
                "message_id": f"msg_{room_state.current_round}_buyer",
                "turn_number": room_state.current_round,
                "timestamp": datetime.now(),
                "sender_id": room_state.buyer_id,
                "sender_type": "buyer",
                "sender_name": room_state.buyer_name,
                "content": result["message"],
                "mentioned_sellers": result["mentioned_sellers"],
                "visibility": [s.seller_id for s in room_state.sellers] + [room_state.buyer_id]  # All can see buyer messages
            }
            
            room_state.conversation_history.append(message)
            
            return result
            
        except Exception as e:
            logger.error(f"Buyer turn error: {e}")
            return None
    
    def _message_routing_node(
        self,
        mentioned_sellers: list[str],
        all_sellers: list
    ) -> list:
        """
        Message routing node - determine which sellers respond.
        
        WHAT: Select sellers to respond based on mentions
        WHY: Only mentioned sellers should respond (or all if no mentions)
        HOW: Use mentioned list or default to all sellers
        """
        if mentioned_sellers:
            # Only mentioned sellers respond
            responding = [s for s in all_sellers if s.seller_id in mentioned_sellers]
            return responding
        else:
            # No mentions = all sellers can respond
            return all_sellers
    
    async def _parallel_seller_responses_node(
        self,
        room_state: NegotiationRoomState,
        sellers: list
    ) -> dict:
        """
        Parallel seller responses node.
        
        WHAT: Get responses from multiple sellers concurrently
        WHY: Sellers respond in parallel for efficiency
        HOW: asyncio.gather with semaphore limit, return_exceptions=True
        """
        semaphore = asyncio.Semaphore(self.parallel_limit)
        results = {}
        
        async def get_seller_response(seller):
            """Get response from a single seller."""
            async with semaphore:
                try:
                    # Find matching inventory item
                    inventory_item = None
                    for item in seller.inventory:
                        if item.item_id == room_state.buyer_constraints.item_id:
                            inventory_item = item
                            break
                    
                    if not inventory_item:
                        logger.warning(f"Seller {seller.name} has no inventory for item")
                        return None
                    
                    seller_agent = SellerAgent(
                        provider=self.provider,
                        seller=seller,
                        inventory_item=inventory_item,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    
                    # Filter conversation for this seller's visibility
                    seller_history = filter_conversation(
                        room_state.conversation_history,
                        seller.seller_id,
                        "seller"
                    )
                    
                    # Create temporary state with filtered history
                    temp_state = NegotiationRoomState(
                        room_id=room_state.room_id,
                        buyer_id=room_state.buyer_id,
                        buyer_name=room_state.buyer_name,
                        buyer_constraints=room_state.buyer_constraints,
                        sellers=room_state.sellers,
                        conversation_history=seller_history,
                        current_round=room_state.current_round,
                        max_rounds=room_state.max_rounds
                    )
                    
                    result = await seller_agent.respond(
                        temp_state,
                        room_state.buyer_name,
                        room_state.buyer_constraints
                    )
                    
                    # Record message in history
                    message: Message = {
                        "message_id": f"msg_{room_state.current_round}_seller_{seller.seller_id}",
                        "turn_number": room_state.current_round,
                        "timestamp": datetime.now(),
                        "sender_id": seller.seller_id,
                        "sender_type": "seller",
                        "sender_name": seller.name,
                        "content": result["message"],
                        "mentioned_sellers": [],
                        "offer": result.get("offer"),
                        "visibility": [room_state.buyer_id, seller.seller_id]  # Buyer and seller can see
                    }
                    
                    room_state.conversation_history.append(message)
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Seller {seller.name} response error: {e}")
                    return None
        
        # Gather all seller responses in parallel
        tasks = [get_seller_response(seller) for seller in sellers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map responses to seller IDs
        for seller, response in zip(sellers, responses):
            if isinstance(response, Exception):
                logger.error(f"Seller {seller.name} raised exception: {response}")
                results[seller.seller_id] = None
            else:
                results[seller.seller_id] = response
        
        return results
    
    def _decision_check_node(
        self,
        room_state: NegotiationRoomState,
        seller_results: dict
    ) -> Optional[dict]:
        """
        Decision check node - determine if buyer should decide.
        
        WHAT: Check if any offer meets buyer's criteria
        WHY: Buyer needs to select best offer or continue
        HOW: Simple heuristic - first valid offer within buyer's price range
        
        Args:
            room_state: Current room state
            seller_results: Dict of seller_id -> response dict
            
        Returns:
            Decision dict with seller_id and offer, or None to continue
        """
        valid_offers = []
        
        for seller_id, result in seller_results.items():
            if not result:
                continue
            
            offer = result.get("offer")
            if not offer:
                continue
            
            price = offer.get("price", 0)
            quantity = offer.get("quantity", 0)
            
            # Check if offer is within buyer's constraints
            if (room_state.buyer_constraints.min_price_per_unit <= price <= room_state.buyer_constraints.max_price_per_unit and
                quantity >= room_state.buyer_constraints.quantity_needed):
                valid_offers.append({
                    "seller_id": seller_id,
                    "offer": offer,
                    "price": price,
                    "quantity": quantity
                })
        
        if valid_offers:
            # Simple heuristic: select first valid offer (could be improved)
            # Sort by price (lowest first) as tie-breaker
            valid_offers.sort(key=lambda x: x["price"])
            best = valid_offers[0]
            
            return {
                "seller_id": best["seller_id"],
                "offer": best["offer"],
                "reason": f"Best offer: ${best['price']:.2f} per unit"
            }
        
        return None

