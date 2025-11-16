"""
ORM models for Phase 3 database persistence.

WHAT: SQLAlchemy models for all database tables
WHY: Persist sessions, negotiations, messages, offers, and outcomes
HOW: Declarative models with proper constraints, relationships, and indexes
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, CheckConstraint, UniqueConstraint, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


# Enums for status fields
class SessionStatus(str, enum.Enum):
    """Session status values."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


class NegotiationStatus(str, enum.Enum):
    """Negotiation run status values."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    NO_SELLERS_AVAILABLE = "no_sellers_available"
    ABORTED = "aborted"


class Session(Base):
    """
    Session table - top-level container for a negotiation episode.
    
    WHAT: Represents a single negotiation session with one buyer and multiple sellers
    WHY: Group related negotiations and track overall session lifecycle
    HOW: Primary key on session_id with CASCADE relationships
    """
    __tablename__ = "sessions"
    
    session_id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    buyer_id = Column(String(100), nullable=False)
    buyer_name = Column(String(100), nullable=False)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING)
    
    # Relationships
    buyers = relationship("Buyer", back_populates="session", cascade="all, delete-orphan")
    sellers = relationship("Seller", back_populates="session", cascade="all, delete-orphan")
    negotiation_runs = relationship("NegotiationRun", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(session_id={self.session_id}, buyer={self.buyer_name}, status={self.status})>"


class Buyer(Base):
    """
    Buyer table - stores buyer information for a session.
    
    WHAT: Buyer entity with constraints for items they want to purchase
    WHY: Track buyer details and link to their item requirements
    HOW: Foreign key to Session with CASCADE delete
    """
    __tablename__ = "buyers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    buyer_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="buyers")
    items = relationship("BuyerItem", back_populates="buyer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Buyer(id={self.id}, name={self.name})>"


class BuyerItem(Base):
    """
    BuyerItem table - items the buyer wants to purchase.
    
    WHAT: Individual items buyer is seeking with price and quantity constraints
    WHY: Track each item's requirements separately for multi-item negotiations
    HOW: Foreign key to Buyer with price/quantity CHECK constraints
    """
    __tablename__ = "buyer_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    buyer_db_id = Column(Integer, ForeignKey("buyers.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(100), nullable=False)
    item_name = Column(String(200), nullable=False)
    quantity_needed = Column(Integer, nullable=False)
    min_price_per_unit = Column(Float, nullable=False)
    max_price_per_unit = Column(Float, nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("quantity_needed >= 1", name="check_quantity_positive"),
        CheckConstraint("min_price_per_unit >= 0", name="check_min_price_non_negative"),
        CheckConstraint("max_price_per_unit > min_price_per_unit", name="check_max_greater_than_min"),
    )
    
    # Relationships
    buyer = relationship("Buyer", back_populates="items")
    
    def __repr__(self):
        return f"<BuyerItem(id={self.id}, item={self.item_name}, qty={self.quantity_needed})>"


class Seller(Base):
    """
    Seller table - stores seller information and profile.
    
    WHAT: Seller entity with behavioral profile (priority, speaking style)
    WHY: Track seller details and link to their inventory
    HOW: Foreign key to Session with CASCADE delete
    """
    __tablename__ = "sellers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)  # customer_retention or maximize_profit
    speaking_style = Column(String(50), nullable=False)  # rude or very_sweet
    
    # Relationships
    session = relationship("Session", back_populates="sellers")
    inventory = relationship("SellerInventory", back_populates="seller", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Seller(id={self.id}, name={self.name}, priority={self.priority})>"


class SellerInventory(Base):
    """
    SellerInventory table - items available from each seller.
    
    WHAT: Individual inventory items with pricing and availability
    WHY: Track what each seller has and their pricing constraints
    HOW: Foreign key to Seller with UNIQUE constraint on (seller, item) and price CHECKs
    """
    __tablename__ = "seller_inventory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_db_id = Column(Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(100), nullable=False)
    item_name = Column(String(200), nullable=False)
    cost_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    least_price = Column(Float, nullable=False)
    quantity_available = Column(Integer, nullable=False)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("seller_db_id", "item_id", name="unique_seller_item"),
        CheckConstraint("cost_price >= 0", name="check_cost_non_negative"),
        CheckConstraint("selling_price > cost_price", name="check_selling_greater_than_cost"),
        CheckConstraint("least_price >= cost_price", name="check_least_greater_than_cost"),
        CheckConstraint("least_price < selling_price", name="check_least_less_than_selling"),
        CheckConstraint("quantity_available >= 1", name="check_inventory_quantity_positive"),
    )
    
    # Relationships
    seller = relationship("Seller", back_populates="inventory")
    
    def __repr__(self):
        return f"<SellerInventory(id={self.id}, item={self.item_name}, qty={self.quantity_available})>"


class NegotiationRun(Base):
    """
    NegotiationRun table - individual negotiation for a specific item.
    
    WHAT: Represents one negotiation round for buyer purchasing one item type
    WHY: Track negotiation state, rounds, and outcome for each item
    HOW: Foreign key to Session with status tracking and timing
    """
    __tablename__ = "negotiation_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    room_id = Column(String(100), unique=True, nullable=False)
    item_id = Column(String(100), nullable=False)
    item_name = Column(String(200), nullable=False)
    status = Column(SQLEnum(NegotiationStatus), nullable=False, default=NegotiationStatus.PENDING)
    current_round = Column(Integer, nullable=False, default=0)
    max_rounds = Column(Integer, nullable=False, default=5)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    selected_seller_id = Column(String(100), nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    # Relationships
    session = relationship("Session", back_populates="negotiation_runs")
    participants = relationship("NegotiationParticipant", back_populates="negotiation_run", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="negotiation_run", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="negotiation_run", cascade="all, delete-orphan")
    outcome = relationship("NegotiationOutcome", back_populates="negotiation_run", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_negotiation_status", "status"),
        Index("idx_negotiation_session", "session_id"),
    )
    
    def __repr__(self):
        return f"<NegotiationRun(run_id={self.run_id}, item={self.item_name}, status={self.status})>"


class NegotiationParticipant(Base):
    """
    NegotiationParticipant table - sellers participating in a negotiation.
    
    WHAT: Links sellers to negotiation runs with participation status
    WHY: Track which sellers were invited and why some were skipped
    HOW: Foreign key to NegotiationRun with participation flag and skip reason
    """
    __tablename__ = "negotiation_participants"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    negotiation_run_id = Column(Integer, ForeignKey("negotiation_runs.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(String(100), nullable=False)
    seller_name = Column(String(100), nullable=False)
    participated = Column(Boolean, nullable=False, default=True)
    skip_reason = Column(String(200), nullable=True)
    
    # Relationships
    negotiation_run = relationship("NegotiationRun", back_populates="participants")
    
    def __repr__(self):
        return f"<NegotiationParticipant(seller={self.seller_name}, participated={self.participated})>"


class Message(Base):
    """
    Message table - conversation history for negotiations.
    
    WHAT: Individual messages exchanged during negotiation
    WHY: Track full conversation history with visibility control
    HOW: Foreign key to NegotiationRun with turn tracking and JSON fields
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid4()))
    negotiation_run_id = Column(Integer, ForeignKey("negotiation_runs.id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    sender_id = Column(String(100), nullable=False)
    sender_type = Column(String(20), nullable=False)  # buyer or seller
    sender_name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    mentioned_sellers = Column(JSON, nullable=True)  # List of seller IDs
    visibility = Column(JSON, nullable=True)  # List of agent IDs who can see this
    
    # Relationships
    negotiation_run = relationship("NegotiationRun", back_populates="messages")
    offer = relationship("Offer", back_populates="message", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_message_negotiation_turn", "negotiation_run_id", "turn_number"),
    )
    
    def __repr__(self):
        return f"<Message(id={self.message_id}, sender={self.sender_name}, turn={self.turn_number})>"


class Offer(Base):
    """
    Offer table - price/quantity offers made by sellers.
    
    WHAT: Specific offers attached to seller messages
    WHY: Track pricing negotiations and decision factors
    HOW: Foreign key to Message with price/quantity validation
    """
    __tablename__ = "offers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(36), ForeignKey("messages.message_id", ondelete="CASCADE"), unique=True, nullable=False)
    negotiation_run_id = Column(Integer, ForeignKey("negotiation_runs.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("price >= 0", name="check_offer_price_non_negative"),
        CheckConstraint("quantity >= 1", name="check_offer_quantity_positive"),
        Index("idx_offer_seller", "seller_id"),
    )
    
    # Relationships
    message = relationship("Message", back_populates="offer")
    negotiation_run = relationship("NegotiationRun", back_populates="offers")
    
    def __repr__(self):
        return f"<Offer(seller={self.seller_id}, price=${self.price}, qty={self.quantity})>"


class NegotiationOutcome(Base):
    """
    NegotiationOutcome table - final result and metrics for negotiation.
    
    WHAT: Aggregated outcome data and decision details
    WHY: Store final decision, metrics, and analytics for each negotiation
    HOW: One-to-one with NegotiationRun via unique FK
    """
    __tablename__ = "negotiation_outcomes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    negotiation_run_id = Column(Integer, ForeignKey("negotiation_runs.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String(50), nullable=False)  # completed, aborted, no_sellers_available
    selected_seller_id = Column(String(100), nullable=True)
    selected_seller_name = Column(String(100), nullable=True)
    final_price_per_unit = Column(Float, nullable=True)
    final_quantity = Column(Integer, nullable=True)
    final_total_cost = Column(Float, nullable=True)
    total_rounds = Column(Integer, nullable=False, default=0)
    total_messages = Column(Integer, nullable=False, default=0)
    total_offers = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=False, default=0.0)
    decision_reason = Column(Text, nullable=True)
    
    # Relationships
    negotiation_run = relationship("NegotiationRun", back_populates="outcome")
    
    def __repr__(self):
        return f"<NegotiationOutcome(run_id={self.negotiation_run_id}, status={self.status})>"

