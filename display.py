"""Display system for Spotify Wrapped-style terminal output."""

import time
from io import StringIO
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align
from rich.style import Style
from rich.box import HEAVY, DOUBLE, ROUNDED, ASCII

from analytics import ChatAnalytics, ParticipantStats
from features import TopicTimeline, ConversationThread, PersonalityProfile
from wrapped import ParticipantWrapped, GroupWrapped, Achievement


console = Console()

# File output console (no colors, for text file export)
_file_console: Console | None = None


# Color palette (Spotify Wrapped inspired)
COLORS = {
    'primary': '#1DB954',      # Spotify green
    'secondary': '#191414',    # Dark
    'accent1': '#FF6B6B',      # Coral
    'accent2': '#4ECDC4',      # Teal
    'accent3': '#FFE66D',      # Yellow
    'accent4': '#A855F7',      # Purple
    'accent5': '#F472B6',      # Pink
    'text': '#FFFFFF',
}

PARTICIPANT_COLORS = [
    '#FF6B6B',  # Coral
    '#4ECDC4',  # Teal
    '#FFE66D',  # Yellow
    '#A855F7',  # Purple
    '#F472B6',  # Pink
    '#60A5FA',  # Blue
    '#34D399',  # Emerald
]

# Characters for distinguishing participants in plain text output
PARTICIPANT_CHARS = ['█', '▓', '▒', '░', '#', '=', '*', '+']


def get_participant_char(index: int) -> str:
    """Get a character for a participant by index (for plain text output)."""
    return PARTICIPANT_CHARS[index % len(PARTICIPANT_CHARS)]


def get_participant_color(index: int) -> str:
    """Get a color for a participant by index."""
    return PARTICIPANT_COLORS[index % len(PARTICIPANT_COLORS)]


def dramatic_pause(seconds: float = 0.5) -> None:
    """Add a dramatic pause for effect."""
    time.sleep(seconds)


def clear_screen() -> None:
    """Clear the terminal screen."""
    console.clear()


def print_header() -> None:
    """Print the main Wrapped header."""
    header_art = """
    ░██╗░░░░░░░██╗██╗░░██╗░█████╗░████████╗░██████╗░█████╗░██████╗░██████╗░
    ░██║░░██╗░░██║██║░░██║██╔══██╗╚══██╔══╝██╔════╝██╔══██╗██╔══██╗██╔══██╗
    ░╚██╗████╗██╔╝███████║███████║░░░██║░░░╚█████╗░███████║██████╔╝██████╔╝
    ░░████╔═████║░██╔══██║██╔══██║░░░██║░░░░╚═══██╗██╔══██║██╔═══╝░██╔═══╝░
    ░░╚██╔╝░╚██╔╝░██║░░██║██║░░██║░░░██║░░░██████╔╝██║░░██║██║░░░░░██║░░░░░
    ░░░╚═╝░░░╚═╝░░╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░╚═════╝░╚═╝░░╚═╝╚═╝░░░░░╚═╝░░░░░
    """

    wrapped_text = """
    ░██╗░░░░░░░██╗██████╗░░█████╗░██████╗░██████╗░███████╗██████╗░
    ░██║░░██╗░░██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
    ░╚██╗████╗██╔╝██████╔╝███████║██████╔╝██████╔╝█████╗░░██║░░██║
    ░░████╔═████║░██╔══██╗██╔══██║██╔═══╝░██╔═══╝░██╔══╝░░██║░░██║
    ░░╚██╔╝░╚██╔╝░██║░░██║██║░░██║██║░░░░░██║░░░░░███████╗██████╔╝
    ░░░╚═╝░░░╚═╝░░╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░╚═╝░░░░░╚══════╝╚═════╝░
    """

    console.print()
    console.print(Text(header_art, style=f"bold {COLORS['primary']}"))
    console.print(Text(wrapped_text, style=f"bold {COLORS['accent3']}"))
    console.print()
    console.print(
        Align.center(Text("2 0 2 5", style=f"bold {COLORS['accent1']} on {COLORS['secondary']}")),
    )
    console.print()


def print_section_header(title: str, color: str = COLORS['primary']) -> None:
    """Print a section header."""
    console.print()
    console.rule(f"[bold {color}]{title}[/]", style=color)
    console.print()


def print_big_stat(label: str, value: str, color: str = COLORS['primary']) -> None:
    """Print a big statistic dramatically."""
    console.print()
    console.print(Align.center(Text(label, style="dim italic")))
    dramatic_pause(0.3)
    console.print(Align.center(Text(value, style=f"bold {color}")))
    console.print()


def print_achievement(achievement: Achievement, color: str = COLORS['accent1']) -> None:
    """Print a video-game style achievement."""
    console.print(f"  [{color}]{achievement.emoji}  {achievement.title}[/]")
    console.print(f"      [dim]{achievement.description}[/]")
    console.print()


def print_quote(quote: str, color: str = COLORS['accent2']) -> None:
    """Print a memorable quote."""
    # Truncate very long quotes
    if len(quote) > 200:
        quote = quote[:197] + "..."

    console.print(f'  [italic {color}]"{quote}"[/]')


def print_participant_wrapped(wrapped: ParticipantWrapped, index: int = 0) -> None:
    """Print a participant's full Wrapped summary."""
    color = get_participant_color(index)
    name = wrapped.name
    first_name = name.split()[0]  # Use first name for labels

    # Big name reveal
    console.print()
    console.print(Align.center(Text(f"{name.upper()}'S WRAPPED", style="dim italic")))
    dramatic_pause(0.5)

    name_art = f"""
    ╔{'═' * (len(name) + 4)}╗
    ║  {name.upper()}  ║
    ╚{'═' * (len(name) + 4)}╝
    """
    console.print(Align.center(Text(name_art, style=f"bold {color}")))

    # Tagline
    if wrapped.tagline:
        console.print(Align.center(Text(f'"{wrapped.tagline}"', style="italic dim")))

    dramatic_pause(0.3)

    # Stats grid
    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column("stat", style="dim")
    stats_table.add_column("value", style=f"bold {color}")

    stats = wrapped.stats
    stats_table.add_row("Messages", f"{stats.total_messages:,}")
    stats_table.add_row("Words", f"{stats.total_words:,}")
    stats_table.add_row("Links Shared", f"{stats.url_count}")
    stats_table.add_row("Avg Length", f"{stats.avg_message_length:.0f} chars")

    console.print()
    console.print(Align.center(stats_table))

    # Personality
    if wrapped.personality_summary:
        console.print()
        print_section_header(f"{first_name.upper()}'S VIBE", color)
        console.print(Panel(
            f"[italic]{wrapped.personality_summary}[/]",
            box=ROUNDED,
            border_style=color,
            padding=(1, 2),
        ))

    # Top topics
    if wrapped.top_topics:
        console.print()
        print_section_header(f"{first_name.upper()} TALKED ABOUT", color)
        for i, topic in enumerate(wrapped.top_topics, 1):
            console.print(f"  [{color}]{i}.[/] {topic}")

    # Memorable quotes
    if wrapped.memorable_quotes:
        console.print()
        print_section_header(f"{first_name.upper()}'S GREATEST HITS", color)
        for quote in wrapped.memorable_quotes:
            print_quote(quote, color)
            console.print()

    # Achievements
    if wrapped.achievements:
        console.print()
        print_section_header(f"{first_name.upper()}'S ACHIEVEMENTS UNLOCKED 🏆", color)
        for achievement in wrapped.achievements:
            print_achievement(achievement, color)

    # Personality archetype (from features)
    if wrapped.personality_profile:
        print_personality_archetype(wrapped.personality_profile, color, first_name)

    console.print()
    console.rule(style="dim")


def print_group_wrapped(wrapped: GroupWrapped, analytics: ChatAnalytics) -> None:
    """Print the group's Wrapped summary."""
    color = COLORS['primary']

    print_section_header(f"{wrapped.chat_name.upper()} WRAPPED", color)

    # Summary stats
    if wrapped.summary:
        console.print(Panel(
            f"[bold {color}]{wrapped.summary}[/]",
            box=DOUBLE,
            border_style=color,
        ))

    # Vibe check
    if wrapped.vibe_check:
        console.print()
        print_section_header("THE VIBE CHECK", COLORS['accent4'])
        console.print(Panel(
            f"[italic]{wrapped.vibe_check}[/]",
            box=ROUNDED,
            border_style=COLORS['accent4'],
            padding=(1, 2),
        ))

    # Group stats
    gs = analytics.group_stats
    console.print()
    print_section_header("BY THE NUMBERS", COLORS['accent2'])

    stats_table = Table(show_header=False, box=ROUNDED, border_style=COLORS['accent2'])
    stats_table.add_column("stat", style="dim")
    stats_table.add_column("value", style=f"bold {COLORS['accent2']}")

    stats_table.add_row("Total Messages", f"{gs.total_messages:,}")
    stats_table.add_row("Total Words", f"{gs.total_words:,}")
    stats_table.add_row("Participants", f"{gs.total_participants}")
    stats_table.add_row("Most Active Day", gs.most_active_day)
    stats_table.add_row("Peak Hour", f"{gs.most_active_hour}:00")
    if gs.busiest_date:
        stats_table.add_row("Busiest Day Ever", f"{gs.busiest_date} ({gs.busiest_date_count} msgs)")

    console.print(Align.center(stats_table))

    # Achievements ceremony
    if wrapped.achievements_ceremony:
        console.print()
        print_section_header("ACHIEVEMENTS UNLOCKED 🏆", COLORS['accent3'])

        for name, achievement in wrapped.achievements_ceremony:
            console.print(f"  [{COLORS['accent3']}]{achievement.emoji}  {achievement.title}[/] — [bold]{name}[/]")
            console.print(f"      [dim]{achievement.description}[/]")
            console.print()

    # Topic timeline (from features)
    if wrapped.topic_timeline:
        console.print()
        print_topic_timeline(wrapped.topic_timeline)

    # Top threads (from features)
    if wrapped.top_threads:
        console.print()
        print_top_threads(wrapped.top_threads)


def print_loading_screen() -> None:
    """Print a loading screen while processing."""
    with Progress(
        SpinnerColumn(style=COLORS['primary']),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[bold]Analyzing your chat history...", total=None)
        time.sleep(1)
        progress.update(task, description="[bold]Computing statistics...")
        time.sleep(0.5)
        progress.update(task, description="[bold]Generating insights with AI...")
        time.sleep(0.5)
        progress.update(task, description="[bold]Finding memorable moments...")
        time.sleep(0.5)
        progress.update(task, description="[bold]Preparing your Wrapped...")
        time.sleep(0.5)


def print_outro() -> None:
    """Print the outro message."""
    console.print()
    console.print(Panel(
        "[bold]Thanks for a great year of chatting![/]\n\n"
        "[dim]WhatsApp Wrapped 2025[/]",
        box=DOUBLE,
        border_style=COLORS['primary'],
        padding=(1, 2),
    ))
    console.print()


def print_divider() -> None:
    """Print a visual divider."""
    console.print()
    console.print(Align.center(Text("* * *", style=f"dim {COLORS['accent4']}")))
    console.print()


# ============================================================================
# New Feature Display Functions
# ============================================================================

def print_topic_timeline(timeline: TopicTimeline, color: str = COLORS['accent2']) -> None:
    """Print the topic timeline with monthly/yearly breakdown."""
    print_section_header("YOUR YEAR IN TOPICS", color)

    # Group by year for display
    months_by_year: dict[str, list[tuple[str, list[str]]]] = {}
    for month_key in sorted(timeline.topics_by_month.keys()):
        year = month_key[:4]
        if year not in months_by_year:
            months_by_year[year] = []
        months_by_year[year].append((month_key, timeline.topics_by_month[month_key]))

    for year in sorted(months_by_year.keys()):
        console.print(f"\n[bold {color}]{year}[/]")
        for month_key, topics in months_by_year[year]:
            # Format month name
            try:
                from datetime import datetime
                month_name = datetime.strptime(month_key, '%Y-%m').strftime('%B')
            except:
                month_name = month_key
            topics_str = ', '.join(topics[:4])  # Show top 4 topics
            console.print(f"  [dim]{month_name}:[/] {topics_str}")

    # Overall top topics
    if timeline.aggregate_topics:
        console.print()
        console.print(f"[bold {color}]Top Topics Overall:[/]")
        for i, topic in enumerate(timeline.aggregate_topics[:5], 1):
            console.print(f"  {i}. {topic}")


def print_top_threads(threads: list[ConversationThread], color: str = COLORS['accent1']) -> None:
    """Print the top conversation threads."""
    print_section_header("TOP 5 CONVERSATIONS THIS YEAR", color)

    thread_emojis = ["🔥", "💬", "⚡", "🎯", "💡"]

    for i, thread in enumerate(threads[:5]):
        emoji = thread_emojis[i] if i < len(thread_emojis) else "💬"
        date_str = thread.start_time.strftime('%b %d, %Y')

        console.print(f"\n[bold {color}]#{i+1} {emoji} {date_str}[/]")
        console.print(f"   [dim]{thread.message_count} messages over {thread.duration_minutes} minutes[/]")
        console.print(f"   [dim]Participants:[/] {', '.join(thread.participants)}")
        if thread.topic_summary:
            console.print(f"   [italic]About:[/] {thread.topic_summary}")


def print_personality_archetype(profile: PersonalityProfile, color: str = COLORS['accent4'], name: str = "") -> None:
    """Print personality archetype with dramatic reveal."""
    console.print()
    name_prefix = f"{name.upper()}'S" if name else "YOUR"
    print_section_header(f"{name_prefix} ARCHETYPE: {profile.archetype.upper()} {profile.archetype_emoji}", color)

    if profile.archetype_reason:
        console.print(Panel(
            f"[italic]{profile.archetype_reason}[/]",
            box=ROUNDED,
            border_style=color,
            padding=(1, 2),
        ))

    # Celebrity match
    if profile.celebrity_match:
        console.print()
        celeb_intro = f"If {name} were a celebrity..." if name else "If you were a celebrity..."
        console.print(Align.center(Text(celeb_intro, style="dim italic")))
        dramatic_pause(0.3)
        console.print(Align.center(Text(profile.celebrity_match, style=f"bold {COLORS['accent3']}")))
        if profile.celebrity_reason:
            console.print(Align.center(Text(f'"{profile.celebrity_reason}"', style="italic dim")))

    # Superpower
    if profile.superpower:
        console.print()
        possessive = f"{name}'s" if name else "Your"
        console.print(f"[bold {color}]{possessive} Superpower:[/] {profile.superpower}")


# ============================================================================
# Usage Graphs
# ============================================================================

def print_usage_graphs(participant_stats: dict[str, ParticipantStats], color: str = COLORS['accent2']) -> None:
    """Print ASCII bar graphs of group activity."""
    from datetime import datetime

    print_section_header("GROUP ACTIVITY BREAKDOWN", color)

    # Get all participants
    names = list(participant_stats.keys())
    short_names = [n.split()[0][:8] for n in names]  # First name, max 8 chars
    max_name_len = max(len(n) for n in short_names)

    # Define bar characters
    bar_char = "█"
    empty_char = "░"

    # 1. Messages per month (last 12 months)
    console.print(f"\n[bold {color}]MESSAGES PER MONTH (last 12 months)[/]")
    console.print()

    # Collect all months across all participants
    all_months: set[str] = set()
    for stats in participant_stats.values():
        all_months.update(stats.messages_by_month.keys())

    if all_months:
        sorted_months = sorted(all_months)[-12:]  # Last 12 months

        # Find max for scaling
        max_monthly = 1
        for stats in participant_stats.values():
            for month in sorted_months:
                max_monthly = max(max_monthly, stats.messages_by_month.get(month, 0))

        bar_width = 20  # Max bar width

        for month in sorted_months:
            try:
                month_label = datetime.strptime(month, '%Y-%m').strftime('%b %y')
            except:
                month_label = month

            console.print(f"  [dim]{month_label:>6}[/] ", end="")
            for i, (name, stats) in enumerate(participant_stats.items()):
                count = stats.messages_by_month.get(month, 0)
                bar_len = int((count / max_monthly) * bar_width) if max_monthly > 0 else 0
                bar = bar_char * bar_len
                p_color = get_participant_color(i)
                console.print(f"[{p_color}]{bar:<{bar_width}}[/] ", end="")
            console.print()

        # Legend
        console.print()
        console.print("  Legend: ", end="")
        for i, short_name in enumerate(short_names):
            p_color = get_participant_color(i)
            console.print(f"[{p_color}]{bar_char}{bar_char}[/] {short_name}  ", end="")
        console.print()

    # 2. Day of week activity
    console.print(f"\n[bold {color}]MOST ACTIVE DAYS[/]")
    console.print()

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_abbrevs = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

    # Find max for scaling
    max_daily = 1
    for stats in participant_stats.values():
        for day in days:
            max_daily = max(max_daily, stats.messages_by_weekday.get(day, 0))

    bar_width = 10

    for i, (name, stats) in enumerate(participant_stats.items()):
        p_color = get_participant_color(i)
        short_name = short_names[i]
        console.print(f"  [{p_color}]{short_name:>{max_name_len}}[/] ", end="")
        for day in days:
            count = stats.messages_by_weekday.get(day, 0)
            bar_len = int((count / max_daily) * bar_width) if max_daily > 0 else 0
            bar = bar_char * bar_len + empty_char * (bar_width - bar_len)
            console.print(f"[{p_color}]{bar}[/]", end="")
        console.print()

    # Day labels
    console.print(f"  {' ' * max_name_len} ", end="")
    for abbrev in day_abbrevs:
        console.print(f"[dim]{abbrev:^{bar_width}}[/]", end="")
    console.print()

    # 3. Peak hours
    console.print(f"\n[bold {color}]PEAK HOURS[/]")
    console.print()

    # Find max for scaling
    max_hourly = 1
    for stats in participant_stats.values():
        for hour in range(24):
            max_hourly = max(max_hourly, stats.messages_by_hour.get(hour, 0))

    # Show 24 hour timeline compressed
    for i, (name, stats) in enumerate(participant_stats.items()):
        p_color = get_participant_color(i)
        short_name = short_names[i]
        console.print(f"  [{p_color}]{short_name:>{max_name_len}}[/] ", end="")
        for hour in range(24):
            count = stats.messages_by_hour.get(hour, 0)
            intensity = count / max_hourly if max_hourly > 0 else 0
            if intensity > 0.7:
                char = "█"
            elif intensity > 0.4:
                char = "▓"
            elif intensity > 0.2:
                char = "▒"
            elif intensity > 0.05:
                char = "░"
            else:
                char = " "
            console.print(f"[{p_color}]{char}[/]", end="")
        console.print()

    # Hour labels
    console.print(f"  {' ' * max_name_len} [dim]0   3   6   9   12  15  18  21  24[/]")
    console.print()


def print_archetype_cards(
    profiles_and_stats: list[tuple[str, PersonalityProfile | None, ParticipantStats]]
) -> None:
    """Print all archetypes side-by-side as cards at the end."""
    print_section_header("THE SQUAD", COLORS['primary'])

    card_width = 23
    num_cards = len(profiles_and_stats)

    # Build card lines for each person
    all_card_lines: list[list[str]] = []

    for name, profile, stats in profiles_and_stats:
        lines = []
        first_name = name.split()[0]

        # Top border
        lines.append(f"╔{'═' * (card_width - 2)}╗")

        # Archetype line
        if profile:
            archetype_text = f"{profile.archetype_emoji} {profile.archetype.upper()}"
        else:
            archetype_text = "? MYSTERY"
        archetype_text = archetype_text[:card_width - 4].center(card_width - 4)
        lines.append(f"║ {archetype_text} ║")

        # Divider
        lines.append(f"╠{'═' * (card_width - 2)}╣")

        # Empty line
        lines.append(f"║{' ' * (card_width - 2)}║")

        # Name
        name_centered = first_name.upper().center(card_width - 4)
        lines.append(f"║ {name_centered} ║")

        # Empty line
        lines.append(f"║{' ' * (card_width - 2)}║")

        # Message count
        msg_text = f"{stats.total_messages:,} msgs"
        msg_centered = msg_text.center(card_width - 4)
        lines.append(f"║ {msg_centered} ║")

        # Empty line
        lines.append(f"║{' ' * (card_width - 2)}║")

        # Celebrity (truncated)
        if profile and profile.celebrity_match:
            # Extract just the name, truncate if needed
            celeb = profile.celebrity_match.split('–')[0].split('-')[0].strip()
            celeb = celeb.replace('**', '').strip()
            if len(celeb) > card_width - 6:
                celeb = celeb[:card_width - 9] + "..."
            celeb_centered = f'"{celeb}"'.center(card_width - 4)
        else:
            celeb_centered = '""'.center(card_width - 4)
        lines.append(f"║ {celeb_centered} ║")

        # Empty line
        lines.append(f"║{' ' * (card_width - 2)}║")

        # Bottom border
        lines.append(f"╚{'═' * (card_width - 2)}╝")

        all_card_lines.append(lines)

    # Print cards side by side
    num_lines = len(all_card_lines[0]) if all_card_lines else 0
    for line_idx in range(num_lines):
        line_parts = []
        for card_idx, card_lines in enumerate(all_card_lines):
            color = get_participant_color(card_idx)
            line_parts.append(f"[{color}]{card_lines[line_idx]}[/]")
        console.print("  " + "   ".join(line_parts))

    console.print()


# ============================================================================
# File Output Support
# ============================================================================

class WrappedRecorder:
    """Records Wrapped output for file export."""

    def __init__(self):
        self.lines: list[str] = []

    def add_header(self) -> None:
        """Add the header to recorded output."""
        self.lines.append(r"""
================================================================================
 __        ___   _    _  _____ ____    _    ____  ____   __        ______      _    ____  ____  _____ ____
 \ \      / / | | |  / \|_   _/ ___|  / \  |  _ \|  _ \  \ \      / /  _ \    / \  |  _ \|  _ \| ____|  _ \
  \ \ /\ / /| |_| | / _ \ | | \___ \ / _ \ | |_) | |_) |  \ \ /\ / /| |_) |  / _ \ | |_) | |_) |  _| | | | |
   \ V  V / |  _  |/ ___ \| |  ___) / ___ \|  __/|  __/    \ V  V / |  _ <  / ___ \|  __/|  __/| |___| |_| |
    \_/\_/  |_| |_/_/   \_\_| |____/_/   \_\_|   |_|        \_/\_/  |_| \_\/_/   \_\_|   |_|   |_____|____/

                                            2 0 2 5
================================================================================
""")

    def add_section(self, title: str) -> None:
        """Add a section header."""
        self.lines.append("")
        self.lines.append(f"{'=' * 80}")
        self.lines.append(f"  {title}")
        self.lines.append(f"{'=' * 80}")
        self.lines.append("")

    def add_subsection(self, title: str) -> None:
        """Add a subsection header."""
        self.lines.append("")
        self.lines.append(f"--- {title} ---")
        self.lines.append("")

    def add_line(self, text: str = "") -> None:
        """Add a line of text."""
        self.lines.append(text)

    def add_stat(self, label: str, value: str) -> None:
        """Add a statistic line."""
        self.lines.append(f"  {label}: {value}")

    def add_quote(self, quote: str) -> None:
        """Add a quote."""
        if len(quote) > 200:
            quote = quote[:197] + "..."
        self.lines.append(f'  "{quote}"')

    def add_achievement(self, achievement: Achievement) -> None:
        """Add an achievement."""
        self.lines.append(f"  {achievement.emoji}  {achievement.title}")
        self.lines.append(f"      {achievement.description}")
        self.lines.append("")

    def add_divider(self) -> None:
        """Add a visual divider."""
        self.lines.append("")
        self.lines.append("  * * *")
        self.lines.append("")

    def add_usage_graphs(self, participant_stats: dict[str, 'ParticipantStats']) -> None:
        """Add ASCII bar graphs of group activity for text output."""
        from datetime import datetime

        self.add_subsection("GROUP ACTIVITY BREAKDOWN")

        # Get all participants
        names = list(participant_stats.keys())
        short_names = [n.split()[0][:8] for n in names]  # First name, max 8 chars
        max_name_len = max(len(n) for n in short_names)

        # Get character for each participant
        participant_chars = [get_participant_char(i) for i in range(len(names))]

        # 1. Messages per month (last 12 months)
        self.add_line("MESSAGES PER MONTH (last 12 months)")
        self.add_line("")

        # Collect all months across all participants
        all_months: set[str] = set()
        for stats in participant_stats.values():
            all_months.update(stats.messages_by_month.keys())

        if all_months:
            sorted_months = sorted(all_months)[-12:]  # Last 12 months

            # Find max for scaling
            max_monthly = 1
            for stats in participant_stats.values():
                for month in sorted_months:
                    max_monthly = max(max_monthly, stats.messages_by_month.get(month, 0))

            bar_width = 15  # Max bar width per participant

            for month in sorted_months:
                try:
                    month_label = datetime.strptime(month, '%Y-%m').strftime('%b %y')
                except:
                    month_label = month

                line = f"  {month_label:>6} "
                for i, (name, stats) in enumerate(participant_stats.items()):
                    count = stats.messages_by_month.get(month, 0)
                    bar_len = int((count / max_monthly) * bar_width) if max_monthly > 0 else 0
                    char = participant_chars[i]
                    bar = char * bar_len
                    line += f"{bar:<{bar_width}} "
                self.add_line(line.rstrip())

            # Legend
            self.add_line("")
            legend = "  Legend: "
            for i, short_name in enumerate(short_names):
                char = participant_chars[i]
                legend += f"{char}{char} = {short_name}  "
            self.add_line(legend.rstrip())

        # 2. Day of week activity
        self.add_line("")
        self.add_line("MOST ACTIVE DAYS")
        self.add_line("")

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_abbrevs = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        # Find max for scaling
        max_daily = 1
        for stats in participant_stats.values():
            for day in days:
                max_daily = max(max_daily, stats.messages_by_weekday.get(day, 0))

        bar_width = 8

        for i, (name, stats) in enumerate(participant_stats.items()):
            short_name = short_names[i]
            char = participant_chars[i]
            empty_char = ' '
            line = f"  {short_name:>{max_name_len}} "
            for day in days:
                count = stats.messages_by_weekday.get(day, 0)
                bar_len = int((count / max_daily) * bar_width) if max_daily > 0 else 0
                bar = char * bar_len + empty_char * (bar_width - bar_len)
                line += bar
            self.add_line(line.rstrip())

        # Day labels
        label_line = f"  {' ' * max_name_len} "
        for abbrev in day_abbrevs:
            label_line += f"{abbrev:^{bar_width}}"
        self.add_line(label_line.rstrip())

        # 3. Peak hours
        self.add_line("")
        self.add_line("PEAK HOURS")
        self.add_line("")

        # Find max for scaling
        max_hourly = 1
        for stats in participant_stats.values():
            for hour in range(24):
                max_hourly = max(max_hourly, stats.messages_by_hour.get(hour, 0))

        # Show 24 hour timeline compressed
        for i, (name, stats) in enumerate(participant_stats.items()):
            short_name = short_names[i]
            char = participant_chars[i]
            line = f"  {short_name:>{max_name_len}} "
            for hour in range(24):
                count = stats.messages_by_hour.get(hour, 0)
                intensity = count / max_hourly if max_hourly > 0 else 0
                if intensity > 0.7:
                    line += char
                elif intensity > 0.4:
                    line += char
                elif intensity > 0.2:
                    line += '·'
                elif intensity > 0.05:
                    line += '.'
                else:
                    line += ' '
            self.add_line(line.rstrip())

        # Hour labels
        self.add_line(f"  {' ' * max_name_len} 0   3   6   9   12  15  18  21  24")
        self.add_line("")

    def add_topic_timeline(self, timeline: TopicTimeline) -> None:
        """Record topic timeline output."""
        self.add_subsection("YOUR YEAR IN TOPICS")

        # Group by year
        from datetime import datetime
        months_by_year: dict[str, list[tuple[str, list[str]]]] = {}
        for month_key in sorted(timeline.topics_by_month.keys()):
            year = month_key[:4]
            if year not in months_by_year:
                months_by_year[year] = []
            months_by_year[year].append((month_key, timeline.topics_by_month[month_key]))

        for year in sorted(months_by_year.keys()):
            self.add_line(f"\n{year}")
            for month_key, topics in months_by_year[year]:
                try:
                    month_name = datetime.strptime(month_key, '%Y-%m').strftime('%B')
                except:
                    month_name = month_key
                topics_str = ', '.join(topics[:4])
                self.add_line(f"  {month_name}: {topics_str}")

        if timeline.aggregate_topics:
            self.add_line("")
            self.add_line("Top Topics Overall:")
            for i, topic in enumerate(timeline.aggregate_topics[:5], 1):
                self.add_line(f"  {i}. {topic}")

    def add_top_threads(self, threads: list[ConversationThread]) -> None:
        """Record top conversation threads."""
        self.add_subsection("TOP 5 CONVERSATIONS THIS YEAR")

        thread_emojis = ["[FIRE]", "[CHAT]", "[BOLT]", "[TARGET]", "[IDEA]"]

        for i, thread in enumerate(threads[:5]):
            emoji = thread_emojis[i] if i < len(thread_emojis) else "[CHAT]"
            date_str = thread.start_time.strftime('%b %d, %Y')

            self.add_line(f"#{i+1} {emoji} {date_str}")
            self.add_line(f"   {thread.message_count} messages over {thread.duration_minutes} minutes")
            self.add_line(f"   Participants: {', '.join(thread.participants)}")
            if thread.topic_summary:
                self.add_line(f"   About: {thread.topic_summary}")
            self.add_line("")

    def add_personality_archetype(self, profile: PersonalityProfile, name: str = "") -> None:
        """Record personality archetype output."""
        name_prefix = f"{name.upper()}'S" if name else "YOUR"
        self.add_subsection(f"{name_prefix} ARCHETYPE: {profile.archetype.upper()} {profile.archetype_emoji}")

        if profile.archetype_reason:
            self.add_line(profile.archetype_reason)

        if profile.celebrity_match:
            self.add_line("")
            celeb_intro = f"If {name} were a celebrity..." if name else "If you were a celebrity..."
            self.add_line(celeb_intro)
            self.add_line(f"  {profile.celebrity_match}")
            if profile.celebrity_reason:
                self.add_line(f'  "{profile.celebrity_reason}"')

        if profile.superpower:
            self.add_line("")
            possessive = f"{name}'s" if name else "Your"
            self.add_line(f"{possessive} Superpower: {profile.superpower}")

    def add_group_wrapped(self, wrapped: GroupWrapped, analytics: ChatAnalytics) -> None:
        """Record group wrapped output."""
        self.add_section(f"{wrapped.chat_name.upper()} WRAPPED")

        if wrapped.summary:
            self.add_line(wrapped.summary)

        if wrapped.vibe_check:
            self.add_subsection("THE VIBE CHECK")
            self.add_line(wrapped.vibe_check)

        gs = analytics.group_stats
        self.add_subsection("BY THE NUMBERS")
        self.add_stat("Total Messages", f"{gs.total_messages:,}")
        self.add_stat("Total Words", f"{gs.total_words:,}")
        self.add_stat("Participants", f"{gs.total_participants}")
        self.add_stat("Most Active Day", gs.most_active_day)
        self.add_stat("Peak Hour", f"{gs.most_active_hour}:00")
        if gs.busiest_date:
            self.add_stat("Busiest Day Ever", f"{gs.busiest_date} ({gs.busiest_date_count} msgs)")

        if wrapped.achievements_ceremony:
            self.add_subsection("ACHIEVEMENTS UNLOCKED")
            for name, achievement in wrapped.achievements_ceremony:
                self.add_line(f"  {achievement.emoji}  {achievement.title} — {name}")
                self.add_line(f"      {achievement.description}")
                self.add_line("")

        # Topic timeline (from features)
        if wrapped.topic_timeline:
            self.add_topic_timeline(wrapped.topic_timeline)

        # Top threads (from features)
        if wrapped.top_threads:
            self.add_top_threads(wrapped.top_threads)

    def add_participant_wrapped(self, wrapped: ParticipantWrapped) -> None:
        """Record participant wrapped output."""
        name = wrapped.name
        first_name = name.split()[0]  # Use first name for labels

        self.add_section(f"{name.upper()}'S WRAPPED")

        if wrapped.tagline:
            self.add_line(f'"{wrapped.tagline}"')
            self.add_line("")

        stats = wrapped.stats
        self.add_subsection("STATS")
        self.add_stat("Messages", f"{stats.total_messages:,}")
        self.add_stat("Words", f"{stats.total_words:,}")
        self.add_stat("Links Shared", f"{stats.url_count}")
        self.add_stat("Avg Length", f"{stats.avg_message_length:.0f} chars")

        if wrapped.personality_summary:
            self.add_subsection(f"{first_name.upper()}'S VIBE")
            self.add_line(wrapped.personality_summary)

        if wrapped.top_topics:
            self.add_subsection(f"{first_name.upper()} TALKED ABOUT")
            for i, topic in enumerate(wrapped.top_topics, 1):
                self.add_line(f"  {i}. {topic}")

        if wrapped.memorable_quotes:
            self.add_subsection(f"{first_name.upper()}'S GREATEST HITS")
            for quote in wrapped.memorable_quotes:
                self.add_quote(quote)
                self.add_line("")

        if wrapped.achievements:
            self.add_subsection(f"{first_name.upper()}'S ACHIEVEMENTS UNLOCKED")
            for achievement in wrapped.achievements:
                self.add_achievement(achievement)

        # Personality archetype (from features)
        if wrapped.personality_profile:
            self.add_personality_archetype(wrapped.personality_profile, first_name)

    def add_outro(self) -> None:
        """Add the outro."""
        self.add_line("")
        self.add_line("=" * 80)
        self.add_line("  Thanks for a great year of chatting!")
        self.add_line("  WhatsApp Wrapped 2025")
        self.add_line("=" * 80)

    def get_text(self) -> str:
        """Get the recorded output as a string."""
        return "\n".join(self.lines)

    def save(self, filepath: str) -> None:
        """Save the recorded output to a file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.get_text())


if __name__ == '__main__':
    # Demo the display components
    print_header()
    dramatic_pause(1)

    print_section_header("DEMO SECTION")

    print_big_stat("You sent", "1,234 messages", COLORS['accent1'])

    demo_achievement = Achievement(
        emoji="🗣️",
        title="CHAT CHAMPION",
        description="Typed 7,345 messages—more than a NaNoWriMo novel"
    )
    print_achievement(demo_achievement)

    print_quote("Your mom is a GPT wrapper", COLORS['accent2'])

    print_divider()
    print_outro()
