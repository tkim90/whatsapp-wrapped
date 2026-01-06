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

from analytics import ChatAnalytics
from wrapped import ParticipantWrapped, GroupWrapped, Award


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


def print_award(award: Award, color: str = COLORS['accent1']) -> None:
    """Print an award with style."""
    award_box = f"""
    [bold {color}]{award.title}[/]
    [dim]{award.description}[/]
    [bold white]{award.value}[/]
    """
    panel = Panel(
        award_box,
        box=ROUNDED,
        border_style=color,
        padding=(0, 2),
    )
    console.print(panel)


def print_quote(quote: str, color: str = COLORS['accent2']) -> None:
    """Print a memorable quote."""
    # Truncate very long quotes
    if len(quote) > 200:
        quote = quote[:197] + "..."

    console.print(f'  [italic {color}]"{quote}"[/]')


def print_participant_wrapped(wrapped: ParticipantWrapped, index: int = 0) -> None:
    """Print a participant's full Wrapped summary."""
    color = get_participant_color(index)

    # Big name reveal
    console.print()
    console.print(Align.center(Text("YOUR WRAPPED FOR...", style="dim italic")))
    dramatic_pause(0.5)

    name_art = f"""
    ╔{'═' * (len(wrapped.name) + 4)}╗
    ║  {wrapped.name.upper()}  ║
    ╚{'═' * (len(wrapped.name) + 4)}╝
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
    stats_table.add_row("Emojis Used", f"{stats.emoji_count}")
    stats_table.add_row("Avg Length", f"{stats.avg_message_length:.0f} chars")

    console.print()
    console.print(Align.center(stats_table))

    # Personality
    if wrapped.personality_summary:
        console.print()
        print_section_header("YOUR VIBE", color)
        console.print(Panel(
            f"[italic]{wrapped.personality_summary}[/]",
            box=ROUNDED,
            border_style=color,
            padding=(1, 2),
        ))

    # Top topics
    if wrapped.top_topics:
        console.print()
        print_section_header("YOU TALKED ABOUT", color)
        for i, topic in enumerate(wrapped.top_topics, 1):
            console.print(f"  [{color}]{i}.[/] {topic}")

    # Memorable quotes
    if wrapped.memorable_quotes:
        console.print()
        print_section_header("QUOTABLE MOMENTS", color)
        for quote in wrapped.memorable_quotes:
            print_quote(quote, color)
            console.print()

    # Awards
    if wrapped.awards:
        console.print()
        print_section_header("YOUR AWARDS", color)
        for award in wrapped.awards:
            print_award(award, color)

    # Top emojis
    if stats.top_emojis:
        console.print()
        print_section_header("YOUR TOP EMOJIS", color)
        emoji_str = "  ".join(f"{emoji} ({count})" for emoji, count in stats.top_emojis[:5])
        console.print(Align.center(Text(emoji_str, style="bold")))

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

    # Awards ceremony
    if wrapped.awards_ceremony:
        console.print()
        print_section_header("AWARDS CEREMONY", COLORS['accent3'])

        for name, award in wrapped.awards_ceremony:
            console.print(f"  [{COLORS['accent3']}]{award.title}[/] goes to... [bold]{name}[/]")
            console.print(f"    [dim]{award.value}[/]")
            console.print()


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
# File Output Support
# ============================================================================

class WrappedRecorder:
    """Records Wrapped output for file export."""

    def __init__(self):
        self.lines: list[str] = []

    def add_header(self) -> None:
        """Add the header to recorded output."""
        self.lines.append("""
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

    def add_award(self, award: Award) -> None:
        """Add an award."""
        self.lines.append(f"  [{award.title}]")
        self.lines.append(f"    {award.description}")
        self.lines.append(f"    => {award.value}")
        self.lines.append("")

    def add_divider(self) -> None:
        """Add a visual divider."""
        self.lines.append("")
        self.lines.append("  * * *")
        self.lines.append("")

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

        if wrapped.awards_ceremony:
            self.add_subsection("AWARDS CEREMONY")
            for name, award in wrapped.awards_ceremony:
                self.add_line(f"  {award.title} goes to... {name}")
                self.add_line(f"    {award.value}")
                self.add_line("")

    def add_participant_wrapped(self, wrapped: ParticipantWrapped) -> None:
        """Record participant wrapped output."""
        self.add_section(f"{wrapped.name.upper()}'S WRAPPED")

        if wrapped.tagline:
            self.add_line(f'"{wrapped.tagline}"')
            self.add_line("")

        stats = wrapped.stats
        self.add_subsection("STATS")
        self.add_stat("Messages", f"{stats.total_messages:,}")
        self.add_stat("Words", f"{stats.total_words:,}")
        self.add_stat("Links Shared", f"{stats.url_count}")
        self.add_stat("Emojis Used", f"{stats.emoji_count}")
        self.add_stat("Avg Length", f"{stats.avg_message_length:.0f} chars")

        if wrapped.personality_summary:
            self.add_subsection("YOUR VIBE")
            self.add_line(wrapped.personality_summary)

        if wrapped.top_topics:
            self.add_subsection("YOU TALKED ABOUT")
            for i, topic in enumerate(wrapped.top_topics, 1):
                self.add_line(f"  {i}. {topic}")

        if wrapped.memorable_quotes:
            self.add_subsection("QUOTABLE MOMENTS")
            for quote in wrapped.memorable_quotes:
                self.add_quote(quote)
                self.add_line("")

        if wrapped.awards:
            self.add_subsection("YOUR AWARDS")
            for award in wrapped.awards:
                self.add_award(award)

        if stats.top_emojis:
            self.add_subsection("YOUR TOP EMOJIS")
            emoji_str = "  ".join(f"{emoji} ({count})" for emoji, count in stats.top_emojis[:5])
            self.add_line(f"  {emoji_str}")

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

    demo_award = Award(
        title="TOP CHATTER",
        description="Most messages sent",
        value="7,345 messages"
    )
    print_award(demo_award)

    print_quote("Your mom is a GPT wrapper", COLORS['accent2'])

    print_divider()
    print_outro()
