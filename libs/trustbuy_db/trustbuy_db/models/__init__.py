"""Importing this module registers every model on `Base.metadata` - Alembic's
`env.py` imports this package so `--autogenerate` and `upgrade head` see the
full schema, and each service imports it for the same reason.
"""

from trustbuy_db.models.audit_log import AuditLog
from trustbuy_db.models.community import (
    Badge,
    Report,
    ReportAttachment,
    ReportVerification,
    ReportVote,
    TrustPointsLedger,
    UserBadge,
)
from trustbuy_db.models.copilot import CopilotConversation, CopilotMessage
from trustbuy_db.models.investigation import (
    AgentRun,
    AlternativeSeller,
    EvidenceItem,
    Investigation,
    Recommendation,
)
from trustbuy_db.models.marketplace import Business, Marketplace
from trustbuy_db.models.product import Advertisement, PriceHistory, Product, ProductImage, Review
from trustbuy_db.models.refresh_token import RefreshToken
from trustbuy_db.models.seller import Seller, SellerLink
from trustbuy_db.models.user import User

__all__ = [
    "User",
    "RefreshToken",
    "AuditLog",
    "Marketplace",
    "Business",
    "Seller",
    "SellerLink",
    "Product",
    "ProductImage",
    "PriceHistory",
    "Review",
    "Advertisement",
    "Investigation",
    "AgentRun",
    "EvidenceItem",
    "Recommendation",
    "AlternativeSeller",
    "Report",
    "ReportAttachment",
    "ReportVote",
    "ReportVerification",
    "TrustPointsLedger",
    "Badge",
    "UserBadge",
    "CopilotConversation",
    "CopilotMessage",
]
