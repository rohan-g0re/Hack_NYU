"""
Negotiation graph orchestrator.

WHAT: State machine for multi-round buyer-seller negotiations
WHY: Coordinate turns, handle parallelism, emit events
HOW: Async loop with buyer/seller nodes, bounded concurrency, event streaming
"""

import asyncio
import random
from typing import AsyncIterator, Dict, TypedDict, Literal
from datetime import datetime

from ..llm.provider import LLMProvider
from ..models.negotiation import (
    NegotiationRoomState,
    Message,
    NegotiationOutcome
)
from ..agents.buyer_agent import BuyerAgent
from ..agents.seller_agent import SellerAgent
from ..services.message_router import select_targets
from ..utils.exceptions import BuyerAgentError, SellerAgentError, NegotiationGraphError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NegotiationEvent(TypedDict):
    """Event emitted during negotiation for streaming to clients."""
    type: Literal["buyer_message", "seller_response", "negotiation_complete", "error", "heartbeat"]
    data: dict


class NegotiationGraph:
    """
    Orchestrator for buyer-seller negotiation rounds.
    
    WHAT: State machine managing negotiation flow
    WHY: Coordinate multi-agent interactions with controlled concurrency
    HOW: Async generator emitting events for each step
    """
    
    def __init__(
        self,
        buyer_agent: BuyerAgent,
        seller_agents: Dict[str, SellerAgent],
        *,
        semaphore_size: int = 10
    ):
        """
        Initialize negotiation graph.
        
        Args:
            buyer_agent: Buyer agent instance
            seller_agents: Dict of seller_id -> SellerAgent
            semaphore_size: Max concurrent seller responses
        """
        self.buyer_agent = buyer_agent
        self.seller_agents = seller_agents
        self.semaphore = asyncio.Semaphore(semaphore_size)
        
        logger.info(
            f"NegotiationGraph initialized with {len(seller_agents)} sellers, "
            f"semaphore={semaphore_size}"
        )
    
    async def run(self, room_state: NegotiationRoomState) -> AsyncIterator[NegotiationEvent]:
        """
        Run negotiation rounds until completion.
        
        WHAT: Execute negotiation loop with event emission
        WHY: Drive conversation to decision or max rounds
        HOW: Sequential seller exchanges per round (buyer→seller1, seller1→buyer, buyer→seller2, etc.)
        
        Args:
            room_state: Negotiation state (modified in place)
        
        Yields:
            NegotiationEvent for each step
        """
        # Seed randomness for deterministic testing
        random.seed(room_state.seed)
        
        logger.info(
            f"Starting negotiation in room {room_state.room_id}, "
            f"exchanges_per_seller={room_state.max_rounds}, "
            f"sellers={len(room_state.active_sellers)}, seed={room_state.seed}"
        )
        
        room_state.status = "in_progress"
        
        # Initialize exchange tracking
        for seller_id in room_state.active_sellers:
            room_state.exchanges_completed[seller_id] = 0
        
        try:
            # Outer loop: rounds (exchanges per seller)
            for exchange_round in range(room_state.max_rounds):
                room_state.current_round = exchange_round
                
                logger.debug(f"Round {exchange_round + 1}/{room_state.max_rounds}")
                
                # Inner loop: cycle through sellers sequentially
                for seller_index, seller_id in enumerate(room_state.active_sellers):
                    room_state.current_seller_index = seller_index
                    
                    logger.debug(
                        f"Round {exchange_round + 1}/{room_state.max_rounds}, "
                        f"Seller {seller_index + 1}/{len(room_state.active_sellers)}: {seller_id}"
                    )
                    
                    # === BUYER TURN (addressing current seller) ===
                    try:
                        buyer_result = await self.buyer_agent.run_turn(room_state)
                        
                        # Add buyer message to history
                        buyer_msg = Message(
                            sender_id=room_state.buyer_id,
                            sender_type="buyer",
                            content=buyer_result.message,
                            round_number=exchange_round,
                            visible_to=["all"],
                            metadata={"target_seller": seller_id, "seller_index": seller_index}
                        )
                        room_state.message_history.append(buyer_msg)
                        
                        # Emit buyer message event
                        yield NegotiationEvent(
                            type="buyer_message",
                            data={
                                "room_id": room_state.room_id,
                                "round": exchange_round,
                                "seller_id": seller_id,
                                "seller_index": seller_index,
                                "message_id": buyer_msg.message_id,
                                "content": buyer_result.message,
                                "timestamp": buyer_msg.timestamp.isoformat()
                            }
                        )
                        
                    except BuyerAgentError as e:
                        logger.error(f"Buyer agent error: {e}")
                        yield NegotiationEvent(
                            type="error",
                            data={
                                "room_id": room_state.room_id,
                                "round": exchange_round,
                                "agent": "buyer",
                                "seller_id": seller_id,
                                "error": str(e),
                                "recoverable": False
                            }
                        )
                        room_state.status = "failed"
                        return
                    
                    # === SELLER RESPONSE (only current seller) ===
                    try:
                        seller_response = await self._seller_response_task(seller_id, room_state)
                        
                        # Add seller message to history
                        seller_msg = Message(
                            sender_id=seller_id,
                            sender_type="seller",
                            content=seller_response.message,
                            round_number=exchange_round,
                            visible_to=["all", f"seller:{seller_id}"]
                        )
                        room_state.message_history.append(seller_msg)
                        
                        # Add offer to history if present
                        if seller_response.offer:
                            room_state.offer_history.append(seller_response.offer)
                        
                        # Increment exchange counter
                        room_state.exchanges_completed[seller_id] += 1
                        
                        # Emit seller response event
                        yield NegotiationEvent(
                            type="seller_response",
                            data={
                                "room_id": room_state.room_id,
                                "round": exchange_round,
                                "seller_id": seller_id,
                                "exchange_number": room_state.exchanges_completed[seller_id],
                                "message_id": seller_msg.message_id,
                                "content": seller_response.message,
                                "offer": {
                                    "offer_id": seller_response.offer.offer_id,
                                    "price": seller_response.offer.price,
                                    "quantity": seller_response.offer.quantity,
                                    "item_id": seller_response.offer.item_id
                                } if seller_response.offer else None,
                                "violations": seller_response.violations,
                                "timestamp": seller_msg.timestamp.isoformat()
                            }
                        )
                        
                    except Exception as e:
                        logger.error(f"Seller {seller_id} error: {e}")
                        yield NegotiationEvent(
                            type="error",
                            data={
                                "room_id": room_state.room_id,
                                "round": exchange_round,
                                "agent": "seller",
                                "seller_id": seller_id,
                                "error": str(e),
                                "recoverable": True
                            }
                        )
                        # Continue to next seller (don't fail entire negotiation)
                        continue
                    
                    # === HEARTBEAT ===
                    yield NegotiationEvent(
                        type="heartbeat",
                        data={
                            "room_id": room_state.room_id,
                            "round": exchange_round,
                            "current_seller": seller_id,
                            "seller_index": seller_index,
                            "exchanges_completed": room_state.exchanges_completed.copy(),
                            "offers_count": len(room_state.offer_history),
                            "messages_count": len(room_state.message_history)
                        }
                    )
                
                # End of seller loop for this round
                
                # === DECISION CHECK (after all sellers in this round) ===
                decision = self._check_decision(room_state)
                
                if decision:
                    # Negotiation complete - early exit after full round
                    outcome = decision
                    room_state.status = "completed"
                    
                    yield NegotiationEvent(
                        type="negotiation_complete",
                        data={
                            "room_id": room_state.room_id,
                            "total_rounds": exchange_round + 1,
                            "exchanges_completed": room_state.exchanges_completed.copy(),
                            "winner_id": outcome.winner_id,
                            "winning_offer": {
                                "offer_id": outcome.winning_offer.offer_id,
                                "seller_id": outcome.winning_offer.seller_id,
                                "price": outcome.winning_offer.price,
                                "quantity": outcome.winning_offer.quantity,
                                "item_id": outcome.winning_offer.item_id
                            } if outcome.winning_offer else None,
                            "reason": outcome.reason,
                            "timestamp": outcome.timestamp.isoformat()
                        }
                    )
                    
                    logger.info(
                        f"Negotiation completed in room {room_state.room_id}: "
                        f"{outcome.reason}"
                    )
                    return  # Early exit after completing full round
            
            # Max rounds reached without decision
            if room_state.status == "in_progress":
                outcome = NegotiationOutcome(
                    winner_id=None,
                    winning_offer=None,
                    total_rounds=room_state.max_rounds,
                    reason=f"Max rounds reached ({room_state.max_rounds} rounds with all sellers), no acceptable offer"
                )
                room_state.status = "completed"
                
                yield NegotiationEvent(
                    type="negotiation_complete",
                    data={
                        "room_id": room_state.room_id,
                        "total_rounds": room_state.max_rounds,
                        "exchanges_completed": room_state.exchanges_completed.copy(),
                        "winner_id": None,
                        "winning_offer": None,
                        "reason": outcome.reason,
                        "timestamp": outcome.timestamp.isoformat()
                    }
                )
                
                logger.info(f"Negotiation completed {room_state.max_rounds} rounds in room {room_state.room_id}")
        
        except Exception as e:
            logger.error(f"Unexpected error in negotiation graph: {e}", exc_info=True)
            room_state.status = "failed"
            
            yield NegotiationEvent(
                type="error",
                data={
                    "room_id": room_state.room_id,
                    "round": room_state.current_round,
                    "agent": "graph",
                    "error": str(e),
                    "recoverable": False
                }
            )
    
    async def _seller_response_task(self, seller_id: str, room_state: NegotiationRoomState):
        """
        Task for a single seller response with semaphore.
        
        Args:
            seller_id: Seller to respond
            room_state: Current state
        
        Returns:
            SellerResponse
        
        Raises:
            SellerAgentError: If seller processing fails
        """
        async with self.semaphore:
            seller_agent = self.seller_agents.get(seller_id)
            if not seller_agent:
                raise SellerAgentError(
                    f"Seller agent not found: {seller_id}",
                    seller_id=seller_id,
                    room_id=room_state.room_id,
                    round_number=room_state.current_round
                )
            
            return await seller_agent.respond(room_state)
    
    def _check_decision(self, room_state: NegotiationRoomState) -> NegotiationOutcome | None:
        """
        Check if negotiation should conclude with a decision.
        
        WHAT: Evaluate if an acceptable offer exists
        WHY: Determine negotiation completion
        HOW: Find best valid offer meeting buyer constraints
        
        Args:
            room_state: Current negotiation state
        
        Returns:
            NegotiationOutcome if decision made, None otherwise
        """
        if not room_state.offer_history:
            return None
        
        constraints = room_state.buyer_constraints
        
        # Filter valid offers from current and previous rounds
        valid_offers = [
            offer for offer in room_state.offer_history
            if (
                offer.status == "pending" and
                offer.price <= constraints.max_price_per_unit and
                offer.price >= constraints.min_price_per_unit and
                offer.quantity >= constraints.quantity_needed
            )
        ]
        
        if not valid_offers:
            return None
        
        # Simple decision: pick lowest price that meets quantity
        # In Phase 3, this will be more sophisticated with decision_engine
        best_offer = min(valid_offers, key=lambda o: o.price)
        
        # Check budget constraint if present
        if constraints.budget_per_item:
            total_cost = best_offer.price * best_offer.quantity
            if total_cost > constraints.budget_per_item:
                return None
        
        # Accept best offer
        best_offer.status = "accepted"
        
        return NegotiationOutcome(
            winner_id=best_offer.seller_id,
            winning_offer=best_offer,
            total_rounds=room_state.current_round + 1,
            reason=f"Accepted offer: ${best_offer.price:.2f}/unit for {best_offer.quantity} units"
        )

