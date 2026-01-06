"""Wrapped content generator using LLM and search."""

import random
from dataclasses import dataclass, field

from analytics import ChatAnalytics, ParticipantStats
from features import ChatFeatures, PersonalityProfile, ConversationThread, TopicTimeline
from lm_studio import LMStudioClient, get_client
from parser import Chat, Message
from search import MessageSearcher


@dataclass
class Achievement:
    """A video-game style achievement for a participant."""
    emoji: str
    title: str
    description: str


@dataclass
class ParticipantWrapped:
    """Wrapped summary for a single participant."""
    name: str
    stats: ParticipantStats
    personality_summary: str = ""
    top_topics: list[str] = field(default_factory=list)
    memorable_quotes: list[str] = field(default_factory=list)
    achievements: list[Achievement] = field(default_factory=list)
    fun_fact: str = ""
    tagline: str = ""
    # New: personality profile from features
    personality_profile: PersonalityProfile | None = None


@dataclass
class GroupWrapped:
    """Wrapped summary for the entire group."""
    chat_name: str
    summary: str = ""
    vibe_check: str = ""
    top_moments: list[str] = field(default_factory=list)
    group_personality: str = ""
    achievements_ceremony: list[tuple[str, Achievement]] = field(default_factory=list)
    # New: from features
    topic_timeline: TopicTimeline | None = None
    top_threads: list[ConversationThread] = field(default_factory=list)


class WrappedGenerator:
    """Generates Wrapped content using LLM and analytics."""

    def __init__(
        self,
        chat: Chat,
        analytics: ChatAnalytics,
        client: LMStudioClient | None = None,
        features: ChatFeatures | None = None
    ):
        self.chat = chat
        self.analytics = analytics
        self.client = client or get_client()
        self.searcher = MessageSearcher(chat.messages, self.client)
        self.features = features  # Optional deep features

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

    def find_memorable_quotes(self, name: str, n: int = 5) -> list[str]:
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

    def generate_achievements(self, name: str) -> list[Achievement]:
        """Generate video-game style achievements based on statistics."""
        stats = self.analytics.participant_stats.get(name)
        if not stats:
            return []

        achievements = []
        analytics = self.analytics

        # Message volume achievements
        if name == analytics.get_top_chatter():
            achievements.append(Achievement(
                emoji="🗣️",
                title="CHAT CHAMPION",
                description=f"Typed {stats.total_messages:,} messages—more than a NaNoWriMo novel"
            ))
        else:
            # Check if they're the quietest
            all_counts = [s.total_messages for s in analytics.participant_stats.values()]
            if stats.total_messages == min(all_counts):
                achievements.append(Achievement(
                    emoji="🤫",
                    title="LURKER LORD",
                    description="Fewest messages but always watching from the shadows"
                ))

        # Message length achievements
        if name == analytics.get_novelist():
            achievements.append(Achievement(
                emoji="✍️",
                title="ESSAYIST",
                description=f"Avg {stats.avg_message_length:.0f} chars/msg—TL;DR is your middle name"
            ))
        else:
            # Check if shortest messages
            all_lengths = [s.avg_message_length for s in analytics.participant_stats.values()]
            if stats.avg_message_length == min(all_lengths):
                achievements.append(Achievement(
                    emoji="⚡",
                    title="SPEED TEXTER",
                    description="Short and sweet—why use many word when few do trick?"
                ))

        # Time-based achievements
        if stats.is_night_owl:
            achievements.append(Achievement(
                emoji="🦉",
                title="NIGHT OWL",
                description=f"Still going strong at {stats.most_active_hour}:00—sleep is for the weak"
            ))

        if stats.is_early_bird:
            achievements.append(Achievement(
                emoji="🌅",
                title="EARLY BIRD",
                description=f"Up and texting by {stats.most_active_hour}:00—catches all the worms"
            ))

        # Check for weekend warrior (more messages on weekends)
        if stats.messages_by_weekday:
            weekend = stats.messages_by_weekday.get('Saturday', 0) + stats.messages_by_weekday.get('Sunday', 0)
            weekday = sum(v for k, v in stats.messages_by_weekday.items() if k not in ['Saturday', 'Sunday'])
            if weekend > 0 and weekday > 0 and (weekend / 2) > (weekday / 5):
                achievements.append(Achievement(
                    emoji="📅",
                    title="WEEKEND WARRIOR",
                    description="Party mode activated on Saturdays and Sundays"
                ))

        # Content-based achievements
        if name == analytics.get_link_lord():
            achievements.append(Achievement(
                emoji="🔗",
                title="LINK DEALER",
                description=f"Shared {stats.url_count} links—the group's personal curator"
            ))

        if stats.media_count > 50:
            achievements.append(Achievement(
                emoji="🎬",
                title="MEDIA MOGUL",
                description=f"Dropped {stats.media_count} images/videos—worth a thousand words each"
            ))

        # Conversation starter achievement
        if name == analytics.get_conversation_catalyst():
            achievements.append(Achievement(
                emoji="🎤",
                title="CONVERSATION STARTER",
                description=f"Broke {stats.conversation_starts} silences—always bringing the energy"
            ))

        # Use LLM to generate a fun personalized achievement
        llm_achievement = self._generate_llm_achievement(name, stats)
        if llm_achievement:
            achievements.append(llm_achievement)

        # Limit to 3-5 achievements
        return achievements[:5]

    def _generate_llm_achievement(self, name: str, stats: ParticipantStats) -> Achievement | None:
        """Use LLM to generate a fun, personalized achievement."""
        messages = self.chat.messages_by_sender.get(name, [])
        if not messages:
            return None

        sample = self._sample_messages(messages, n=30)
        messages_text = self._format_messages_for_llm(sample)

        prompt = f"""Based on these messages from {name}, create ONE funny video-game style achievement for them.

Sample messages:
{messages_text}

The achievement should be:
- Based on their personality/communication style (sarcastic? supportive? dramatic? nerdy?)
- Funny and specific to something you notice in their messages
- Formatted as: EMOJI|TITLE|DESCRIPTION

Examples:
💀|ROAST MASTER|Delivered burns so sick they need aloe vera
🎭|DRAMA MONARCH|Every story is an epic saga with twists
🧠|WIKIPEDIA BRAIN|Always dropping random knowledge bombs
🌶️|SPICY TAKE SPECIALIST|Hot opinions served fresh daily
👻|PHANTOM|Disappears for weeks then drops a novel

Output ONE achievement in the format EMOJI|TITLE|DESCRIPTION (no extra text):"""

        try:
            response = self.client.generate(
                prompt,
                system_prompt="You create funny, specific video-game achievements. Output exactly one achievement in EMOJI|TITLE|DESCRIPTION format.",
                temperature=0.9,
                max_tokens=100
            ).strip()

            # Parse the response
            parts = response.split('|')
            if len(parts) >= 3:
                return Achievement(
                    emoji=parts[0].strip(),
                    title=parts[1].strip().upper(),
                    description=parts[2].strip()
                )
        except Exception:
            pass

        return None

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
        wrapped.achievements = self.generate_achievements(name)
        wrapped.tagline = self.generate_tagline(name)

        # Add personality profile from features if available
        if self.features and name in self.features.personality_profiles:
            wrapped.personality_profile = self.features.personality_profiles[name]

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

        # Compile achievements ceremony
        for name in self.chat.participants:
            achievements = self.generate_achievements(name)
            for achievement in achievements:
                wrapped.achievements_ceremony.append((name, achievement))

        # Generate summary
        gs = self.analytics.group_stats
        if gs.date_range:
            days = (gs.date_range[1] - gs.date_range[0]).days
            wrapped.summary = (
                f"{gs.total_messages:,} messages over {days} days. "
                f"That's {gs.total_messages // max(days, 1)} messages per day!"
            )

        # Add features if available
        if self.features:
            wrapped.topic_timeline = self.features.topic_timeline
            wrapped.top_threads = self.features.top_threads

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
    print(f"\nAchievements:")
    for ach in wrapped.achievements:
        print(f"  {ach.emoji} {ach.title}: {ach.description}")
