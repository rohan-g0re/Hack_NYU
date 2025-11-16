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
from ..agents.prompts import render_decision_prompt
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
        logger.info(f"Starting negotiation graph for room {room_state.room_id}")
        logger.info(f"Max rounds: {self.max_rounds}, Current round: {room_state.current_round}")
        logger.info(f"Number of sellers: {len(room_state.sellers)}")
        
        # Emit connected event
        yield {
            "type": "heartbeat",
            "data": {"message": "Negotiation started", "round": room_state.current_round},
            "timestamp": datetime.now()
        }
        
        try:
            while room_state.current_round < self.max_rounds:
                room_state.current_round += 1
                logger.info(f"=== Starting round {room_state.current_round}/{self.max_rounds} ===")
                
                # Emit round_start event
                yield {
                    "type": "round_start",
                    "data": {
                        "round_number": room_state.current_round,
                        "max_rounds": self.max_rounds
                    },
                    "timestamp": datetime.now()
                }
                
                # Node 1: Buyer Turn
                buyer_result = await self._buyer_turn_node(room_state)
                if not buyer_result:
                    break
                
                yield {
                    "type": "buyer_message",
                    "data": {
                        "sender_id": room_state.buyer_id,
                        "sender_name": room_state.buyer_name,
                        "sender_type": "buyer",
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
                        # Find seller name
                        seller_name = next(
                            (s.name for s in room_state.sellers if s.seller_id == seller_id),
                            "Unknown Seller"
                        )
                        
                        yield {
                            "type": "seller_response",
                            "data": {
                                "seller_id": seller_id,
                                "sender_name": seller_name,
                                "sender_type": "seller",
                                "message": result["message"],
                                "offer": result.get("offer"),
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                
                # Node 4: Decision Check (async - buyer agent decides)
                decision = await self._decision_check_node(room_state, seller_results)
                
                if decision:
                    room_state.status = "completed"
                    room_state.selected_seller_id = decision["seller_id"]
                    room_state.final_offer = decision["offer"]
                    room_state.decision_reason = decision.get("reason", "Best offer selected")
                    
                    # Find seller name
                    selected_seller_name = next(
                        (s.name for s in room_state.sellers if s.seller_id == decision["seller_id"]),
                        "Unknown Seller"
                    )
                    
                    # Emit decision event first
                    yield {
                        "type": "decision",
                        "data": {
                            "decision": "accept",
                            "chosen_seller_id": decision["seller_id"],
                            "chosen_seller_name": selected_seller_name,
                            "final_price": decision["offer"]["price"],
                            "final_quantity": decision["offer"]["quantity"],
                            "total_cost": decision["offer"]["price"] * decision["offer"]["quantity"],
                            "reason": decision.get("reason", "Best offer selected")
                        },
                        "timestamp": datetime.now()
                    }
                    
                    # Then emit completion
                    yield {
                        "type": "negotiation_complete",
                        "data": {
                            "selected_seller_id": decision["seller_id"],
                            "selected_seller_name": selected_seller_name,
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
            logger.info(f"Creating buyer agent for room {room_state.room_id}")
            buyer_agent = BuyerAgent(
                provider=self.provider,
                constraints=room_state.buyer_constraints,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Filter conversation for buyer's visibility
            buyer_history = filter_conversation(
                room_state.conversation_history,
                room_state.buyer_id,
                "buyer"
            )
            
            # Create temporary state with filtered history
            temp_state = NegotiationRoomState(
                room_id=room_state.room_id,
                buyer_id=room_state.buyer_id,
                buyer_name=room_state.buyer_name,
                buyer_constraints=room_state.buyer_constraints,
                sellers=room_state.sellers,
                conversation_history=buyer_history,  # Use filtered history
                current_round=room_state.current_round,
                max_rounds=room_state.max_rounds,
                llm_provider=room_state.llm_provider,
                llm_model=room_state.llm_model
            )
            
            logger.info(f"Running buyer turn for round {room_state.current_round}")
            result = await buyer_agent.run_turn(temp_state)
            logger.info(f"Buyer agent returned result: {result}")
            
            if not result:
                logger.error("Buyer agent returned None/empty result")
                return None
            
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
            logger.info(f"Buyer message added to history: {result['message'][:100]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Buyer turn error: {e}", exc_info=True)
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
            logger.info(f"Message routing: mentioned_sellers={mentioned_sellers}")
            logger.info(f"Message routing: all_sellers IDs={[s.seller_id for s in all_sellers]}, names={[s.name for s in all_sellers]}")
            responding = [s for s in all_sellers if s.seller_id in mentioned_sellers]
            logger.info(f"Message routing: selected {len(responding)} sellers to respond: {[s.name for s in responding]}")
            return responding
        else:
            # No mentions = all sellers can respond
            logger.info(f"Message routing: no mentions, all {len(all_sellers)} sellers can respond")
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
                    logger.info(f"Getting response from seller {seller.name} (ID: {seller.seller_id}) for item: {room_state.buyer_constraints.item_name}")
                    logger.debug(f"Seller {seller.name} inventory items: {[item.item_name for item in seller.inventory]}")
                    
                    # Find matching inventory item by item_name (case-insensitive)
                    inventory_item = None
                    for item in seller.inventory:
                        if item.item_name.lower().strip() == room_state.buyer_constraints.item_name.lower().strip():
                            inventory_item = item
                            logger.info(f"Found matching inventory item for {seller.name}: {item.item_name}")
                            break
                    
                    if not inventory_item:
                        logger.warning(f"Seller {seller.name} (ID: {seller.seller_id}) has no inventory for item '{room_state.buyer_constraints.item_name}'. Available items: {[item.item_name for item in seller.inventory]}")
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
                        max_rounds=room_state.max_rounds,
                        llm_provider=room_state.llm_provider,
                        llm_model=room_state.llm_model  # Pass model to temp state
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
                    
                    logger.info(f"Seller {seller.name} successfully generated response")
                    return result
                    
                except Exception as e:
                    logger.error(f"Seller {seller.name} (ID: {seller.seller_id}) response error: {e}", exc_info=True)
                    return None
        
        # Gather all seller responses in parallel
        tasks = [get_seller_response(seller) for seller in sellers]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Map responses to seller IDs
        for seller, response in zip(sellers, responses):
            if isinstance(response, Exception):
                logger.error(f"Seller {seller.name} (ID: {seller.seller_id}) raised exception: {response}", exc_info=True)
                results[seller.seller_id] = None
            elif response is None:
                logger.warning(f"Seller {seller.name} (ID: {seller.seller_id}) returned None response")
                results[seller.seller_id] = None
            else:
                logger.info(f"Seller {seller.name} (ID: {seller.seller_id}) response mapped successfully")
                results[seller.seller_id] = response
        
        return results
    
    async def _decision_check_node(
        self,
        room_state: NegotiationRoomState,
        seller_results: dict
    ) -> Optional[dict]:
        """
        Decision check node - let buyer agent decide if they want to accept.
        
        WHAT: Use buyer agent to decide if they want to accept an offer or continue
        WHY: Buyer should make decision based on conversation context, not just price
        HOW: Extract valid offers, ask buyer agent, parse decision response
        
        Args:
            room_state: Current room state
            seller_results: Dict of seller_id -> response dict
            
        Returns:
            Decision dict with seller_id and offer, or None to continue
        """
        # Check minimum rounds requirement
        min_rounds = settings.MIN_NEGOTIATION_ROUNDS
        if room_state.current_round < min_rounds:
            logger.debug(f"Round {room_state.current_round} < min {min_rounds}, continuing")
            return None
        
        # Extract valid offers
        valid_offers = []
        seller_id_to_name = {s.seller_id: s.name for s in room_state.sellers}
        
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
                    "seller_name": seller_id_to_name.get(seller_id, seller_id),
                    "offer": offer,
                    "price": price,
                    "quantity": quantity
                })
        
        if not valid_offers:
            logger.debug("No valid offers, continuing negotiation")
            return None
        
        # Sort offers by price (lowest first) for presentation
        valid_offers.sort(key=lambda x: x["price"])
        
        try:
            # Render decision prompt
            decision_messages = render_decision_prompt(
                buyer_name=room_state.buyer_name,
                constraints=room_state.buyer_constraints,
                valid_offers=valid_offers,
                conversation_history=room_state.conversation_history,
                current_round=room_state.current_round,
                min_rounds=min_rounds
            )
            
            # Ask buyer agent to decide - use model from room_state if available
            result = await self.provider.generate(
                messages=decision_messages,
                temperature=0.3,  # Slightly higher for decision-making
                max_tokens=100,
                stop=None,
                model=getattr(room_state, 'llm_model', None)  # Use model from session if available
            )
            
            decision_text = result.text.upper().strip()
            logger.info(f"Buyer decision response: {decision_text}")
            
            # Parse decision: look for "ACCEPT [SellerName]"
            if "ACCEPT" in decision_text:
                # Extract seller name from response
                for offer in valid_offers:
                    seller_name = offer["seller_name"].upper()
                    # Check if seller name appears in decision text
                    if seller_name in decision_text or offer["seller_id"] in decision_text:
                        logger.info(f"Buyer decided to accept offer from {offer['seller_name']}")
                        return {
                            "seller_id": offer["seller_id"],
                            "offer": offer["offer"],
                            "reason": f"Buyer accepted offer from {offer['seller_name']}: ${offer['price']:.2f} per unit"
                        }
                
                # If "ACCEPT" found but seller name unclear, accept first (best) offer
                logger.warning("ACCEPT found but seller name unclear, accepting best offer")
                best = valid_offers[0]
                return {
                    "seller_id": best["seller_id"],
                    "offer": best["offer"],
                    "reason": f"Buyer accepted offer: ${best['price']:.2f} per unit"
                }
            
            # If CONTINUE or KEEP NEGOTIATING, return None
            if "CONTINUE" in decision_text or "KEEP NEGOTIATING" in decision_text or "NEGOTIATING" in decision_text:
                logger.info("Buyer decided to continue negotiating")
                return None
            
            # Default: if unclear, continue (conservative)
            logger.info("Decision unclear, continuing negotiation")
            return None
            
        except Exception as e:
            logger.error(f"Error in buyer decision: {e}")
            # On error, continue negotiating (conservative)
            return None

