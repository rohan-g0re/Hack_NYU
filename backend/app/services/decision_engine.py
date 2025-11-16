"""
Decision engine for analyzing and selecting offers.

WHAT: Multi-factor offer analysis and intelligent selection
WHY: Buyer needs to make informed decisions beyond just price
HOW: Score offers on price, responsiveness, rounds, and seller profile
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from ..models.agent import Seller, BuyerConstraints
from ..models.message import Offer
from ..models.negotiation import NegotiationRoomState
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OfferAnalysis:
    """Analyzed offer with scoring metrics."""
    seller_id: str
    seller_name: str
    offer: Offer
    price_score: float  # 0-100, lower price = higher score
    responsiveness_score: float  # Based on response time/round
    negotiation_rounds: int
    seller_priority: str  # customer_retention or maximize_profit
    profile_score: float  # Bonus for customer_retention sellers
    total_score: float


def analyze_offers(
    room_state: NegotiationRoomState,
    seller_results: Dict[str, dict]
) -> List[OfferAnalysis]:
    """
    Analyze all offers with multi-factor scoring.
    
    WHAT: Calculate scores for each offer based on multiple factors
    WHY: Enable intelligent decision making beyond just price
    HOW: Apply weighted scoring algorithm across 4 dimensions
    
    Scoring Breakdown:
    - Price (40%): Lower price within budget = higher score
    - Responsiveness (30%): Earlier responders score higher  
    - Rounds (20%): Fewer rounds to first offer = better
    - Profile (10%): customer_retention sellers get bonus
    
    Args:
        room_state: Current negotiation state
        seller_results: Dict of seller_id -> response with offer
        
    Returns:
        List of OfferAnalysis objects, sorted by total_score descending
    """
    analyses = []
    
    buyer_constraints = room_state.buyer_constraints
    current_round = room_state.current_round
    
    # Get all sellers map for quick lookup
    sellers_map = {s.seller_id: s for s in room_state.sellers}
    
    for seller_id, result in seller_results.items():
        if not result:
            continue
            
        offer = result.get("offer")
        if not offer:
            continue
            
        seller = sellers_map.get(seller_id)
        if not seller:
            continue
            
        price = offer.get("price", 0)
        quantity = offer.get("quantity", 0)
        
        # Validate offer is within buyer constraints (with 10% flexibility on max price)
        # Allow buyer to stretch budget slightly for good offers
        max_price_flexible = buyer_constraints.max_price_per_unit * 1.1
        
        if price < buyer_constraints.min_price_per_unit:
            logger.debug(f"Offer from {seller.name} below minimum price: ${price}")
            continue
            
        if price > max_price_flexible:
            logger.debug(
                f"Offer from {seller.name} above flexible price limit: ${price} "
                f"(max: ${buyer_constraints.max_price_per_unit}, flexible: ${max_price_flexible:.2f})"
            )
            continue
        
        # Log if using flexible pricing
        if price > buyer_constraints.max_price_per_unit:
            logger.info(
                f"Accepting offer from {seller.name} with flexible pricing: ${price:.2f} "
                f"(+{((price/buyer_constraints.max_price_per_unit - 1) * 100):.1f}% over budget)"
            )
            
        if quantity < buyer_constraints.quantity_needed:
            logger.debug(f"Offer from {seller.name} insufficient quantity: {quantity}")
            continue
        
        # Calculate price score (40 points max)
        # Lower price = higher score
        price_range = buyer_constraints.max_price_per_unit - buyer_constraints.min_price_per_unit
        if price_range > 0:
            price_score = 40.0 * (buyer_constraints.max_price_per_unit - price) / price_range
        else:
            # If min == max, any valid price gets full score
            price_score = 40.0
        
        # Calculate responsiveness score (30 points max)
        # Responded in earlier rounds = higher score
        # Normalize based on current_round
        if current_round > 0:
            # First round gets full score, later rounds get less
            responsiveness_score = 30.0 * (1.0 - (current_round - 1) / max(current_round, room_state.max_rounds))
        else:
            responsiveness_score = 30.0
        
        # Calculate negotiation rounds score (20 points max)  
        # Check how many rounds it took to get offer from this seller
        seller_offer_round = current_round
        if hasattr(room_state, 'offers_by_seller') and seller_id in room_state.offers_by_seller:
            # Find first offer round
            seller_offer_round = getattr(room_state, 'first_offer_round', current_round) or current_round
        
        if room_state.max_rounds > 0:
            rounds_score = 20.0 * (1.0 - (seller_offer_round - 1) / room_state.max_rounds)
        else:
            rounds_score = 20.0
        
        # Calculate profile score (10 points max)
        # customer_retention sellers get bonus for being buyer-friendly
        if seller.profile.priority == "customer_retention":
            profile_score = 10.0
        else:
            profile_score = 0.0
        
        # Total score
        total_score = price_score + responsiveness_score + rounds_score + profile_score
        
        analysis = OfferAnalysis(
            seller_id=seller_id,
            seller_name=seller.name,
            offer=offer,
            price_score=price_score,
            responsiveness_score=responsiveness_score,
            negotiation_rounds=seller_offer_round,
            seller_priority=seller.profile.priority,
            profile_score=profile_score,
            total_score=total_score
        )
        
        analyses.append(analysis)
        
        logger.info(
            f"Analyzed offer from {seller.name}: "
            f"price=${price:.2f} (score: {price_score:.1f}), "
            f"round={seller_offer_round} (resp: {responsiveness_score:.1f}, rounds: {rounds_score:.1f}), "
            f"profile={seller.profile.priority} (score: {profile_score:.1f}), "
            f"TOTAL: {total_score:.1f}/100"
        )
    
    # Sort by total score descending (best first)
    analyses.sort(key=lambda x: x.total_score, reverse=True)
    
    return analyses


def select_best_offer(
    analyses: List[OfferAnalysis],
    buyer_constraints: BuyerConstraints
) -> Optional[OfferAnalysis]:
    """
    Select the best offer from analyzed offers.
    
    WHAT: Apply tie-breakers and select highest-scored offer
    WHY: Need deterministic selection when multiple good offers
    HOW: Use total_score, with price as tie-breaker
    
    Args:
        analyses: List of analyzed offers (already scored)
        buyer_constraints: Buyer's constraints for validation
        
    Returns:
        Best OfferAnalysis or None if no valid offers
    """
    if not analyses:
        return None
    
    # Filter to valid offers only (redundant check but safe)
    # Apply same 10% flexibility on max price
    max_price_flexible = buyer_constraints.max_price_per_unit * 1.1
    valid_analyses = [
        a for a in analyses
        if (buyer_constraints.min_price_per_unit <= a.offer["price"] <= max_price_flexible
            and a.offer["quantity"] >= buyer_constraints.quantity_needed)
    ]
    
    if not valid_analyses:
        logger.warning("No valid offers after filtering")
        return None
    
    # Already sorted by total_score, so first is best
    best = valid_analyses[0]
    
    # Log if there are close competitors
    if len(valid_analyses) > 1:
        second_best = valid_analyses[1]
        score_diff = best.total_score - second_best.total_score
        if score_diff < 5.0:  # Within 5 points
            logger.info(
                f"Close decision: {best.seller_name} (score: {best.total_score:.1f}) "
                f"vs {second_best.seller_name} (score: {second_best.total_score:.1f}), "
                f"diff: {score_diff:.1f}"
            )
    
    logger.info(f"Selected best offer: {best.seller_name} with score {best.total_score:.1f}/100")
    
    return best


def generate_decision_reason(analysis: OfferAnalysis) -> str:
    """
    Generate human-readable decision explanation.
    
    WHAT: Create explanation for why this offer was selected
    WHY: Transparency and auditability of decision
    HOW: Summarize key factors from analysis
    
    Args:
        analysis: The selected offer analysis
        
    Returns:
        Human-readable decision reason
    """
    price = analysis.offer["price"]
    quantity = analysis.offer["quantity"]
    
    reason_parts = [
        f"Selected {analysis.seller_name}",
        f"${price:.2f}/unit for {quantity} units (total: ${price * quantity:.2f})",
        f"Score: {analysis.total_score:.1f}/100"
    ]
    
    # Add breakdown
    breakdown = []
    if analysis.price_score > 35:  # High price score
        breakdown.append(f"competitive price ({analysis.price_score:.0f}/40)")
    if analysis.responsiveness_score > 25:  # High responsiveness
        breakdown.append(f"quick response ({analysis.responsiveness_score:.0f}/30)")
    if analysis.negotiation_rounds <= 2:
        breakdown.append(f"early offer (round {analysis.negotiation_rounds})")
    if analysis.profile_score > 0:
        breakdown.append(f"{analysis.seller_priority} seller (+{analysis.profile_score:.0f})")
    
    if breakdown:
        reason_parts.append(f"[{', '.join(breakdown)}]")
    
    return " - ".join(reason_parts)

