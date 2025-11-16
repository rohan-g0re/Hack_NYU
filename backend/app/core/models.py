"""
SQLAlchemy ORM models for Phase 3.

WHAT: Database schema definitions for sessions, buyers, sellers, negotiations
WHY: Persist all negotiation data with proper constraints and relationships
HOW: SQLAlchemy v2 declarative models with CHECK constraints, FKs, indexes
"""

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, 
    CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from .database import Base


class Session(Base):
    """Session table - represents a configured marketplace episode."""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    status = Column(
        String(20),
        CheckConstraint("status IN ('draft', 'active', 'completed')"),
        default='draft',
        nullable=False
    )
    llm_model = Column(String(100), nullable=False)
    llm_temperature = Column(Float, default=0.7, nullable=False)
    llm_max_tokens = Column(Integer, default=500, nullable=False)
    llm_provider = Column(String(20), default='lm_studio', nullable=False)  # 'lm_studio' or 'openrouter'
    
    # Relationships
    buyers = relationship("Buyer", back_populates="session", cascade="all, delete-orphan")
    sellers = relationship("Seller", back_populates="session", cascade="all, delete-orphan")
    negotiation_runs = relationship("NegotiationRun", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_sessions_status", "status"),
    )


class Buyer(Base):
    """Buyer table - buyer configuration per session."""
    __tablename__ = "buyers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="buyers")
    buyer_items = relationship("BuyerItem", back_populates="buyer", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_buyers_session", "session_id"),
    )


class BuyerItem(Base):
    """Buyer items table - shopping list per buyer."""
    __tablename__ = "buyer_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    buyer_id = Column(String(36), ForeignKey("buyers.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    quantity_needed = Column(Integer, CheckConstraint("quantity_needed > 0"), nullable=False)
    min_price_per_unit = Column(Float, CheckConstraint("min_price_per_unit >= 0"), nullable=False)
    max_price_per_unit = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    buyer = relationship("Buyer", back_populates="buyer_items")
    negotiation_runs = relationship("NegotiationRun", back_populates="buyer_item", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("max_price_per_unit > min_price_per_unit"),
        Index("idx_buyer_items_buyer", "buyer_id"),
    )


class Seller(Base):
    """Seller table - seller configuration per session."""
    __tablename__ = "sellers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    priority = Column(
        String(20),
        CheckConstraint("priority IN ('customer_retention', 'maximize_profit')"),
        nullable=False
    )
    speaking_style = Column(
        String(20),
        CheckConstraint("speaking_style IN ('rude', 'very_sweet')"),
        nullable=False
    )
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="sellers")
    inventory = relationship("SellerInventory", back_populates="seller", cascade="all, delete-orphan")
    negotiation_participants = relationship("NegotiationParticipant", back_populates="seller", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="seller")
    
    __table_args__ = (
        Index("idx_sellers_session", "session_id"),
    )


class SellerInventory(Base):
    """Seller inventory table - items available per seller."""
    __tablename__ = "seller_inventory"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = Column(String(36), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    cost_price = Column(Float, CheckConstraint("cost_price >= 0"), nullable=False)
    selling_price = Column(Float, CheckConstraint("selling_price > cost_price"), nullable=False)
    least_price = Column(Float, nullable=False)
    quantity_available = Column(Integer, CheckConstraint("quantity_available >= 0"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    seller = relationship("Seller", back_populates="inventory")
    
    __table_args__ = (
        CheckConstraint("least_price > cost_price AND least_price < selling_price"),
        UniqueConstraint("seller_id", "item_id", name="uq_seller_inventory_item"),
        Index("idx_seller_inventory_seller", "seller_id"),
        Index("idx_seller_inventory_item", "item_id"),
    )


class NegotiationRun(Base):
    """Negotiation runs table - individual negotiation per item."""
    __tablename__ = "negotiation_runs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    buyer_item_id = Column(String(36), ForeignKey("buyer_items.id", ondelete="CASCADE"), nullable=False)
    status = Column(
        String(20),
        CheckConstraint("status IN ('pending', 'active', 'completed', 'no_sellers_available', 'aborted')"),
        default='pending',
        nullable=False
    )
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    current_round = Column(Integer, default=0, nullable=False)
    max_rounds = Column(Integer, default=10, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    session = relationship("Session", back_populates="negotiation_runs")
    buyer_item = relationship("BuyerItem", back_populates="negotiation_runs")
    participants = relationship("NegotiationParticipant", back_populates="negotiation_run", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="negotiation_run", cascade="all, delete-orphan")
    outcome = relationship("NegotiationOutcome", back_populates="negotiation_run", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_negotiation_runs_session", "session_id"),
        Index("idx_negotiation_runs_status", "status"),
    )


class NegotiationParticipant(Base):
    """Negotiation participants table - sellers participating in a run."""
    __tablename__ = "negotiation_participants"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    negotiation_run_id = Column(String(36), ForeignKey("negotiation_runs.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(String(36), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    negotiation_run = relationship("NegotiationRun", back_populates="participants")
    seller = relationship("Seller", back_populates="negotiation_participants")
    
    __table_args__ = (
        UniqueConstraint("negotiation_run_id", "seller_id", name="uq_negotiation_participant"),
    )


class Message(Base):
    """Messages table - conversation history."""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    negotiation_run_id = Column(String(36), ForeignKey("negotiation_runs.id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    sender_type = Column(
        String(10),
        CheckConstraint("sender_type IN ('buyer', 'seller')"),
        nullable=False
    )
    sender_id = Column(String(36), nullable=False)  # References buyers.id or sellers.id
    sender_name = Column(String(100), nullable=False)
    message_text = Column(Text, nullable=False)
    mentioned_agents = Column(Text, nullable=True)  # JSON array of mentioned seller IDs
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    negotiation_run = relationship("NegotiationRun", back_populates="messages")
    offer = relationship("Offer", back_populates="message", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_messages_negotiation", "negotiation_run_id"),
        Index("idx_messages_turn", "negotiation_run_id", "turn_number"),
    )


class Offer(Base):
    """Offers table - seller offers linked to messages."""
    __tablename__ = "offers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(String(36), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    price_per_unit = Column(Float, CheckConstraint("price_per_unit > 0"), nullable=False)
    quantity = Column(Integer, CheckConstraint("quantity > 0"), nullable=False)
    conditions = Column(Text, nullable=True)  # Optional conditions or terms
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    message = relationship("Message", back_populates="offer")
    seller = relationship("Seller", back_populates="offers")
    
    __table_args__ = (
        Index("idx_offers_message", "message_id"),
        Index("idx_offers_seller", "seller_id"),
    )


class NegotiationOutcome(Base):
    """Negotiation outcomes table - final decision per run."""
    __tablename__ = "negotiation_outcomes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    negotiation_run_id = Column(String(36), ForeignKey("negotiation_runs.id", ondelete="CASCADE"), nullable=False, unique=True)
    decision_type = Column(
        String(20),
        CheckConstraint("decision_type IN ('deal', 'no_deal')"),
        nullable=False
    )
    selected_seller_id = Column(String(36), ForeignKey("sellers.id"), nullable=True)
    final_price_per_unit = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=True)
    total_cost = Column(Float, nullable=True)
    decision_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    negotiation_run = relationship("NegotiationRun", back_populates="outcome")
    
    __table_args__ = (
        Index("idx_outcomes_negotiation", "negotiation_run_id"),
    )

