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

            # Extract and process search results
            if is_multi_query:
                # Multi-query: response.results is a list of lists
                # Each inner list contains results for one query
                multi_query_results: list[list[SearchResultItem]] = []
                total_count = 0
                
                if hasattr(response, "results") and response.results:
                    for query_results in response.results:
                        query_result_items: list[SearchResultItem] = []
                        for result in query_results:
                            query_result_items.append(
                                SearchResultItem(
                                    title=result.title,
                                    url=result.url,
                                    snippet=getattr(result, "snippet", None),
                                    date=getattr(result, "date", None),
                                )
                            )
                        multi_query_results.append(query_result_items)
                        total_count += len(query_result_items)
                
                logger.info(
                    f"Multi-query search completed - ID: {search_id}, "
                    f"Queries: {len(multi_query_results)}, "
                    f"Total results: {total_count}"
                )
                
                return SearchResponse(
                    id=search_id,
                    results=multi_query_results,
                    query=request.query,
                    total_results=total_count,
                    created=int(time.time()),
                    is_multi_query=True,
                )
            else:
                # Single query: response.results is a flat list
                single_query_results: list[SearchResultItem] = []
                if hasattr(response, "results") and response.results:
                    for result in response.results:
                        single_query_results.append(
                            SearchResultItem(
                                title=result.title,
                                url=result.url,
                                snippet=getattr(result, "snippet", None),
                                date=getattr(result, "date", None),
                            )
                        )

                logger.info(
                    f"Search completed - ID: {search_id}, Results: {len(single_query_results)}"
                )

                return SearchResponse(
                    id=search_id,
                    results=single_query_results,
                    query=request.query,
                    total_results=len(single_query_results),
                    created=int(time.time()),
                    is_multi_query=False,
                )

        except Exception as e:
            logger.error(f"Search failed - ID: {search_id}, Error: {str(e)}")
            raise RuntimeError(f"Search failed: {str(e)}") from e


# Global service instance
search_service = SearchService()
