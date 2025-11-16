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
from ..core.session_manager import session_manager
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
                
                # Emit raw response for debugging
                yield {
                    "type": "debug_raw",
                    "data": {
                        "agent_type": "buyer",
                        "agent_name": room_state.buyer_name,
                        "raw_response": buyer_result.get("raw_response", ""),
                        "sanitized_message": buyer_result["message"],
                        "round": room_state.current_round
                    },
                    "timestamp": datetime.now()
                }
                
                yield {
                    "type": "buyer_message",
                    "data": {
                        "sender_type": "buyer",
                        "sender_id": room_state.buyer_id,
                        "sender_name": room_state.buyer_name,
                        "message": buyer_result["message"],
                        "content": buyer_result["message"],  # Alias for compatibility
                        "mentioned_sellers": buyer_result["mentioned_sellers"],
                        "turn_number": room_state.current_round,
                        "round": room_state.current_round
                    },
                    "timestamp": datetime.now()
                }
                
                # Node 2: Message Routing (determine which sellers respond)
                logger.warning("[BUYER_MENTIONS] %s", buyer_result["mentioned_sellers"])
                logger.warning("[ALL_SELLERS] %s", [(s.seller_id, s.name) for s in room_state.sellers])
                
                responding_sellers = self._message_routing_node(
                    buyer_result["mentioned_sellers"],
                    room_state.sellers
                )
                
                logger.warning("[RESPONDING_SELLERS] %s", [(s.seller_id, s.name) for s in responding_sellers])
                
                if not responding_sellers:
                    logger.warning("[NO_SELLERS] No sellers to respond, ending negotiation")
                    break
                
                # Node 3: Parallel Seller Responses
                seller_results = await self._parallel_seller_responses_node(
                    room_state,
                    responding_sellers
                )
                
                # Emit seller responses
                logger.warning("[SELLER_RESULTS] %s", seller_results)
                for seller_id, result in seller_results.items():
                    seller_name = next(
                        (s.name for s in room_state.sellers if s.seller_id == seller_id),
                        "Unknown Seller"
                    )
                    
                    if not result:
                        logger.error("[SELLER_EMPTY_RESULT] %s (%s) returned None/empty result - no response emitted", seller_name, seller_id)
                        error_message = f"⚠️ {seller_name} could not respond this round (internal error)."
                        raw_response = f"ERROR: Seller {seller_name} returned None/empty result. Check backend logs for details."
                        
                        yield {
                            "type": "debug_raw",
                            "data": {
                                "agent_type": "seller",
                                "agent_name": seller_name,
                                "raw_response": raw_response,
                                "sanitized_message": error_message,
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                        
                        yield {
                            "type": "seller_response",
                            "data": {
                                "sender_type": "seller",
                                "sender_id": seller_id,
                                "seller_id": seller_id,
                                "sender_name": seller_name,
                                "seller_name": seller_name,
                                "message": error_message,
                                "content": error_message,  # Alias for compatibility
                                "offer": None,
                                "turn_number": room_state.current_round,
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                        continue
                    
                    if result.get("error"):
                        error_message = result.get("message") or f"⚠️ {seller_name} could not respond this round."
                        
                        yield {
                            "type": "debug_raw",
                            "data": {
                                "agent_type": "seller",
                                "agent_name": seller_name,
                                "raw_response": result.get("raw_response", ""),
                                "sanitized_message": error_message,
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                        
                        yield {
                            "type": "seller_response",
                            "data": {
                                "sender_type": "seller",
                                "sender_id": seller_id,
                                "seller_id": seller_id,
                                "sender_name": seller_name,
                                "seller_name": seller_name,
                                "message": error_message,
                                "content": error_message,  # Alias for compatibility
                                "offer": None,
                                "turn_number": room_state.current_round,
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                        continue
                    
                    # Normal response - emit raw and seller_response events
                    yield {
                        "type": "debug_raw",
                        "data": {
                            "agent_type": "seller",
                            "agent_name": seller_name,
                            "raw_response": result.get("raw_response", ""),
                            "sanitized_message": result["message"],
                            "round": room_state.current_round
                        },
                        "timestamp": datetime.now()
                    }
                    
                    yield {
                        "type": "seller_response",
                        "data": {
                            "sender_type": "seller",
                            "sender_id": seller_id,
                            "seller_id": seller_id,
                            "sender_name": seller_name,
                            "seller_name": seller_name,
                            "message": result["message"],
                            "content": result["message"],  # Alias for compatibility
                            "offer": result.get("offer"),
                            "turn_number": room_state.current_round,
                            "round": room_state.current_round
                        },
                        "timestamp": datetime.now()
                    }
                
                has_valid_seller = any(
                    result and not result.get("error")
                    for result in seller_results.values()
                )
                
                if not has_valid_seller:
                    room_state.status = "aborted"
                    yield {
                        "type": "negotiation_complete",
                        "data": {
                            "selected_seller_id": None,
                            "selected_seller_name": None,
                            "final_offer": None,
                            "reason": "No sellers could respond",
                            "rounds": room_state.current_round
                        },
                        "timestamp": datetime.now()
                    }
                    break
                
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
            
            logger.info(f"Running buyer turn for round {room_state.current_round}")
            result = await buyer_agent.run_turn(room_state)
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
                    # Find matching inventory item BY NAME (case-insensitive)
                    inventory_item = None
                    buyer_item_name = room_state.buyer_constraints.item_name.lower().strip()
                    for item in seller.inventory:
                        if item.item_name.lower().strip() == buyer_item_name:
                            inventory_item = item
                            break
                    
                    if not inventory_item:
                        logger.error("[SELLER_NO_INVENTORY] %s has no inventory matching '%s'", seller.name, buyer_item_name)
                        logger.error("   Buyer wants: '%s'", buyer_item_name)
                        logger.error("   Seller %s inventory: %s", seller.name, [(i.item_name.lower().strip(), i.item_name) for i in seller.inventory])
                        logger.error("   Seller %s inventory count: %s", seller.name, len(seller.inventory))
                        # Return error dict instead of None so we can emit debug event
                        return {
                            "error": "no_inventory_match",
                            "message": f"⚠️ Seller {seller.name} has no matching inventory",
                            "raw_response": f"ERROR: Seller {seller.name} has no inventory matching '{buyer_item_name}'. Available: {[i.item_name for i in seller.inventory]}",
                            "offer": None
                        }
                    
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
                    
                    logger.warning("[CALL_SELLER] %s", seller.name)
                    result = await seller_agent.respond(
                        temp_state,
                        room_state.buyer_name,
                        room_state.buyer_constraints
                    )
                    logger.warning("[SELLER_RETURNED] %s", {"seller": seller.name, "result": result})
                    
                    # Persist seller message to database
                    if result and result.get("message"):
                        db_message = session_manager.record_message(
                            run_id=room_state.room_id,
                            turn_number=room_state.current_round,
                            sender_type="seller",
                            sender_id=seller.seller_id,
                            sender_name=seller.name,
                            message_text=result["message"],
                            mentioned_agents=[]
                        )
                        
                        # Persist offer if present
                        offer = result.get("offer")
                        if offer and db_message:
                            session_manager.record_offer(
                                message_id=db_message.id,
                                seller_id=seller.seller_id,
                                price_per_unit=offer.get("price", 0),
                                quantity=offer.get("quantity", 0),
                                conditions=None
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
            
            # Ask buyer agent to decide
            result = await self.provider.generate(
                messages=decision_messages,
                temperature=0.3,  # Slightly higher for decision-making
                max_tokens=100,
                stop=None
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

