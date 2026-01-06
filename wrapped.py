"""Wrapped content generator using LLM and search."""

import random
from dataclasses import dataclass, field

from analytics import ChatAnalytics, ParticipantStats
from lm_studio import LMStudioClient, get_client
from parser import Chat, Message
from search import MessageSearcher


@dataclass
class Award:
    """A fun award for a participant."""
    title: str
    description: str
    value: str


@dataclass
class ParticipantWrapped:
    """Wrapped summary for a single participant."""
    name: str
    stats: ParticipantStats
    personality_summary: str = ""
    top_topics: list[str] = field(default_factory=list)
    memorable_quotes: list[str] = field(default_factory=list)
    awards: list[Award] = field(default_factory=list)
    fun_fact: str = ""
    tagline: str = ""


@dataclass
class GroupWrapped:
    """Wrapped summary for the entire group."""
    chat_name: str
    summary: str = ""
    vibe_check: str = ""
    top_moments: list[str] = field(default_factory=list)
    group_personality: str = ""
    awards_ceremony: list[tuple[str, Award]] = field(default_factory=list)


class WrappedGenerator:
    """Generates Wrapped content using LLM and analytics."""

    def __init__(
        self,
        chat: Chat,
        analytics: ChatAnalytics,
        client: LMStudioClient | None = None
    ):
        self.chat = chat
        self.analytics = analytics
        self.client = client or get_client()
        self.searcher = MessageSearcher(chat.messages, self.client)

    def _sample_messages(
        self,
        messages: list[Message],
        n: int = 30,
        min_length: int = 20
    ) -> list[Message]:
        """Sample representative messages from a list."""
        # Filter out media and very short messages
        good_messages = [
            m for m in messages
            if not m.is_media and len(m.content) >= min_length
        ]

        if len(good_messages) <= n:
            return good_messages

        # Sample evenly across the time range
        return random.sample(good_messages, n)

    def _format_messages_for_llm(self, messages: list[Message]) -> str:
        """Format messages for LLM input."""
        formatted = []
        for msg in messages:
            content = msg.content[:300]  # Truncate long messages
            formatted.append(f"- {content}")
        return '\n'.join(formatted)

    def generate_personality_summary(self, name: str) -> str:
        """Generate a fun personality summary for a participant."""
        messages = self.chat.messages_by_sender.get(name, [])
        if not messages:
            return "A mysterious presence in the chat..."

        sample = self._sample_messages(messages, n=40)
        messages_text = self._format_messages_for_llm(sample)

        stats = self.analytics.participant_stats.get(name)
        stats_context = ""
        if stats:
            stats_context = f"""
Stats:
- Sent {stats.total_messages:,} messages
- Shared {stats.url_count} links
- Used {stats.emoji_count} emojis
- Most active at {stats.most_active_hour}:00
- Average message length: {stats.avg_message_length:.0f} characters
"""

        prompt = f"""Based on these chat messages from {name}, write a SHORT, fun, Spotify Wrapped-style personality summary (2-3 sentences max). Be playful and specific to what you see in the messages. Don't be generic.
{stats_context}
Sample messages:
{messages_text}

Write the personality summary for {name} (2-3 sentences, fun and specific):"""

        try:
            return self.client.generate(
                prompt,
                system_prompt="You write fun, witty Spotify Wrapped-style summaries. Be concise, playful, and specific. No generic praise - find unique quirks.",
                temperature=0.8
            ).strip()
        except Exception as e:
            return f"The enigmatic {name}, keeper of messages..."

    def generate_top_topics(self, name: str, n: int = 5) -> list[str]:
        """Identify top conversation topics for a participant."""
        messages = self.chat.messages_by_sender.get(name, [])
        if not messages:
            return []

        sample = self._sample_messages(messages, n=50)
        messages_text = self._format_messages_for_llm(sample)

        prompt = f"""Based on these messages from {name}, identify their TOP {n} conversation topics or interests.

Messages:
{messages_text}

List exactly {n} topics, one per line (just the topic name, no numbers or bullets):"""

        try:
            response = self.client.generate(
                prompt,
                system_prompt="You analyze chat messages to identify recurring topics and interests. Be specific and concise.",
                temperature=0.5
            )
            topics = [line.strip() for line in response.strip().split('\n') if line.strip()]
            return topics[:n]
        except Exception:
            return ["Life", "The Universe", "Everything"]

    def find_memorable_quotes(self, name: str, n: int = 3) -> list[str]:
        """Find memorable/funny quotes from a participant using search."""
        messages = self.chat.messages_by_sender.get(name, [])
        if not messages:
            return []

        # Use various search queries to find interesting messages
        search_queries = [
            "funny hilarious lol lmao haha",
            "love hate best worst amazing terrible",
            "actually honestly literally basically",
        ]

        candidates: list[Message] = []

        # Keyword search for interesting messages
        for msg in messages:
            if not msg.is_media and len(msg.content) > 30:
                # Prioritize messages with personality
                content_lower = msg.content.lower()
                if any(word in content_lower for word in ['haha', 'lol', '!', '?', 'wtf', 'omg']):
                    candidates.append(msg)

        # Also add some random longer messages
        long_messages = [m for m in messages if not m.is_media and len(m.content) > 50]
        if long_messages:
            candidates.extend(random.sample(long_messages, min(10, len(long_messages))))

        if not candidates:
            candidates = [m for m in messages if not m.is_media][:20]

        if not candidates:
            return []

        # Use LLM to pick the best quotes
        sample = random.sample(candidates, min(20, len(candidates)))
        messages_text = self._format_messages_for_llm(sample)

        prompt = f"""From these messages by {name}, pick the {n} most memorable, funny, or quotable ones. These should be messages that would make good "Wrapped" highlights.

Messages:
{messages_text}

Copy exactly {n} of the best quotes (just the quote text, one per line):"""

        try:
            response = self.client.generate(
                prompt,
                system_prompt="You select the most memorable and quotable messages. Pick ones that are funny, insightful, or uniquely characteristic.",
                temperature=0.7
            )
            quotes = [line.strip().strip('-').strip() for line in response.strip().split('\n') if line.strip()]
            return quotes[:n]
        except Exception:
            # Fallback to random quotes
            return [m.content[:100] for m in random.sample(candidates, min(n, len(candidates)))]

    def generate_awards(self, name: str) -> list[Award]:
        """Generate fun awards based on statistics."""
        stats = self.analytics.participant_stats.get(name)
        if not stats:
            return []

        awards = []

        # Check various award criteria
        analytics = self.analytics

        if name == analytics.get_top_chatter():
            awards.append(Award(
                title="TOP CHATTER",
                description="Most messages sent",
                value=f"{stats.total_messages:,} messages"
            ))

        if name == analytics.get_link_lord():
            awards.append(Award(
                title="LINK LORD",
                description="Shared the most URLs",
                value=f"{stats.url_count} links"
            ))

        if name == analytics.get_emoji_enthusiast():
            awards.append(Award(
                title="EMOJI ENTHUSIAST",
                description="Used the most emojis",
                value=f"{stats.emoji_count} emojis"
            ))

        if name == analytics.get_conversation_catalyst():
            awards.append(Award(
                title="CONVERSATION CATALYST",
                description="Started the most conversations",
                value=f"{stats.conversation_starts} times"
            ))

        if name == analytics.get_novelist():
            awards.append(Award(
                title="THE NOVELIST",
                description="Longest average messages",
                value=f"{stats.avg_message_length:.0f} chars/msg"
            ))

        if stats.is_night_owl:
            awards.append(Award(
                title="NIGHT OWL",
                description="Active in the wee hours",
                value=f"Peak: {stats.most_active_hour}:00"
            ))

        if stats.is_early_bird:
            awards.append(Award(
                title="EARLY BIRD",
                description="Up with the sun",
                value=f"Peak: {stats.most_active_hour}:00"
            ))

        # Top emoji user award
        if stats.top_emojis:
            top_emoji, count = stats.top_emojis[0]
            awards.append(Award(
                title=f"{top_emoji} SPECIALIST",
                description="Favorite emoji",
                value=f"Used {count} times"
            ))

        return awards

    def generate_tagline(self, name: str) -> str:
        """Generate a witty tagline for a participant."""
        stats = self.analytics.participant_stats.get(name)
        if not stats:
            return "Mystery Member"

        # Quick LLM call for tagline
        messages = self.chat.messages_by_sender.get(name, [])
        sample = self._sample_messages(messages, n=10)
        messages_text = self._format_messages_for_llm(sample)

        prompt = f"""Based on these messages and stats, write a SHORT witty tagline (5-8 words max) for {name}.

Stats: {stats.total_messages} messages, {stats.url_count} links, {stats.emoji_count} emojis

Sample messages:
{messages_text}

Tagline:"""

        try:
            return self.client.generate(
                prompt,
                system_prompt="You write punchy, memorable taglines. Think Twitter bio energy.",
                temperature=0.9,
                max_tokens=30
            ).strip().strip('"')
        except Exception:
            return "Living their best chat life"

    def generate_participant_wrapped(self, name: str) -> ParticipantWrapped:
        """Generate complete Wrapped for a participant."""
        stats = self.analytics.participant_stats.get(name)
        if not stats:
            return ParticipantWrapped(name=name, stats=ParticipantStats(name=name))

        wrapped = ParticipantWrapped(name=name, stats=stats)
        wrapped.personality_summary = self.generate_personality_summary(name)
        wrapped.top_topics = self.generate_top_topics(name)
        wrapped.memorable_quotes = self.find_memorable_quotes(name)
        wrapped.awards = self.generate_awards(name)
        wrapped.tagline = self.generate_tagline(name)

        return wrapped

    def generate_group_vibe(self) -> str:
        """Generate overall group vibe description."""
        # Sample messages from all participants
        sample = self._sample_messages(self.chat.messages, n=50)
        messages_text = self._format_messages_for_llm(sample)

        gs = self.analytics.group_stats
        context = f"""
Group chat with {gs.total_participants} people
{gs.total_messages:,} total messages over {gs.date_range[1] - gs.date_range[0] if gs.date_range else 'unknown'} days
Most active: {gs.most_active_day}s at {gs.most_active_hour}:00
"""

        prompt = f"""Based on these group chat messages, describe the group's overall VIBE in 2-3 fun sentences. What kind of friend group is this? What energy do they bring?
{context}
Sample messages from the group:
{messages_text}

Group vibe (2-3 sentences, fun and specific):"""

        try:
            return self.client.generate(
                prompt,
                system_prompt="You describe group dynamics in a fun, Spotify Wrapped style. Be specific about the vibe, not generic.",
                temperature=0.8
            ).strip()
        except Exception:
            return "A legendary group chat with unmatched energy!"

    def generate_group_wrapped(self, chat_name: str = "The Group Chat") -> GroupWrapped:
        """Generate complete Wrapped for the group."""
        wrapped = GroupWrapped(chat_name=chat_name)
        wrapped.vibe_check = self.generate_group_vibe()

        # Compile awards ceremony
        for name in self.chat.participants:
            awards = self.generate_awards(name)
            for award in awards:
                wrapped.awards_ceremony.append((name, award))

        # Generate summary
        gs = self.analytics.group_stats
        if gs.date_range:
            days = (gs.date_range[1] - gs.date_range[0]).days
            wrapped.summary = (
                f"{gs.total_messages:,} messages over {days} days. "
                f"That's {gs.total_messages // max(days, 1)} messages per day!"
            )

        return wrapped


if __name__ == '__main__':
    import sys
    from parser import parse_chat
    from analytics import analyze_chat

    if len(sys.argv) < 2:
        print("Usage: python wrapped.py <chat_file>")
        sys.exit(1)

    print("Parsing chat...")
    chat = parse_chat(sys.argv[1])

    print("Computing analytics...")
    analytics = analyze_chat(chat)

    print("Generating Wrapped (this may take a moment)...")
    generator = WrappedGenerator(chat, analytics)

    # Generate for first participant as test
    name = chat.participants[0]
    print(f"\nGenerating Wrapped for {name}...")
    wrapped = generator.generate_participant_wrapped(name)

    print(f"\n=== {name}'s WRAPPED ===")
    print(f"Tagline: {wrapped.tagline}")
    print(f"\nPersonality: {wrapped.personality_summary}")
    print(f"\nTop Topics: {', '.join(wrapped.top_topics)}")
    print(f"\nMemorable Quotes:")
    for quote in wrapped.memorable_quotes:
        print(f"  \"{quote}\"")
    print(f"\nAwards:")
    for award in wrapped.awards:
        print(f"  {award.title}: {award.description} ({award.value})")
