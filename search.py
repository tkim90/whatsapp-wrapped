"""Search system with BM25, semantic, and keyword search."""

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from lm_studio import LMStudioClient, get_client
from parser import Message


@dataclass
class SearchResult:
    """A search result with score and message."""
    message: Message
    score: float
    method: str  # 'bm25', 'semantic', 'keyword', 'hybrid'


class MessageSearcher:
    """Unified search over messages using multiple methods."""

    def __init__(
        self,
        messages: list[Message],
        client: LMStudioClient | None = None,
        embed_on_init: bool = False
    ):
        self.messages = messages
        self.client = client or get_client()

        # Tokenized corpus for BM25
        self._corpus = [self._tokenize(m.content) for m in messages]
        self._bm25 = BM25Okapi(self._corpus)

        # Embeddings for semantic search (lazy loaded)
        self._embeddings: np.ndarray | None = None

        if embed_on_init:
            self._compute_embeddings()

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    def _compute_embeddings(self) -> None:
        """Compute embeddings for all messages."""
        if self._embeddings is not None:
            return

        texts = [m.content for m in self.messages]
        embeddings_list = self.client.get_embeddings_batch(texts)
        self._embeddings = np.array(embeddings_list)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def search_bm25(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Search using BM25 algorithm."""
        query_tokens = self._tokenize(query)
        scores = self._bm25.get_scores(query_tokens)

        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append(SearchResult(
                    message=self.messages[idx],
                    score=float(scores[idx]),
                    method='bm25'
                ))

        return results

    def search_semantic(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Search using semantic similarity with embeddings."""
        self._compute_embeddings()
        assert self._embeddings is not None

        query_embedding = np.array(self.client.get_embedding(query))

        # Compute similarities
        similarities = []
        for i, emb in enumerate(self._embeddings):
            sim = self._cosine_similarity(query_embedding, emb)
            similarities.append((i, sim))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in similarities[:top_k]:
            if score > 0:
                results.append(SearchResult(
                    message=self.messages[idx],
                    score=score,
                    method='semantic'
                ))

        return results

    def search_keyword(
        self,
        pattern: str,
        case_insensitive: bool = True,
        top_k: int = 100
    ) -> list[SearchResult]:
        """Search using regex pattern matching (grep-like)."""
        flags = re.IGNORECASE if case_insensitive else 0

        try:
            regex = re.compile(pattern, flags)
        except re.error:
            # Fall back to literal search if invalid regex
            regex = re.compile(re.escape(pattern), flags)

        results = []
        for msg in self.messages:
            matches = list(regex.finditer(msg.content))
            if matches:
                # Score based on number of matches
                score = len(matches)
                results.append(SearchResult(
                    message=msg,
                    score=float(score),
                    method='keyword'
                ))

        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def search_hybrid(
        self,
        query: str,
        top_k: int = 10,
        bm25_weight: float = 0.3,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.2
    ) -> list[SearchResult]:
        """Combine all search methods with weighted scoring."""
        # Get results from each method
        bm25_results = self.search_bm25(query, top_k=top_k * 2)
        semantic_results = self.search_semantic(query, top_k=top_k * 2)
        keyword_results = self.search_keyword(query, top_k=top_k * 2)

        # Normalize scores within each method
        def normalize_scores(results: list[SearchResult]) -> dict[int, float]:
            if not results:
                return {}
            max_score = max(r.score for r in results)
            if max_score == 0:
                return {}
            return {
                id(r.message): r.score / max_score
                for r in results
            }

        bm25_scores = normalize_scores(bm25_results)
        semantic_scores = normalize_scores(semantic_results)
        keyword_scores = normalize_scores(keyword_results)

        # Combine scores
        message_scores: dict[int, tuple[Message, float]] = {}

        for results, scores, weight in [
            (bm25_results, bm25_scores, bm25_weight),
            (semantic_results, semantic_scores, semantic_weight),
            (keyword_results, keyword_scores, keyword_weight),
        ]:
            for r in results:
                msg_id = id(r.message)
                normalized = scores.get(msg_id, 0)
                if msg_id not in message_scores:
                    message_scores[msg_id] = (r.message, 0.0)
                msg, score = message_scores[msg_id]
                message_scores[msg_id] = (msg, score + normalized * weight)

        # Sort and return top results
        sorted_results = sorted(
            message_scores.values(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            SearchResult(message=msg, score=score, method='hybrid')
            for msg, score in sorted_results[:top_k]
        ]

    def find_similar_messages(
        self,
        reference_message: Message,
        top_k: int = 5
    ) -> list[SearchResult]:
        """Find messages similar to a reference message."""
        return self.search_semantic(reference_message.content, top_k=top_k + 1)[1:]

    def search_by_sender(
        self,
        sender: str,
        query: str | None = None,
        top_k: int = 10
    ) -> list[SearchResult]:
        """Search within a specific sender's messages."""
        sender_messages = [m for m in self.messages if m.sender == sender]

        if not query:
            # Return most recent messages
            return [
                SearchResult(message=m, score=1.0, method='filter')
                for m in sender_messages[-top_k:]
            ]

        # Create temporary searcher for sender's messages
        temp_searcher = MessageSearcher(sender_messages, self.client)
        return temp_searcher.search_hybrid(query, top_k=top_k)


if __name__ == '__main__':
    import sys
    from parser import parse_chat

    if len(sys.argv) < 2:
        print("Usage: python search.py <chat_file> [query]")
        sys.exit(1)

    chat = parse_chat(sys.argv[1])
    print(f"Loaded {len(chat.messages)} messages")

    searcher = MessageSearcher(chat.messages)

    query = sys.argv[2] if len(sys.argv) > 2 else "funny"
    print(f"\nSearching for: '{query}'")

    print("\n--- BM25 Results ---")
    for r in searcher.search_bm25(query, top_k=3):
        print(f"[{r.score:.2f}] {r.message.sender}: {r.message.content[:80]}...")

    print("\n--- Keyword Results ---")
    for r in searcher.search_keyword(query, top_k=3):
        print(f"[{r.score:.2f}] {r.message.sender}: {r.message.content[:80]}...")
