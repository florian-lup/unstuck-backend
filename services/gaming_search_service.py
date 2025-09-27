"""Search service with Perplexity Search API integration."""

import logging
import time
from uuid import uuid4

from schemas.gaming_search import (
    SearchRequest,
    SearchResponse,
    SearchResultItem,
)

from clients.perplexity_client import perplexity_client

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling search requests using Perplexity Search API."""

    def __init__(self) -> None:
        """Initialize the Search service."""

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform a search using Perplexity Search API.

        Args:
            request: Search request

        Returns:
            Search response
        """
        search_id = str(uuid4())

        try:
            logger.info(f"Search started - ID: {search_id}, Query: {request.query}")

            # Call Perplexity search API
            response = perplexity_client.search(
                query=request.query,
                max_results=request.max_results,
                max_tokens_per_page=request.max_tokens_per_page,
            )

            # Extract and process search results
            search_results = []
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

            logger.info(f"Search completed - ID: {search_id}, Results: {len(search_results)}")

            return SearchResponse(
                id=search_id,
                results=search_results,
                query=request.query,
                total_results=len(search_results),
                created=int(time.time()),
            )

        except Exception as e:
            logger.error(f"Search failed - ID: {search_id}, Error: {str(e)}")
            raise RuntimeError(f"Search failed: {str(e)}") from e


# Global service instance
search_service = SearchService()