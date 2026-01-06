"""WhatsApp chat export parser."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Message:
    """Represents a single WhatsApp message."""
    timestamp: datetime
    sender: str
    content: str
    is_media: bool = False
    is_edited: bool = False

    @property
    def text_only(self) -> str:
        """Return content without edit markers and URLs."""
        text = self.content
        text = re.sub(r'<This message was edited>', '', text)
        text = re.sub(r'https?://\S+', '', text)
        return text.strip()


@dataclass
class Chat:
    """Represents a parsed WhatsApp chat."""
    messages: list[Message]
    participants: list[str]

    @property
    def messages_by_sender(self) -> dict[str, list[Message]]:
        """Group messages by sender."""
        by_sender: dict[str, list[Message]] = {}
        for msg in self.messages:
            if msg.sender not in by_sender:
                by_sender[msg.sender] = []
            by_sender[msg.sender].append(msg)
        return by_sender


# Regex to match WhatsApp message header
# Format: [M/D/YY, HH:MM:SS] Name: Message
MESSAGE_PATTERN = re.compile(
    r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}:\d{2})\]\s*([^:]+):\s*(.*)$'
)

# Alternative format without seconds: [M/D/YY, HH:MM] Name: Message
MESSAGE_PATTERN_NO_SECONDS = re.compile(
    r'^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\]\s*([^:]+):\s*(.*)$'
)

# Media indicators
MEDIA_INDICATORS = [
    'image omitted',
    'video omitted',
    'audio omitted',
    'sticker omitted',
    'document omitted',
    'GIF omitted',
    'Contact card omitted',
]


def parse_timestamp(date_str: str, time_str: str) -> datetime:
    """Parse date and time strings into a datetime object."""
    # Handle different date formats
    date_parts = date_str.split('/')
    month, day = int(date_parts[0]), int(date_parts[1])
    year = int(date_parts[2])

    # Handle 2-digit years
    if year < 100:
        year += 2000

    # Handle time with or without seconds
    time_parts = time_str.split(':')
    hour, minute = int(time_parts[0]), int(time_parts[1])
    second = int(time_parts[2]) if len(time_parts) > 2 else 0

    return datetime(year, month, day, hour, minute, second)


def is_media_message(content: str) -> bool:
    """Check if message content indicates media."""
    content_lower = content.lower().strip()
    # Check for media omitted markers (with or without special chars)
    cleaned = re.sub(r'[^\w\s]', '', content_lower)
    for indicator in MEDIA_INDICATORS:
        if indicator.lower().replace(' ', '') in cleaned.replace(' ', ''):
            return True
    return False


def parse_chat(file_path: str | Path) -> Chat:
    """Parse a WhatsApp chat export file."""
    file_path = Path(file_path)

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    messages: list[Message] = []
    participants: set[str] = set()
    current_message: Message | None = None

    for line in lines:
        line = line.rstrip('\n')

        # Try to match message header
        match = MESSAGE_PATTERN.match(line)
        if not match:
            match = MESSAGE_PATTERN_NO_SECONDS.match(line)

        if match:
            # Save previous message if exists
            if current_message:
                messages.append(current_message)

            date_str, time_str, sender, content = match.groups()
            sender = sender.strip()
            content = content.strip()

            # Handle special invisible character at start
            if content.startswith('\u200e'):
                content = content[1:]

            timestamp = parse_timestamp(date_str, time_str)
            is_media = is_media_message(content)
            is_edited = '<This message was edited>' in content

            current_message = Message(
                timestamp=timestamp,
                sender=sender,
                content=content,
                is_media=is_media,
                is_edited=is_edited
            )
            participants.add(sender)

        elif current_message:
            # Continuation of previous message (multi-line)
            current_message.content += '\n' + line

    # Don't forget the last message
    if current_message:
        messages.append(current_message)

    return Chat(
        messages=messages,
        participants=sorted(participants)
    )


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser.py <chat_file>")
        sys.exit(1)

    chat = parse_chat(sys.argv[1])
    print(f"Parsed {len(chat.messages)} messages from {len(chat.participants)} participants")
    print(f"Participants: {', '.join(chat.participants)}")

    for sender, msgs in chat.messages_by_sender.items():
        print(f"  {sender}: {len(msgs)} messages")
