"""Search service with Perplexity Search API integration."""

import logging
import time
from uuid import uuid4

from clients.perplexity_client import perplexity_client
from schemas.gaming_search import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling search requests using Perplexity Search API."""

    def __init__(self) -> None:
        """Initialize the Search service."""

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform a search using Perplexity Search API.
        Supports both single query and multi-query (up to 5 queries).

        Args:
            request: Search request with single query or list of queries

        Returns:
            Search response with results
        """
        search_id = str(uuid4())
        is_multi_query = isinstance(request.query, list)

        try:
            logger.info(
                f"Search started - ID: {search_id}, "
                f"Query: {request.query}, "
                f"Multi-query: {is_multi_query}"
            )

            # Call Perplexity search API
            response = perplexity_client.search(
                query=request.query,
                max_results=request.max_results,
                max_tokens_per_page=request.max_tokens_per_page,
            )

            # Debug logging to understand response structure
            logger.debug(f"Response type: {type(response)}")
            if hasattr(response, "results"):
                logger.debug(f"Results type: {type(response.results)}")
                if response.results and len(response.results) > 0:
                    logger.debug(f"First result type: {type(response.results[0])}")
                    logger.debug(f"First result: {response.results[0]}")

            # Extract and process search results
            # Note: Multi-query returns flat list (one result per query), not nested lists
            search_results: list[SearchResultItem] = []
            if hasattr(response, "results") and response.results:
                for result in response.results:
                    search_results.append(
                        SearchResultItem(
                            title=result.title,
                            url=result.url,
                            snippet=getattr(result, "snippet", None),
                            date=getattr(result, "date", None),
                        )
                    )

            logger.info(
                f"Search completed - ID: {search_id}, "
                f"Query type: {'multi' if is_multi_query else 'single'}, "
                f"Results: {len(search_results)}"
            )

            return SearchResponse(
                id=search_id,
                results=search_results,
                query=request.query,
                total_results=len(search_results),
                created=int(time.time()),
                is_multi_query=is_multi_query,
            )

        except Exception as e:
            logger.error(f"Search failed - ID: {search_id}, Error: {str(e)}")
            raise RuntimeError(f"Search failed: {str(e)}") from e


# Global service instance
search_service = SearchService()
