"""
Negotiation graph builder - LangGraph-style orchestration.

WHAT: Async state machine for multi-round negotiations
WHY: Orchestrate buyer turns, parallel seller responses, and intelligent decision logic
HOW: Async generator with nodes: BuyerTurn → Routing → ParallelSellers → DecisionCheck → BuyerDecision → complete
     Flow: Analyze offers with decision engine, then use LLM for final selection
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
from ..services.decision_engine import analyze_offers, select_best_offer, generate_decision_reason
from ..agents.prompts import render_buyer_decision_prompt
from ..core.config import settings
from ..utils.logger import get_logger
import re

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
        # Use slightly higher temperature (0.15) to prevent deterministic pattern completion
        # This adds randomness while maintaining consistency
        self.temperature = max(0.15, settings.LLM_DEFAULT_TEMPERATURE)
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
                        # Get seller name
                        seller_name = next(
                            (s.name for s in room_state.sellers if s.seller_id == seller_id),
                            "Unknown Seller"
                        )
                        
                        yield {
                            "type": "seller_response",
                            "data": {
                                "seller_id": seller_id,
                                "seller_name": seller_name,
                                "message": result["message"],
                                "updated_offer": result.get("offer"),  # Frontend expects "updated_offer"
                                "round": room_state.current_round
                            },
                            "timestamp": datetime.now()
                        }
                
                # Node 4: Decision Check (analyze offers)
                decision_check = self._decision_check_node(room_state, seller_results)
                
                # Determine if buyer should make a decision
                # Smart decision logic: decide early if exceptional offer, otherwise wait until final round
                is_last_round = room_state.current_round >= self.max_rounds
                should_decide_early = self._should_make_decision(room_state, decision_check)
                
                if is_last_round or should_decide_early:
                    # Node 5: Buyer Decision (LLM-based selection)
                    # Always make a decision on the last round, even if no valid offers
                    has_valid_offers = decision_check and decision_check.get("valid_offers")
                    
                    if has_valid_offers:
                        valid_offers = decision_check["valid_offers"]
                        buyer_decision = await self._buyer_decision_node(room_state, valid_offers)
                        
                        if buyer_decision:
                            room_state.status = "completed"
                            room_state.selected_seller_id = buyer_decision["seller_id"]
                            room_state.final_offer = buyer_decision["offer"]
                            room_state.decision_reason = buyer_decision.get("reason", "Best offer selected")
                            
                            # Get seller name
                            seller_name = next(
                                (s.name for s in room_state.sellers if s.seller_id == buyer_decision["seller_id"]),
                                "Unknown Seller"
                            )
                            
                            yield {
                                "type": "negotiation_complete",
                                "data": {
                                    "selected_seller": buyer_decision["seller_id"],  # Frontend expects "selected_seller"
                                    "seller_name": seller_name,
                                    "final_price": buyer_decision["offer"].get("price"),
                                    "quantity": buyer_decision["offer"].get("quantity"),
                                    "reason": buyer_decision.get("reason"),
                                    "rounds": room_state.current_round
                                },
                                "timestamp": datetime.now()
                            }
                            break
                    
                    # No valid offers on final round - still complete negotiation
                    logger.warning(f"Max rounds reached ({self.max_rounds}) with no valid offers")
                    room_state.status = "aborted"
                    yield {
                        "type": "negotiation_complete",
                        "data": {
                            "selected_seller": None,  # Frontend expects "selected_seller"
                            "seller_name": None,
                            "final_price": None,
                            "quantity": None,
                            "reason": "No valid offers received after maximum negotiation rounds",
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
            
            # This should not be reached as decision is always made on last round
            # Kept as safety fallback
            if room_state.status != "completed" and room_state.status != "aborted":
                logger.error("Negotiation ended unexpectedly without decision or abort")
                room_state.status = "aborted"
                yield {
                    "type": "negotiation_complete",
                    "data": {
                        "selected_seller": None,  # Frontend expects "selected_seller"
                        "seller_name": None,
                        "final_price": None,
                        "quantity": None,
                        "reason": "Negotiation ended unexpectedly",
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
                    # Find matching inventory item by name (case-insensitive)
                    inventory_item = None
                    item_name_lower = room_state.buyer_constraints.item_name.lower().strip()
                    for item in seller.inventory:
                        if item.item_name.lower().strip() == item_name_lower:
                            inventory_item = item
                            break
                    
                    if not inventory_item:
                        logger.warning(f"Seller {seller.name} has no inventory for item {room_state.buyer_constraints.item_name}")
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
                    
                    # Track offer (Phase 2)
                    if result.get("offer"):
                        if seller.seller_id not in room_state.offers_by_seller:
                            room_state.offers_by_seller[seller.seller_id] = []
                        
                        offer_with_round = dict(result["offer"])
                        offer_with_round["round"] = room_state.current_round
                        room_state.offers_by_seller[seller.seller_id].append(offer_with_round)
                        
                        # Track first offer round
                        if room_state.first_offer_round is None:
                            room_state.first_offer_round = room_state.current_round
                    
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
        Decision check node - analyze offers using decision engine.
        
        WHAT: Analyze offers with multi-factor scoring
        WHY: Determine if any valid offers exist for buyer to choose from
        HOW: Use decision engine to analyze and score offers
        
        Args:
            room_state: Current room state
            seller_results: Dict of seller_id -> response dict
            
        Returns:
            Dict with "valid_offers" (list of OfferAnalysis) or None if no valid offers
        """
        # Use decision engine to analyze offers
        try:
            offer_analyses = analyze_offers(room_state, seller_results)
            
            if offer_analyses:
                logger.info(f"Found {len(offer_analyses)} valid offers for decision")
                return {
                    "valid_offers": offer_analyses
                }
            else:
                logger.info("No valid offers yet, continuing negotiation")
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing offers: {e}")
            return None
    
    async def _buyer_decision_node(
        self,
        room_state: NegotiationRoomState,
        valid_offers: list
    ) -> Optional[dict]:
        """
        Buyer decision node - use LLM to select best offer.
        
        WHAT: Ask buyer LLM to make intelligent offer selection
        WHY: More realistic decision making considering soft factors
        HOW: Create decision prompt with offer table, get LLM selection, validate
        
        Args:
            room_state: Current room state
            valid_offers: List of OfferAnalysis objects
            
        Returns:
            Decision dict with seller_id, offer, and reason, or None if decision fails
        """
        if not valid_offers:
            return None
        
        try:
            # Create decision prompt
            decision_prompt = render_buyer_decision_prompt(
                buyer_name=room_state.buyer_name,
                constraints=room_state.buyer_constraints,
                offers=valid_offers,
                conversation_history=room_state.conversation_history
            )
            
            # Get LLM decision
            logger.info(f"Asking buyer LLM to decide from {len(valid_offers)} offers")
            result = await self.provider.generate(
                messages=decision_prompt,
                temperature=0.0,  # Deterministic
                max_tokens=128,
                stop=None
            )
            
            # Parse decision from response
            selected_seller_id = self._parse_decision(result.text, valid_offers)
            
            if not selected_seller_id:
                # Fallback to best scored offer if LLM doesn't make clear decision
                logger.warning("LLM decision unclear, using highest scored offer")
                best_analysis = select_best_offer(valid_offers, room_state.buyer_constraints)
                if best_analysis:
                    selected_seller_id = best_analysis.seller_id
                else:
                    return None
            
            # Find the selected offer analysis
            selected_analysis = None
            for analysis in valid_offers:
                if analysis.seller_id == selected_seller_id:
                    selected_analysis = analysis
                    break
            
            if not selected_analysis:
                logger.error(f"Selected seller {selected_seller_id} not found in valid offers")
                return None
            
            # Generate decision reason
            reason = generate_decision_reason(selected_analysis)
            
            logger.info(f"Buyer decided: {reason}")
            
            return {
                "seller_id": selected_analysis.seller_id,
                "offer": selected_analysis.offer,
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Buyer decision node error: {e}")
            # Fallback to best scored offer
            best_analysis = select_best_offer(valid_offers, room_state.buyer_constraints)
            if best_analysis:
                return {
                    "seller_id": best_analysis.seller_id,
                    "offer": best_analysis.offer,
                    "reason": generate_decision_reason(best_analysis)
                }
            return None
    
    def _should_make_decision(
        self,
        room_state: NegotiationRoomState,
        decision_check: Optional[dict]
    ) -> bool:
        """
        Determine if buyer should make an early decision.
        
        WHAT: Smart logic to decide before final round if conditions are right
        WHY: Allow buyer to accept exceptional offers early
        HOW: Check minimum rounds, exceptional offer scores, or multiple good offers
        
        Args:
            room_state: Current negotiation state
            decision_check: Result from decision_check_node with valid_offers
            
        Returns:
            True if buyer should make decision now, False to continue negotiating
        """
        # Must have at least completed minimum rounds (allow negotiation)
        MIN_ROUNDS = 3
        if room_state.current_round < MIN_ROUNDS:
            return False
        
        # No valid offers yet - continue negotiating
        if not decision_check or not decision_check.get("valid_offers"):
            return False
        
        valid_offers = decision_check["valid_offers"]
        
        # Check for exceptional offer (score > 85/100)
        EXCEPTIONAL_SCORE_THRESHOLD = 85.0
        best_score = max(offer.total_score for offer in valid_offers)
        
        if best_score >= EXCEPTIONAL_SCORE_THRESHOLD:
            logger.info(
                f"Early decision triggered: exceptional offer with score {best_score:.1f}/100 "
                f"at round {room_state.current_round}"
            )
            return True
        
        # Check for multiple good offers (competitive marketplace)
        # If we have 2+ offers with score > 70, buyer can choose
        GOOD_SCORE_THRESHOLD = 70.0
        good_offers = [o for o in valid_offers if o.total_score >= GOOD_SCORE_THRESHOLD]
        
        if len(good_offers) >= 2 and room_state.current_round >= 5:
            logger.info(
                f"Early decision triggered: {len(good_offers)} competitive offers "
                f"at round {room_state.current_round}"
            )
            return True
        
        # Otherwise, continue negotiating
        return False
    
    def _parse_decision(self, text: str, valid_offers: list) -> Optional[str]:
        """
        Parse buyer's decision from LLM response.
        
        WHAT: Extract seller mention from decision text
        WHY: LLM response needs parsing to find selected seller
        HOW: Look for "DECISION: @SellerName" pattern or @mentions
        
        Args:
            text: LLM response text
            valid_offers: List of OfferAnalysis to match against
            
        Returns:
            seller_id of selected seller, or None if unclear
        """
        if not text:
            return None
        
        # Create map of seller names to IDs
        seller_map = {analysis.seller_name.lower(): analysis.seller_id for analysis in valid_offers}
        
        # First try to find "DECISION: @SellerName" pattern
        decision_pattern = r'DECISION:\s*@(\w+)'
        match = re.search(decision_pattern, text, re.IGNORECASE)
        if match:
            seller_name = match.group(1).lower()
            if seller_name in seller_map:
                logger.info(f"Parsed decision: @{seller_name}")
                return seller_map[seller_name]
        
        # Fallback: look for any @mention in the response
        mention_pattern = r'@(\w+)'
        mentions = re.findall(mention_pattern, text)
        for mention in mentions:
            mention_lower = mention.lower()
            if mention_lower in seller_map:
                logger.info(f"Found mention in decision: @{mention}")
                return seller_map[mention_lower]
        
        # No clear decision found
        logger.warning(f"Could not parse decision from: {text[:100]}")
        return None

