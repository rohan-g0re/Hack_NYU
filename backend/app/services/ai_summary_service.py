"""
AI Summary Service for generating negotiation summaries.

WHAT: Generate AI-powered summaries of negotiations using OpenRouter
WHY: Provide insights and highlights for completed negotiations
HOW: Fetch conversation history and use LLM to generate narratives and analysis
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import json

from ..core.models import NegotiationRun, Message, Offer, BuyerItem, Seller
from ..llm.provider_factory import get_provider
from ..llm.types import ChatMessage, ProviderResponseError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AISummaryService:
    """Service for generating AI summaries of negotiations."""
    
    def __init__(self):
        """Initialize the AI summary service."""
        self.provider = None
        try:
            # Always use OpenRouter for summaries
            self.provider = get_provider("openrouter")
            logger.info("AI Summary Service initialized with OpenRouter")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter for summaries: {e}")
    
    def _build_conversation_context(
        self,
        db: Session,
        run_id: str
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Build conversation context for AI summarization.
        
        Args:
            db: Database session
            run_id: Negotiation run ID
            
        Returns:
            Tuple of (conversation_text, metadata)
        """
        run = db.query(NegotiationRun).filter(NegotiationRun.id == run_id).first()
        if not run:
            return None, None
        
        buyer_item = db.query(BuyerItem).filter(BuyerItem.id == run.buyer_item_id).first()
        if not buyer_item:
            return None, None
        
        # Get all messages in order
        messages = db.query(Message).filter(
            Message.negotiation_run_id == run_id
        ).order_by(Message.turn_number).all()
        
        # Get all offers
        offers = db.query(Offer).join(Message).filter(
            Message.negotiation_run_id == run_id
        ).all()
        
        # Build offer map
        offer_map = {offer.message_id: offer for offer in offers}
        
        # Build conversation text
        conversation_lines = []
        conversation_lines.append(f"Item: {buyer_item.item_name}")
        conversation_lines.append(f"Quantity needed: {buyer_item.quantity_needed}")
        conversation_lines.append(f"Price range: ${buyer_item.min_price_per_unit:.2f} - ${buyer_item.max_price_per_unit:.2f} per unit")
        conversation_lines.append(f"Negotiation rounds: {run.current_round}")
        conversation_lines.append(f"Status: {run.status}")
        conversation_lines.append("\nConversation:\n")
        
        for msg in messages:
            sender_label = f"{msg.sender_name} ({msg.sender_type})"
            conversation_lines.append(f"[Round {msg.turn_number}] {sender_label}: {msg.message_text}")
            
            # Add offer details if present
            if msg.id in offer_map:
                offer = offer_map[msg.id]
                conversation_lines.append(
                    f"  → Offer: ${offer.price_per_unit:.2f}/unit for {offer.quantity} units "
                    f"(Total: ${offer.price_per_unit * offer.quantity:.2f})"
                )
        
        conversation_text = "\n".join(conversation_lines)
        
        # Build metadata
        metadata = {
            "item_name": buyer_item.item_name,
            "quantity": buyer_item.quantity_needed,
            "min_price": buyer_item.min_price_per_unit,
            "max_price": buyer_item.max_price_per_unit,
            "rounds": run.current_round,
            "status": run.status,
            "message_count": len(messages),
            "offer_count": len(offers)
        }
        
        return conversation_text, metadata
    
    async def generate_item_summary(
        self,
        db: Session,
        run_id: str
    ) -> Optional[Dict]:
        """
        Generate AI summary for a single negotiation.
        
        Args:
            db: Database session
            run_id: Negotiation run ID
            
        Returns:
            Dict with narrative and highlights, or None if failed
        """
        if not self.provider:
            logger.warning("OpenRouter not available for summary generation")
            return None
        
        try:
            conversation_text, metadata = self._build_conversation_context(db, run_id)
            if not conversation_text:
                logger.warning(f"Could not build conversation context for run {run_id}")
                return None
            
            # Create prompt for item summary
            prompt = f"""Analyze this negotiation conversation and provide a detailed summary.

{conversation_text}

Please provide your response in the following JSON format:
{{
  "narrative": "A 2-3 sentence summary of how the negotiation went and who won",
  "buyer_analysis": {{
    "what_went_well": "What the buyer did well in this negotiation",
    "what_to_improve": "What the buyer could have done better"
  }},
  "seller_analysis": {{
    "what_went_well": "What the seller did well in this negotiation",
    "what_to_improve": "What the seller could have done better"
  }},
  "highlights": {{
    "best_offer": "The best offer received (e.g., '$X.XX per unit from SellerName')",
    "turning_points": ["List of 1-3 key moments that changed the negotiation"],
    "tactics_used": ["List of 2-4 negotiation tactics employed by buyer or sellers"]
  }},
  "deal_winner": "Either 'buyer', 'seller', or 'balanced' - who got the better deal and why (1 sentence)"
}}

Focus on the negotiation dynamics, what each party did well and poorly, and who came out ahead."""

            messages = [
                ChatMessage(role="system", content="You are an expert negotiation analyst. Provide concise, insightful summaries in valid JSON format."),
                ChatMessage(role="user", content=prompt)
            ]
            
            # Call OpenRouter
            result = await self.provider.generate(
                messages=messages,
                model=None,  # Use default model
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse JSON response
            response_text = result.text.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            summary_data = json.loads(response_text)
            
            logger.info(f"Generated AI summary for run {run_id}")
            return summary_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI summary: {e}")
            logger.error(f"Response was: {result.text if 'result' in locals() else 'No response'}")
            return None
        except Exception as e:
            logger.error(f"Error generating item summary: {e}")
            return None
    
    async def generate_overall_analysis(
        self,
        db: Session,
        session_id: str,
        purchase_summaries: List[Dict]
    ) -> Optional[Dict]:
        """
        Generate overall analysis for all negotiations in a session.
        
        Args:
            db: Database session
            session_id: Session ID
            purchase_summaries: List of purchase summary dicts with AI summaries
            
        Returns:
            Dict with performance insights, comparison, and recommendations
        """
        if not self.provider:
            logger.warning("OpenRouter not available for overall analysis")
            return None
        
        try:
            # Build context from all purchases
            context_lines = []
            context_lines.append(f"Session Analysis - {len(purchase_summaries)} negotiations completed\n")
            
            for i, purchase in enumerate(purchase_summaries, 1):
                context_lines.append(f"\nNegotiation {i}: {purchase['item_name']}")
                context_lines.append(f"  Seller: {purchase['selected_seller']}")
                context_lines.append(f"  Final Price: ${purchase['final_price_per_unit']:.2f}/unit")
                context_lines.append(f"  Total Cost: ${purchase['total_cost']:.2f}")
                context_lines.append(f"  Rounds: {purchase['negotiation_rounds']}")
                
                # Check if ai_summary exists (could be dict or Pydantic model)
                ai_sum = purchase.get('ai_summary')
                if ai_sum:
                    # Handle both dict and Pydantic model formats
                    if hasattr(ai_sum, 'narrative'):
                        context_lines.append(f"  Summary: {ai_sum.narrative}")
                    elif isinstance(ai_sum, dict):
                        context_lines.append(f"  Summary: {ai_sum.get('narrative', 'N/A')}")
            
            context_text = "\n".join(context_lines)
            
            prompt = f"""Analyze this buyer's overall negotiation performance across multiple items:

{context_text}

Provide a comprehensive analysis in the following JSON format:
{{
  "performance_insights": "2-3 sentences analyzing the buyer's overall negotiation performance and effectiveness",
  "cross_item_comparison": "2-3 sentences comparing how negotiations differed across items (which went well, which didn't, patterns observed)",
  "recommendations": ["3-5 specific, actionable recommendations for future negotiations"]
}}

Focus on strategy effectiveness, patterns, and practical advice."""

            messages = [
                ChatMessage(role="system", content="You are an expert negotiation coach providing strategic analysis and advice. Provide responses in valid JSON format."),
                ChatMessage(role="user", content=prompt)
            ]
            
            result = await self.provider.generate(
                messages=messages,
                model=None,
                temperature=0.7,
                max_tokens=1200
            )
            
            response_text = result.text.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            analysis_data = json.loads(response_text)
            
            logger.info(f"Generated overall analysis for session {session_id}")
            return analysis_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from overall analysis: {e}")
            logger.error(f"Response was: {result.text if 'result' in locals() else 'No response'}")
            return None
        except Exception as e:
            logger.error(f"Error generating overall analysis: {e}")
            return None


# Singleton instance
ai_summary_service = AISummaryService()

