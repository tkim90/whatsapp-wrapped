#!/usr/bin/env python3
"""WhatsApp Wrapped 2025 - Spotify-style chat analysis."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from parser import parse_chat
from analytics import analyze_chat
from lm_studio import LMStudioClient
from wrapped import WrappedGenerator
from features import load_or_extract_features, get_features_cache_path
from display import (
    console,
    print_header,
    print_group_wrapped,
    print_participant_wrapped,
    print_divider,
    print_outro,
    print_usage_graphs,
    print_archetype_cards,
    dramatic_pause,
    COLORS,
    WrappedRecorder,
)


def check_lm_studio(client: LMStudioClient) -> bool:
    """Check if LM Studio is available."""
    if not client.is_available():
        console.print(
            f"[bold red]Error:[/] LM Studio is not running at {client.base_url}\n"
            f"Please start LM Studio and load the required models:\n"
            f"  - Embedding: {client.embedding_model}\n"
            f"  - LLM: {client.chat_model}\n"
        )
        return False
    return True


def run_wrapped(
    chat_file: Path,
    chat_name: str | None = None,
    skip_individuals: bool = False,
    quick_mode: bool = False,
    output_file: Path | None = None,
    rebuild_index: bool = False,
    index_only: bool = False
) -> None:
    """Run the full Wrapped generation pipeline."""

    # Initialize LM Studio client
    client = LMStudioClient()

    # Check LM Studio availability
    if not check_lm_studio(client):
        sys.exit(1)

    # Parse chat
    with Progress(
        SpinnerColumn(style=COLORS['primary']),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[bold]Parsing chat file...", total=None)
        chat = parse_chat(chat_file)
        progress.update(task, description=f"[bold]Parsed {len(chat.messages):,} messages from {len(chat.participants)} participants")
        dramatic_pause(0.5)

    # Analyze chat
    with Progress(
        SpinnerColumn(style=COLORS['primary']),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[bold]Computing analytics...", total=None)
        analytics = analyze_chat(chat)
        progress.update(task, description="[bold]Analytics complete!")
        dramatic_pause(0.5)

    # Determine chat name
    if not chat_name:
        chat_name = chat_file.stem.replace('-', ' ').replace('_', ' ').title()

    # Extract deep features (topic timeline, conversations, personality archetypes)
    features = None
    if not quick_mode:
        def feature_progress(msg):
            console.print(f"  [dim]{msg}[/]")

        console.print(f"\n[bold {COLORS['primary']}]Extracting deep features...[/]")
        features = load_or_extract_features(
            chat, chat_file, client,
            force_rebuild=rebuild_index,
            progress_callback=feature_progress
        )
        console.print(f"[bold green]Features ready![/]\n")

        # If index-only mode, just save and exit
        if index_only:
            cache_path = get_features_cache_path(chat_file)
            console.print(f"[bold green]Index saved to:[/] {cache_path}")
            return

    # Initialize generator with features
    generator = WrappedGenerator(chat, analytics, client, features=features)

    # Initialize recorder for file output
    recorder = WrappedRecorder() if output_file else None

    # Print header
    print_header()
    if recorder:
        recorder.add_header()
    dramatic_pause(1)

    # Generate and display group wrapped
    with Progress(
        SpinnerColumn(style=COLORS['primary']),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("[bold]Generating group insights...", total=None)
        group_wrapped = generator.generate_group_wrapped(chat_name)
        progress.update(task, description="[bold]Group insights ready!")
        dramatic_pause(0.3)

    print_group_wrapped(group_wrapped, analytics)
    if recorder:
        recorder.add_group_wrapped(group_wrapped, analytics)

    # Usage graphs
    print_usage_graphs(analytics.participant_stats)

    print_divider()
    if recorder:
        recorder.add_divider()

    # Generate individual wrappeds
    participant_wrappeds = []
    if not skip_individuals:
        for i, participant in enumerate(chat.participants):
            with Progress(
                SpinnerColumn(style=COLORS['primary']),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"[bold]Generating {participant}'s Wrapped...", total=None)
                participant_wrapped = generator.generate_participant_wrapped(participant)
                progress.update(task, description=f"[bold]{participant}'s Wrapped ready!")
                dramatic_pause(0.2)

            participant_wrappeds.append(participant_wrapped)
            print_participant_wrapped(participant_wrapped, i)
            if recorder:
                recorder.add_participant_wrapped(participant_wrapped)

            if i < len(chat.participants) - 1:
                print_divider()
                if recorder:
                    recorder.add_divider()
                dramatic_pause(0.3)

        # Show all archetypes side-by-side at the end
        profiles_and_stats = [
            (pw.name, pw.personality_profile, pw.stats)
            for pw in participant_wrappeds
        ]
        print_archetype_cards(profiles_and_stats)

    print_outro()
    if recorder:
        recorder.add_outro()

    # Save to file if requested
    if output_file and recorder:
        recorder.save(str(output_file))
        console.print(f"\n[bold green]Saved to:[/] {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WhatsApp Wrapped 2025 - Spotify-style chat analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py chat.txt
  python main.py chat.txt --name "The Squad"
  python main.py chat.txt --group-only
  python main.py chat.txt --output wrapped.txt
  python main.py chat.txt -o  # Auto-generate filename
  python main.py chat.txt --rebuild-index  # Force fresh feature extraction
  python main.py chat.txt --index-only  # Just build index, don't display

Requirements:
  LM Studio must be running at http://127.0.0.1:1234 with:
  - Embedding model: text-embedding-nomic-embed-text-v1.5
  - LLM model: openai/gpt-oss-20b
        """
    )

    parser.add_argument(
        "chat_file",
        type=Path,
        help="Path to WhatsApp chat export file"
    )
    parser.add_argument(
        "--name", "-n",
        type=str,
        default=None,
        help="Custom name for the group chat"
    )
    parser.add_argument(
        "--group-only", "-g",
        action="store_true",
        help="Only show group wrapped, skip individual wrappeds"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick mode with fewer LLM calls"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        nargs='?',
        const='auto',
        default=None,
        help="Output to a .txt file. Provide a filename or use without argument for auto-generated name"
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Force rebuilding the feature index (topic timeline, personalities, etc.)"
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Only build/update the feature index without generating Wrapped output"
    )

    args = parser.parse_args()

    # Validate chat file
    if not args.chat_file.exists():
        console.print(f"[bold red]Error:[/] File not found: {args.chat_file}")
        sys.exit(1)

    # Handle output file
    output_file = None
    if args.output:
        if args.output == 'auto':
            # Auto-generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chat_stem = args.chat_file.stem.replace(' ', '-')[:30]
            output_file = Path(f"wrapped-{chat_stem}-{timestamp}.txt")
        else:
            output_file = Path(args.output)
            if not output_file.suffix:
                output_file = output_file.with_suffix('.txt')

    try:
        run_wrapped(
            chat_file=args.chat_file,
            chat_name=args.name,
            skip_individuals=args.group_only,
            quick_mode=args.quick,
            output_file=output_file,
            rebuild_index=args.rebuild_index,
            index_only=args.index_only
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Wrapped generation cancelled.[/]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise


if __name__ == "__main__":
    main()
