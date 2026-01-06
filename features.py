"""Deep feature extraction for WhatsApp Wrapped."""

import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

from lm_studio import LMStudioClient, get_client
from parser import Chat, Message


# Personality archetypes
ARCHETYPES = {
    "The Wizard": {
        "emoji": "🧙",
        "description": "Shares wisdom, explains complex topics, the go-to person for knowledge",
        "traits": ["explains", "actually", "basically", "think about", "the thing is"]
    },
    "The Jester": {
        "emoji": "🃏",
        "description": "Brings humor, memes, lightens the mood when things get heavy",
        "traits": ["haha", "lol", "jaja", "lmao", "wtf", "omg"]
    },
    "The Politician": {
        "emoji": "🎭",
        "description": "Diplomatic, mediates conflicts, sees all sides of every argument",
        "traits": ["but also", "on the other hand", "i see what you mean", "fair point"]
    },
    "The Professor": {
        "emoji": "📚",
        "description": "Educational, shares links and articles, keeps everyone informed",
        "traits": ["http", "article", "read this", "check this out", "interesting"]
    },
    "The Cheerleader": {
        "emoji": "📣",
        "description": "Supportive, encouraging, always there to hype up the squad",
        "traits": ["amazing", "proud", "you got this", "lets go", "awesome"]
    },
    "The Rebel": {
        "emoji": "🔥",
        "description": "Contrarian, provocative opinions, not afraid to disagree",
        "traits": ["disagree", "actually no", "unpopular opinion", "but why", "thats bs"]
    },
    "The Storyteller": {
        "emoji": "📖",
        "description": "Long messages, rich narratives, loves to share experiences",
        "traits": []  # Detected by message length
    },
    "The Reactor": {
        "emoji": "⚡",
        "description": "Quick responses, short reactions, keeps the conversation flowing",
        "traits": []  # Detected by message length and frequency
    },
    "The Connector": {
        "emoji": "🔗",
        "description": "Brings up plans, coordinates events, the social glue",
        "traits": ["we should", "lets", "when are", "plans", "meet up", "weekend"]
    }
}


@dataclass
class ConversationThread:
    """A conversation thread with rapid back-and-forth."""
    start_time: datetime
    end_time: datetime
    message_count: int
    participants: list[str]
    exchange_score: float  # How back-and-forth it was
    topic_summary: str = ""
    sample_messages: list[str] = field(default_factory=list)

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def to_dict(self) -> dict:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "message_count": self.message_count,
            "participants": self.participants,
            "exchange_score": self.exchange_score,
            "topic_summary": self.topic_summary,
            "sample_messages": self.sample_messages,
            "duration_minutes": self.duration_minutes
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationThread":
        return cls(
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            message_count=data["message_count"],
            participants=data["participants"],
            exchange_score=data["exchange_score"],
            topic_summary=data.get("topic_summary", ""),
            sample_messages=data.get("sample_messages", [])
        )


@dataclass
class TopicTimeline:
    """Topics extracted over time."""
    topics_by_month: dict[str, list[str]] = field(default_factory=dict)
    topics_by_year: dict[str, list[str]] = field(default_factory=dict)
    aggregate_topics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topics_by_month": self.topics_by_month,
            "topics_by_year": self.topics_by_year,
            "aggregate_topics": self.aggregate_topics
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TopicTimeline":
        return cls(
            topics_by_month=data.get("topics_by_month", {}),
            topics_by_year=data.get("topics_by_year", {}),
            aggregate_topics=data.get("aggregate_topics", [])
        )


@dataclass
class PersonalityProfile:
    """Rich personality analysis for a participant."""
    name: str
    archetype: str = ""
    archetype_emoji: str = ""
    archetype_reason: str = ""
    celebrity_match: str = ""
    celebrity_reason: str = ""
    communication_style: str = ""
    superpower: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "archetype": self.archetype,
            "archetype_emoji": self.archetype_emoji,
            "archetype_reason": self.archetype_reason,
            "celebrity_match": self.celebrity_match,
            "celebrity_reason": self.celebrity_reason,
            "communication_style": self.communication_style,
            "superpower": self.superpower
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PersonalityProfile":
        return cls(**data)


@dataclass
class ChatFeatures:
    """All extracted features for the chat."""
    chat_hash: str
    extracted_at: datetime
    topic_timeline: TopicTimeline
    top_threads: list[ConversationThread]
    personality_profiles: dict[str, PersonalityProfile]

    def to_dict(self) -> dict:
        return {
            "chat_hash": self.chat_hash,
            "extracted_at": self.extracted_at.isoformat(),
            "topic_timeline": self.topic_timeline.to_dict(),
            "top_threads": [t.to_dict() for t in self.top_threads],
            "personality_profiles": {
                name: p.to_dict()
                for name, p in self.personality_profiles.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatFeatures":
        return cls(
            chat_hash=data["chat_hash"],
            extracted_at=datetime.fromisoformat(data["extracted_at"]),
            topic_timeline=TopicTimeline.from_dict(data["topic_timeline"]),
            top_threads=[ConversationThread.from_dict(t) for t in data["top_threads"]],
            personality_profiles={
                name: PersonalityProfile.from_dict(p)
                for name, p in data["personality_profiles"].items()
            }
        )

    def save(self, filepath: str | Path) -> None:
        """Save features to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str | Path) -> "ChatFeatures":
        """Load features from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


def compute_chat_hash(chat: Chat) -> str:
    """Compute a hash of the chat for cache invalidation."""
    content = f"{len(chat.messages)}_{chat.messages[0].timestamp}_{chat.messages[-1].timestamp}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


class FeatureExtractor:
    """Extracts deep features from chat data."""

    def __init__(self, chat: Chat, client: LMStudioClient | None = None):
        self.chat = chat
        self.client = client or get_client()

    def _format_messages_for_llm(self, messages: list[Message], include_sender: bool = True) -> str:
        """Format messages for LLM input."""
        formatted = []
        for msg in messages[:50]:  # Limit to avoid token overflow
            content = msg.content[:200]
            if include_sender:
                formatted.append(f"[{msg.sender}]: {content}")
            else:
                formatted.append(f"- {content}")
        return '\n'.join(formatted)

    # =========================================================================
    # Conversation Thread Detection
    # =========================================================================

    def find_conversation_threads(
        self,
        max_gap_minutes: int = 5,
        min_messages: int = 10
    ) -> list[ConversationThread]:
        """Find conversation threads based on message timing."""
        if not self.chat.messages:
            return []

        sorted_msgs = sorted(self.chat.messages, key=lambda m: m.timestamp)
        threads: list[list[Message]] = []
        current_thread: list[Message] = [sorted_msgs[0]]

        for i in range(1, len(sorted_msgs)):
            msg = sorted_msgs[i]
            prev_msg = sorted_msgs[i - 1]
            gap = (msg.timestamp - prev_msg.timestamp).total_seconds() / 60

            if gap <= max_gap_minutes:
                current_thread.append(msg)
            else:
                if len(current_thread) >= min_messages:
                    threads.append(current_thread)
                current_thread = [msg]

        if len(current_thread) >= min_messages:
            threads.append(current_thread)

        # Score and convert threads
        scored_threads = []
        for thread_msgs in threads:
            thread = self._score_thread(thread_msgs)
            scored_threads.append(thread)

        # Sort by engagement score and return top 5
        scored_threads.sort(key=lambda t: t.exchange_score, reverse=True)
        return scored_threads[:5]

    def _score_thread(self, messages: list[Message]) -> ConversationThread:
        """Score a thread based on engagement metrics."""
        participants = list(set(m.sender for m in messages))
        message_count = len(messages)

        # Calculate back-and-forth score
        sender_changes = 0
        for i in range(1, len(messages)):
            if messages[i].sender != messages[i-1].sender:
                sender_changes += 1

        # Normalize: higher score for more alternation
        max_changes = message_count - 1
        alternation_ratio = sender_changes / max_changes if max_changes > 0 else 0

        # Combine factors into engagement score
        participant_factor = len(participants) / len(self.chat.participants)
        message_factor = min(message_count / 50, 1.0)  # Cap at 50 messages
        avg_length = sum(len(m.content) for m in messages) / message_count
        length_factor = min(avg_length / 100, 1.0)  # Cap at 100 chars

        exchange_score = (
            alternation_ratio * 0.4 +
            participant_factor * 0.2 +
            message_factor * 0.2 +
            length_factor * 0.2
        )

        # Get sample messages (first few and some from middle)
        sample = messages[:3] + messages[len(messages)//2:len(messages)//2+2]
        sample_texts = [m.content[:100] for m in sample]

        return ConversationThread(
            start_time=messages[0].timestamp,
            end_time=messages[-1].timestamp,
            message_count=message_count,
            participants=participants,
            exchange_score=exchange_score,
            sample_messages=sample_texts
        )

    def summarize_thread(self, thread: ConversationThread, all_messages: list[Message]) -> str:
        """Use LLM to summarize what a thread was about."""
        # Find messages in this thread's time range
        thread_msgs = [
            m for m in all_messages
            if thread.start_time <= m.timestamp <= thread.end_time
        ]

        messages_text = self._format_messages_for_llm(thread_msgs[:30])

        prompt = f"""This is a conversation that had {thread.message_count} messages over {thread.duration_minutes} minutes between {', '.join(thread.participants)}.

Summarize in ONE sentence what this conversation was about:

{messages_text}

One sentence summary:"""

        try:
            return self.client.generate(
                prompt,
                system_prompt="You summarize conversations concisely. One sentence only.",
                temperature=0.5,
                max_tokens=100
            ).strip()
        except Exception:
            return "An engaging discussion"

    # =========================================================================
    # Topic Timeline Extraction
    # =========================================================================

    def extract_topic_timeline(self) -> TopicTimeline:
        """Extract topics by month and year."""
        timeline = TopicTimeline()

        # Group messages by month
        messages_by_month: dict[str, list[Message]] = {}
        for msg in self.chat.messages:
            month_key = msg.timestamp.strftime('%Y-%m')
            if month_key not in messages_by_month:
                messages_by_month[month_key] = []
            messages_by_month[month_key].append(msg)

        # Extract topics for each month
        for month_key in sorted(messages_by_month.keys()):
            month_msgs = messages_by_month[month_key]
            topics = self._extract_topics_from_messages(month_msgs, n_topics=5)
            timeline.topics_by_month[month_key] = topics

        # Aggregate by year
        topics_by_year: dict[str, list[str]] = {}
        for month_key, topics in timeline.topics_by_month.items():
            year = month_key[:4]
            if year not in topics_by_year:
                topics_by_year[year] = []
            topics_by_year[year].extend(topics)

        # Get top topics per year
        for year, all_topics in topics_by_year.items():
            # Count topic frequency
            topic_counts = Counter(all_topics)
            timeline.topics_by_year[year] = [t for t, _ in topic_counts.most_common(5)]

        # Overall aggregate
        all_topics = []
        for topics in timeline.topics_by_month.values():
            all_topics.extend(topics)
        topic_counts = Counter(all_topics)
        timeline.aggregate_topics = [t for t, _ in topic_counts.most_common(10)]

        return timeline

    def _extract_topics_from_messages(
        self,
        messages: list[Message],
        n_topics: int = 5
    ) -> list[str]:
        """Extract topics from a set of messages using LLM."""
        # Sample messages
        good_messages = [m for m in messages if not m.is_media and len(m.content) > 20]
        if len(good_messages) > 40:
            sample = random.sample(good_messages, 40)
        else:
            sample = good_messages

        if not sample:
            return ["General chat"]

        messages_text = self._format_messages_for_llm(sample, include_sender=False)

        prompt = f"""Based on these chat messages, identify the {n_topics} main topics discussed.

Messages:
{messages_text}

List exactly {n_topics} topics, one per line (short, 2-4 words each):"""

        try:
            response = self.client.generate(
                prompt,
                system_prompt="You identify conversation topics. Be specific and concise.",
                temperature=0.5
            )
            topics = [
                line.strip().strip('-').strip('0123456789.').strip()
                for line in response.strip().split('\n')
                if line.strip()
            ]
            return topics[:n_topics]
        except Exception:
            return ["General discussion"]

    # =========================================================================
    # Personality Archetype Detection
    # =========================================================================

    def extract_personality_profile(self, name: str) -> PersonalityProfile:
        """Extract personality profile for a participant."""
        messages = self.chat.messages_by_sender.get(name, [])
        if not messages:
            return PersonalityProfile(name=name, archetype="The Mystery")

        profile = PersonalityProfile(name=name)

        # Detect archetype based on traits and patterns
        archetype, emoji = self._detect_archetype(messages)
        profile.archetype = archetype
        profile.archetype_emoji = emoji

        # Use LLM for deeper analysis
        sample = random.sample(messages, min(40, len(messages)))
        messages_text = self._format_messages_for_llm(sample, include_sender=False)

        prompt = f"""Based on these messages from {name}, answer briefly:

Messages:
{messages_text}

1. Why are they "{archetype}"? (one sentence)
2. If they were a celebrity, who would they be and why? (name + one sentence reason)
3. Their communication superpower in one phrase (5 words max)

Format your response as:
ARCHETYPE_REASON: [reason]
CELEBRITY: [name] - [reason]
SUPERPOWER: [superpower]"""

        try:
            response = self.client.generate(
                prompt,
                system_prompt="You analyze personalities in a fun, Wrapped style. Be specific and witty.",
                temperature=0.8
            )

            # Parse response
            for line in response.strip().split('\n'):
                if line.startswith('ARCHETYPE_REASON:'):
                    profile.archetype_reason = line.replace('ARCHETYPE_REASON:', '').strip()
                elif line.startswith('CELEBRITY:'):
                    parts = line.replace('CELEBRITY:', '').strip().split(' - ', 1)
                    profile.celebrity_match = parts[0].strip()
                    profile.celebrity_reason = parts[1].strip() if len(parts) > 1 else ""
                elif line.startswith('SUPERPOWER:'):
                    profile.superpower = line.replace('SUPERPOWER:', '').strip()

        except Exception:
            profile.archetype_reason = f"Embodies the spirit of {archetype}"
            profile.celebrity_match = "A unique original"
            profile.superpower = "Being themselves"

        return profile

    def _detect_archetype(self, messages: list[Message]) -> tuple[str, str]:
        """Detect archetype based on message patterns."""
        all_content = ' '.join(m.content.lower() for m in messages)
        msg_lengths = [len(m.content) for m in messages]
        avg_length = sum(msg_lengths) / len(msg_lengths) if msg_lengths else 0

        # Score each archetype
        scores: dict[str, float] = {}

        for archetype, info in ARCHETYPES.items():
            score = 0
            for trait in info["traits"]:
                count = all_content.count(trait)
                score += count

            # Special detection for Storyteller (long messages)
            if archetype == "The Storyteller" and avg_length > 80:
                score += 50

            # Special detection for Reactor (short messages, high frequency)
            if archetype == "The Reactor" and avg_length < 30:
                score += 30

            scores[archetype] = score

        # Get highest scoring archetype
        best_archetype = max(scores, key=lambda k: scores[k])
        return best_archetype, ARCHETYPES[best_archetype]["emoji"]

    # =========================================================================
    # Main Extraction
    # =========================================================================

    def extract_all_features(self, progress_callback=None) -> ChatFeatures:
        """Extract all features from the chat."""
        chat_hash = compute_chat_hash(self.chat)

        # Step 1: Find conversation threads
        if progress_callback:
            progress_callback("Finding engaging conversations...")
        threads = self.find_conversation_threads()

        # Summarize top threads
        sorted_msgs = sorted(self.chat.messages, key=lambda m: m.timestamp)
        for thread in threads:
            if progress_callback:
                progress_callback(f"Analyzing conversation from {thread.start_time.strftime('%b %d')}...")
            thread.topic_summary = self.summarize_thread(thread, sorted_msgs)

        # Step 2: Extract topic timeline
        if progress_callback:
            progress_callback("Extracting topic timeline...")
        topic_timeline = self.extract_topic_timeline()

        # Step 3: Extract personality profiles
        personality_profiles = {}
        for name in self.chat.participants:
            if progress_callback:
                progress_callback(f"Analyzing {name}'s personality...")
            personality_profiles[name] = self.extract_personality_profile(name)

        return ChatFeatures(
            chat_hash=chat_hash,
            extracted_at=datetime.now(),
            topic_timeline=topic_timeline,
            top_threads=threads,
            personality_profiles=personality_profiles
        )


def get_features_cache_path(chat_file: Path) -> Path:
    """Get the cache file path for a chat file."""
    return chat_file.with_suffix('.features.json')


def load_or_extract_features(
    chat: Chat,
    chat_file: Path,
    client: LMStudioClient | None = None,
    force_rebuild: bool = False,
    progress_callback=None
) -> ChatFeatures:
    """Load cached features or extract fresh ones."""
    cache_path = get_features_cache_path(chat_file)
    chat_hash = compute_chat_hash(chat)

    # Try to load from cache
    if not force_rebuild and cache_path.exists():
        try:
            cached = ChatFeatures.load(cache_path)
            if cached.chat_hash == chat_hash:
                if progress_callback:
                    progress_callback("Loaded features from cache")
                return cached
        except Exception:
            pass  # Cache invalid, extract fresh

    # Extract fresh features
    extractor = FeatureExtractor(chat, client)
    features = extractor.extract_all_features(progress_callback)

    # Save to cache
    features.save(cache_path)
    if progress_callback:
        progress_callback(f"Saved features to {cache_path.name}")

    return features


if __name__ == '__main__':
    import sys
    from parser import parse_chat

    if len(sys.argv) < 2:
        print("Usage: python features.py <chat_file>")
        sys.exit(1)

    chat_file = Path(sys.argv[1])
    print(f"Parsing {chat_file}...")
    chat = parse_chat(chat_file)

    print("Extracting features (this may take a moment)...")

    def progress(msg):
        print(f"  {msg}")

    features = load_or_extract_features(
        chat, chat_file,
        force_rebuild='--rebuild' in sys.argv,
        progress_callback=progress
    )

    print(f"\n=== Topic Timeline ===")
    for month, topics in sorted(features.topic_timeline.topics_by_month.items()):
        print(f"{month}: {', '.join(topics)}")

    print(f"\n=== Top 5 Conversations ===")
    for i, thread in enumerate(features.top_threads, 1):
        print(f"\n#{i} ({thread.start_time.strftime('%b %d, %Y')})")
        print(f"   {thread.message_count} messages over {thread.duration_minutes} min")
        print(f"   Participants: {', '.join(thread.participants)}")
        print(f"   About: {thread.topic_summary}")

    print(f"\n=== Personality Profiles ===")
    for name, profile in features.personality_profiles.items():
        print(f"\n{name}: {profile.archetype} {profile.archetype_emoji}")
        print(f"  Why: {profile.archetype_reason}")
        print(f"  Celebrity: {profile.celebrity_match}")
        print(f"  Superpower: {profile.superpower}")
