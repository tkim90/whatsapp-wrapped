"""Analytics engine for computing chat statistics."""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from parser import Chat, Message


# Common emoji pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U00002600-\U000026FF"  # misc symbols
    "]+",
    flags=re.UNICODE
)

URL_PATTERN = re.compile(r'https?://\S+')


@dataclass
class ParticipantStats:
    """Statistics for a single participant."""
    name: str
    total_messages: int = 0
    total_words: int = 0
    total_characters: int = 0
    media_count: int = 0
    edited_count: int = 0
    url_count: int = 0
    emoji_count: int = 0
    top_emojis: list[tuple[str, int]] = field(default_factory=list)
    messages_by_hour: dict[int, int] = field(default_factory=dict)
    messages_by_day: dict[str, int] = field(default_factory=dict)
    conversation_starts: int = 0
    avg_message_length: float = 0.0
    longest_message: Message | None = None
    first_message_date: datetime | None = None
    last_message_date: datetime | None = None
    most_active_hour: int = 0
    most_active_day: str = ""

    # Computed properties for awards
    @property
    def is_night_owl(self) -> bool:
        """Check if most active between midnight and 5am."""
        night_messages = sum(self.messages_by_hour.get(h, 0) for h in range(0, 5))
        total = sum(self.messages_by_hour.values())
        return total > 0 and (night_messages / total) > 0.15

    @property
    def is_early_bird(self) -> bool:
        """Check if most active between 5am and 8am."""
        morning_messages = sum(self.messages_by_hour.get(h, 0) for h in range(5, 8))
        total = sum(self.messages_by_hour.values())
        return total > 0 and (morning_messages / total) > 0.15


@dataclass
class GroupStats:
    """Statistics for the entire group chat."""
    total_messages: int = 0
    total_words: int = 0
    total_participants: int = 0
    date_range: tuple[datetime, datetime] | None = None
    most_active_day: str = ""
    most_active_hour: int = 0
    busiest_date: str = ""
    busiest_date_count: int = 0
    messages_by_hour: dict[int, int] = field(default_factory=dict)
    messages_by_weekday: dict[str, int] = field(default_factory=dict)


def extract_emojis(text: str) -> list[str]:
    """Extract all emojis from text."""
    return EMOJI_PATTERN.findall(text)


def count_words(text: str) -> int:
    """Count words in text."""
    # Remove URLs and count remaining words
    text = URL_PATTERN.sub('', text)
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def compute_participant_stats(name: str, messages: list[Message]) -> ParticipantStats:
    """Compute statistics for a single participant."""
    stats = ParticipantStats(name=name)
    stats.total_messages = len(messages)

    if not messages:
        return stats

    emoji_counter: Counter[str] = Counter()
    messages_by_hour: Counter[int] = Counter()
    messages_by_day: Counter[str] = Counter()

    for msg in messages:
        # Word and character counts
        word_count = count_words(msg.content)
        stats.total_words += word_count
        stats.total_characters += len(msg.content)

        # Media and edits
        if msg.is_media:
            stats.media_count += 1
        if msg.is_edited:
            stats.edited_count += 1

        # URLs
        urls = URL_PATTERN.findall(msg.content)
        stats.url_count += len(urls)

        # Emojis
        emojis = extract_emojis(msg.content)
        stats.emoji_count += len(emojis)
        emoji_counter.update(emojis)

        # Time patterns
        messages_by_hour[msg.timestamp.hour] += 1
        day_key = msg.timestamp.strftime('%Y-%m-%d')
        messages_by_day[day_key] += 1

        # Longest message
        if stats.longest_message is None or len(msg.content) > len(stats.longest_message.content):
            stats.longest_message = msg

    # Store counters
    stats.messages_by_hour = dict(messages_by_hour)
    stats.messages_by_day = dict(messages_by_day)

    # Top emojis
    stats.top_emojis = emoji_counter.most_common(10)

    # Averages
    stats.avg_message_length = stats.total_characters / stats.total_messages

    # Date range
    sorted_msgs = sorted(messages, key=lambda m: m.timestamp)
    stats.first_message_date = sorted_msgs[0].timestamp
    stats.last_message_date = sorted_msgs[-1].timestamp

    # Most active hour
    if messages_by_hour:
        stats.most_active_hour = max(messages_by_hour, key=lambda h: messages_by_hour[h])

    # Most active day
    if messages_by_day:
        stats.most_active_day = max(messages_by_day, key=lambda d: messages_by_day[d])

    return stats


def compute_conversation_starts(
    chat: Chat,
    gap_threshold: timedelta = timedelta(hours=2)
) -> dict[str, int]:
    """
    Count how many times each participant started a conversation.
    A conversation start is defined as a message after a gap of gap_threshold.
    """
    starts: Counter[str] = Counter()

    sorted_messages = sorted(chat.messages, key=lambda m: m.timestamp)

    for i, msg in enumerate(sorted_messages):
        if i == 0:
            starts[msg.sender] += 1
            continue

        prev_msg = sorted_messages[i - 1]
        gap = msg.timestamp - prev_msg.timestamp

        if gap >= gap_threshold:
            starts[msg.sender] += 1

    return dict(starts)


def compute_group_stats(chat: Chat) -> GroupStats:
    """Compute statistics for the entire group."""
    stats = GroupStats()
    stats.total_messages = len(chat.messages)
    stats.total_participants = len(chat.participants)

    if not chat.messages:
        return stats

    messages_by_hour: Counter[int] = Counter()
    messages_by_weekday: Counter[str] = Counter()
    messages_by_date: Counter[str] = Counter()

    for msg in chat.messages:
        stats.total_words += count_words(msg.content)
        messages_by_hour[msg.timestamp.hour] += 1
        messages_by_weekday[msg.timestamp.strftime('%A')] += 1
        messages_by_date[msg.timestamp.strftime('%Y-%m-%d')] += 1

    stats.messages_by_hour = dict(messages_by_hour)
    stats.messages_by_weekday = dict(messages_by_weekday)

    # Date range
    sorted_msgs = sorted(chat.messages, key=lambda m: m.timestamp)
    stats.date_range = (sorted_msgs[0].timestamp, sorted_msgs[-1].timestamp)

    # Most active patterns
    if messages_by_hour:
        stats.most_active_hour = max(messages_by_hour, key=lambda h: messages_by_hour[h])
    if messages_by_weekday:
        stats.most_active_day = max(messages_by_weekday, key=lambda d: messages_by_weekday[d])
    if messages_by_date:
        stats.busiest_date = max(messages_by_date, key=lambda d: messages_by_date[d])
        stats.busiest_date_count = messages_by_date[stats.busiest_date]

    return stats


@dataclass
class ChatAnalytics:
    """Complete analytics for a chat."""
    group_stats: GroupStats
    participant_stats: dict[str, ParticipantStats]
    conversation_starts: dict[str, int]

    def get_top_chatter(self) -> str:
        """Get the participant with most messages."""
        return max(
            self.participant_stats.values(),
            key=lambda s: s.total_messages
        ).name

    def get_link_lord(self) -> str:
        """Get the participant who shared most URLs."""
        return max(
            self.participant_stats.values(),
            key=lambda s: s.url_count
        ).name

    def get_emoji_enthusiast(self) -> str:
        """Get the participant who used most emojis."""
        return max(
            self.participant_stats.values(),
            key=lambda s: s.emoji_count
        ).name

    def get_conversation_catalyst(self) -> str:
        """Get the participant who started most conversations."""
        return max(self.conversation_starts, key=lambda n: self.conversation_starts[n])

    def get_novelist(self) -> str:
        """Get the participant with longest average messages."""
        return max(
            self.participant_stats.values(),
            key=lambda s: s.avg_message_length
        ).name

    def get_night_owls(self) -> list[str]:
        """Get participants who are night owls."""
        return [
            s.name for s in self.participant_stats.values()
            if s.is_night_owl
        ]


def analyze_chat(chat: Chat) -> ChatAnalytics:
    """Perform complete analysis on a chat."""
    group_stats = compute_group_stats(chat)

    participant_stats = {}
    for sender, messages in chat.messages_by_sender.items():
        participant_stats[sender] = compute_participant_stats(sender, messages)

    conversation_starts = compute_conversation_starts(chat)

    # Update participant stats with conversation starts
    for name, count in conversation_starts.items():
        if name in participant_stats:
            participant_stats[name].conversation_starts = count

    return ChatAnalytics(
        group_stats=group_stats,
        participant_stats=participant_stats,
        conversation_starts=conversation_starts
    )


if __name__ == '__main__':
    import sys
    from parser import parse_chat

    if len(sys.argv) < 2:
        print("Usage: python analytics.py <chat_file>")
        sys.exit(1)

    chat = parse_chat(sys.argv[1])
    analytics = analyze_chat(chat)

    print(f"=== Group Stats ===")
    print(f"Total messages: {analytics.group_stats.total_messages:,}")
    print(f"Total words: {analytics.group_stats.total_words:,}")
    print(f"Participants: {analytics.group_stats.total_participants}")
    if analytics.group_stats.date_range:
        start, end = analytics.group_stats.date_range
        print(f"Date range: {start.date()} to {end.date()}")
    print(f"Most active hour: {analytics.group_stats.most_active_hour}:00")
    print(f"Most active day: {analytics.group_stats.most_active_day}")

    print(f"\n=== Participant Stats ===")
    for name, stats in sorted(
        analytics.participant_stats.items(),
        key=lambda x: x[1].total_messages,
        reverse=True
    ):
        print(f"\n{name}:")
        print(f"  Messages: {stats.total_messages:,}")
        print(f"  Words: {stats.total_words:,}")
        print(f"  URLs shared: {stats.url_count}")
        print(f"  Emojis used: {stats.emoji_count}")
        print(f"  Avg message length: {stats.avg_message_length:.1f} chars")
        print(f"  Most active hour: {stats.most_active_hour}:00")
        if stats.top_emojis:
            top_3 = ' '.join(e for e, c in stats.top_emojis[:3])
            print(f"  Top emojis: {top_3}")

    print(f"\n=== Awards ===")
    print(f"Top Chatter: {analytics.get_top_chatter()}")
    print(f"Link Lord: {analytics.get_link_lord()}")
    print(f"Emoji Enthusiast: {analytics.get_emoji_enthusiast()}")
    print(f"Conversation Catalyst: {analytics.get_conversation_catalyst()}")
    print(f"The Novelist: {analytics.get_novelist()}")
