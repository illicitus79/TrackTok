"""Pagination utilities for API endpoints."""
from typing import Any, Dict, List, Optional

from flask import request
from sqlalchemy.orm import Query


class Pagination:
    """Pagination helper class."""

    def __init__(
        self,
        items: List[Any],
        page: int,
        per_page: int,
        total: int
    ):
        """
        Initialize pagination.
        
        Args:
            items: List of items for current page
            page: Current page number (1-indexed)
            per_page: Items per page
            total: Total number of items
        """
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1 if self.has_prev else None
        self.next_num = page + 1 if self.has_next else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pagination to dictionary format."""
        return {
            "items": self.items,
            "page": self.page,
            "per_page": self.per_page,
            "total": self.total,
            "pages": self.pages,
            "has_prev": self.has_prev,
            "has_next": self.has_next,
            "prev_num": self.prev_num,
            "next_num": self.next_num
        }


def paginate(
    query: Query,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    max_per_page: int = 100,
    default_per_page: int = 20
) -> Pagination:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed), defaults to request arg
        per_page: Items per page, defaults to request arg
        max_per_page: Maximum allowed per_page value
        default_per_page: Default per_page if not specified
        
    Returns:
        Pagination object
    """
    # Get pagination parameters from request if not provided
    if page is None:
        page = request.args.get('page', 1, type=int)
    if per_page is None:
        per_page = request.args.get('per_page', default_per_page, type=int)

    # Validate and clamp values
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    # Get total count
    total = query.count()

    # Get items for current page
    offset = (page - 1) * per_page
    items = query.limit(per_page).offset(offset).all()

    return Pagination(
        items=items,
        page=page,
        per_page=per_page,
        total=total
    )


def get_pagination_params(
    default_per_page: int = 20,
    max_per_page: int = 100
) -> tuple[int, int]:
    """
    Extract and validate pagination parameters from request.
    
    Args:
        default_per_page: Default items per page
        max_per_page: Maximum allowed items per page
        
    Returns:
        Tuple of (page, per_page)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)

    # Validate
    page = max(1, page)
    per_page = max(1, min(per_page, max_per_page))

    return page, per_page


def add_pagination_headers(response, pagination: Pagination) -> None:
    """
    Add pagination metadata to response headers.
    
    Args:
        response: Flask response object
        pagination: Pagination object
    """
    response.headers['X-Total-Count'] = str(pagination.total)
    response.headers['X-Total-Pages'] = str(pagination.pages)
    response.headers['X-Current-Page'] = str(pagination.page)
    response.headers['X-Per-Page'] = str(pagination.per_page)
    
    if pagination.has_next:
        response.headers['X-Next-Page'] = str(pagination.next_num)
    if pagination.has_prev:
        response.headers['X-Prev-Page'] = str(pagination.prev_num)
