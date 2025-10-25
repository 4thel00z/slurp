import argparse
import sys
from argparse import Namespace
from dataclasses import dataclass
from os import getenv
from typing import Optional

from slurp.adapters.instrumentation import InstrumentationConfig


@dataclass
class TokenConfig:
    openrouter_api_key: str

    @staticmethod
    def from_env() -> Optional["TokenConfig"]:
        openrouter_api_key = getenv("OPENROUTER_API_KEY")
        try:
            return TokenConfig( openrouter_api_key)
        except ValueError as err:
            print(f"Error creating TokenConfig: {err}")
            return None

    def __post_init__(self):
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY must be set in the environment.")


@dataclass
class ConfluenceConfig:
    username: str
    api_key: str
    space: str
    base_url: str = "https://aleph-alpha.atlassian.net"
    cloud: bool = True
    months_back: int = 0
    random_selection: bool = True
    concurrency: int = 4
    max_pages: int = 50
    page_batch_size: int = 50
    skip: int = 0
    enabled: bool = True

    @staticmethod
    def add_to_parser(parser: argparse.ArgumentParser) -> None:
        """Add Confluence configuration arguments to the given parser."""
        group = parser.add_argument_group('Confluence Options')
        group.add_argument(
            "--confluence-space",
            dest="space",
            type=str,
            default="",
            help="Space key to operate on",
        )
        group.add_argument(
            "--confluence-cloud/--no-confluence-cloud",
            dest="cloud",
            default=True,
            help="Use Confluence Cloud API (default: True)",
        )
        group.add_argument(
            "--confluence-enabled",
            dest="enabled",
            action="store_true",
            default=True,
            help="Enable Confluence integration (default: True)",
        )
        group.add_argument(
            "--confluence-disabled",
            dest="enabled",
            action="store_false",
            help="Disable Confluence integration",
        )
        group.add_argument(
            "--confluence-max-pages",
            dest="max_pages",
            type=int,
            default=50,
            help="Maximum number of pages to fetch (default: 50)",
        )
        group.add_argument(
            "--confluence-months-back",
            dest="months_back",
            type=int,
            default=0,
            help="How many months back to look for updates (0 = no filter, default: 0)",
        )
        group.add_argument(
            "--confluence-random-selection/--no-confluence-random-selection",
            dest="random_selection",
            default=True,
            help="Whether to pick pages at random (default: True)",
        )
        group.add_argument(
            "--confluence-concurrency",
            dest="concurrency",
            type=int,
            default=4,
            help="Number of concurrent workers (default: 4)",
        )
        group.add_argument(
            "--confluence-page-batch-size",
            dest="page_batch_size",
            type=int,
            default=50,
            help="Page-size for list endpoints (default: 50)",
        )
        group.add_argument(
            "--confluence-skip",
            dest="skip",
            type=int,
            default=0,
            help="Number of pages to skip (default: 0)",
        )
        group.add_argument(
            "--confluence-base-url",
            dest="base_url",
            type=str,
            default="https://aleph-alpha.atlassian.net",
            help="Base URL for API calls (default: https://aleph-alpha.atlassian.net)",
        )
        group.add_argument(
            "--confluence-username",
            dest="username",
            type=str,
            default="",
            help="User email for Confluence authentication",
        )

    @staticmethod
    def parse(
        argv: list[str],
    ):
        parser = argparse.ArgumentParser(description="Confluence configuration parser")
        ConfluenceConfig.add_to_parser(parser)
        return parser.parse_known_args(argv)

    @staticmethod
    def from_default(
        argv: list[str] = None,
    ) -> "ConfluenceConfig":
        argv = argv if argv else sys.argv
        args, _ = ConfluenceConfig.parse(argv)
        return ConfluenceConfig(
            base_url=args.base_url or getenv("CONFLUENCE_BASE_URL"),
            username=args.username or getenv("CONFLUENCE_USERNAME"),
            api_key=getenv("CONFLUENCE_API_KEY"),
            space=args.space,
            cloud=args.cloud,
            max_pages=args.max_pages,
            months_back=args.months_back,
            random_selection=args.random_selection,
            concurrency=args.concurrency,
            page_batch_size=args.page_batch_size,
            skip=args.skip,
            enabled=args.enabled,
        )


@dataclass
class KafkaConfig:
    bootstrap_servers: str = "localhost:19092"
    topic: str = "tasks"
    client_id: str = "slurp"

    @staticmethod
    def add_to_parser(parser: argparse.ArgumentParser) -> None:
        """Add Kafka configuration arguments to the given parser."""
        group = parser.add_argument_group('Kafka Options')
        group.add_argument(
            "--kafka-bootstrap-servers",
            dest="bootstrap_servers",
            type=str,
            default="localhost:19092",
            help="Kafka bootstrap servers (default: localhost:19092)",
        )
        group.add_argument(
            "--kafka-topic",
            dest="topic",
            type=str,
            default="tasks",
            help="Kafka topic to produce to (default: tasks)",
        )
        group.add_argument(
            "--kafka-client-id",
            dest="client_id",
            type=str,
            default="slurp",
            help="Kafka client ID (default: slurp)",
        )

    @staticmethod
    def parse(
        argv: list[str] = None,
    ):
        parser = argparse.ArgumentParser(description="Kafka configuration parser")
        KafkaConfig.add_to_parser(parser)
        return parser.parse_known_args(argv)

    @staticmethod
    def from_env() -> "KafkaConfig":
        return KafkaConfig(
            bootstrap_servers=getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),
            topic=getenv("KAFKA_TOPIC", "tasks"),
            client_id=getenv("KAFKA_CLIENT_ID", "slurp"),
        )

    @staticmethod
    def from_default(
        argv: list[str] = None,
    ) -> "KafkaConfig":
        argv = argv if argv else sys.argv
        args, _ = KafkaConfig.parse(argv)
        defaults = KafkaConfig.from_env()
        return KafkaConfig(
            bootstrap_servers=args.bootstrap_servers or defaults.bootstrap_servers,
            topic=args.topic or defaults.topic,
            client_id=args.client_id or defaults.client_id,
        )


@dataclass
class SQLiteConfig:
    database: str
    timeout: float = 1.0

    @staticmethod
    def add_to_parser(parser: argparse.ArgumentParser) -> None:
        """Add SQLite configuration arguments to the given parser."""
        group = parser.add_argument_group('SQLite Options')
        group.add_argument(
            "--sqlite-database",
            dest="database",
            type=str,
            default=getenv("SQLITE_DATABASE", "./data.db"),
            help="Path to SQLite database file (default: ./data.db)",
        )
        group.add_argument(
            "--sqlite-timeout",
            dest="timeout",
            type=float,
            default=float(getenv("SQLITE_TIMEOUT", "5.0")),
            help="Timeout in seconds for database locks (default: 5.0)",
        )

    @staticmethod
    def parse(argv: list[str] = None):
        parser = argparse.ArgumentParser(add_help=False)
        SQLiteConfig.add_to_parser(parser)
        return parser.parse_known_args(argv)

    @staticmethod
    def from_env() -> "SQLiteConfig":
        return SQLiteConfig(
            database=getenv("SQLITE_DATABASE", "./document_scraper.db"),
            timeout=float(getenv("SQLITE_TIMEOUT", "1.0")),
        )

    @staticmethod
    def from_default(argv: list[str] = None) -> "SQLiteConfig":
        argv = argv or sys.argv
        args, _ = SQLiteConfig.parse(argv)
        defaults = SQLiteConfig.from_env()
        return SQLiteConfig(
            database=args.database or defaults.database,
            timeout=args.timeout or defaults.timeout,
        )


@dataclass
class GeneratorConfig:
    language: str
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    base_url: str = "https://openrouter.ai/api/v1"
    difficulty_ratio: str = "mixed"
    concurrency: int = 5
    is_short: bool = True
    batch_size: int = 1
    enabled: bool = True

    @staticmethod
    def add_to_parser(parser: argparse.ArgumentParser) -> None:
        """Add Generator configuration arguments to the given parser."""
        group = parser.add_argument_group('Generator Options')
        group.add_argument(
            "--generator-model",
            dest="model",
            type=str,
            default="google/gemini-2.5-flash-preview-05-20",
            help="LLM model to use for QA generation (default: google/gemini-2.5-flash-preview-05-20)",
        )
        group.add_argument(
            "--generator-language",
            dest="language",
            type=str,
            choices=["de", "en"],
            default="de",
            help="Language for generated questions (default: de)",
        )
        group.add_argument(
            "--generator-max-tokens",
            dest="max_tokens",
            type=int,
            default=4096,
            help="Maximum number of tokens (default: 4096)",
        )
        group.add_argument(
            "--generator-temperature",
            dest="temperature",
            type=float,
            default=0.7,
            help="Temperature for generation (default: 0.7)",
        )
        group.add_argument(
            "--generator-base-url",
            dest="base_url",
            type=str,
            default="https://openrouter.ai/api/v1",
            help="Base URL for the LLM API (default: https://openrouter.ai/api/v1)",
        )
        group.add_argument(
            "--generator-difficulty-ratio",
            dest="difficulty_ratio",
            type=str,
            choices=["easy", "medium", "hard", "mixed", "balanced"],
            default="mixed",
            help="Question difficulty distribution (default: mixed)",
        )
        group.add_argument(
            "--generator-concurrency",
            dest="concurrency",
            type=int,
            default=5,
            help="Number of concurrent LLM requests (default: 5)",
        )
        group.add_argument(
            "--generator-is-short",
            dest="is_short",
            action="store_true",
            default=True,
            help="Generate short questions (default: True)",
        )
        group.add_argument(
            "--generator-batch-size",
            dest="batch_size",
            type=int,
            default=1,
            help="Number of documents to process together (1=single, >1=cross-document, default: 1)",
        )
        group.add_argument(
            "--generator-enabled",
            dest="enabled",
            action="store_true",
            default=True,
            help="Enable question generation (default: True)",
        )
        group.add_argument(
            "--generator-disabled",
            dest="enabled",
            action="store_false",
            help="Disable question generation",
        )

    @staticmethod
    def from_args(args: list[str]) -> "GeneratorConfig":
        parser = argparse.ArgumentParser(description="Model configuration parser")
        GeneratorConfig.add_to_parser(parser)
        parsed_args, _ = parser.parse_known_args(args)
        return GeneratorConfig(
            language=parsed_args.language.lower(),
            model=parsed_args.model,
            max_tokens=parsed_args.max_tokens,
            temperature=parsed_args.temperature,
            base_url=parsed_args.base_url,
            difficulty_ratio=parsed_args.difficulty_ratio,
            concurrency=parsed_args.concurrency,
            is_short=parsed_args.is_short,
            batch_size=parsed_args.batch_size,
            enabled=parsed_args.enabled,
        )


@dataclass
class AppConfig:
    token: TokenConfig
    instrumentation: InstrumentationConfig
    confluence: ConfluenceConfig
    kafka: KafkaConfig
    generator: GeneratorConfig
    sqlite: SQLiteConfig

    @staticmethod
    def from_default(
        argv: list[str],
    ) -> "AppConfig":
        return AppConfig(
            token=TokenConfig.from_env(),
            instrumentation=InstrumentationConfig.from_env().setup(),
            confluence=ConfluenceConfig.from_default(argv=argv),
            kafka=KafkaConfig.from_default(argv=argv),
            generator=GeneratorConfig.from_args(args=argv),
            sqlite=SQLiteConfig.from_default(argv=argv),
        )


def create_cli_parser() -> argparse.ArgumentParser:
    """
    Create the main CLI parser with subcommands for scraper and worker.
    """
    parser = argparse.ArgumentParser(
        prog="slurp",
        description="Slurp - Confluence RAG Dataset Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    
    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
        help='Available commands',
    )
    
    # Scraper subcommand
    scraper_parser = subparsers.add_parser(
        'scraper',
        help='Run the Confluence page scraper',
        description='Discovers Confluence pages and submits them to Kafka queue',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ConfluenceConfig.add_to_parser(scraper_parser)
    KafkaConfig.add_to_parser(scraper_parser)
    
    # Worker subcommand  
    worker_parser = subparsers.add_parser(
        'worker',
        help='Run the QA generation worker',
        description='Processes pages from Kafka and generates Question-Answer pairs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ConfluenceConfig.add_to_parser(worker_parser)
    KafkaConfig.add_to_parser(worker_parser)
    GeneratorConfig.add_to_parser(worker_parser)
    SQLiteConfig.add_to_parser(worker_parser)
    
    return parser


def parse_global_args(argv: list[str]) -> Namespace:
    """
    Parse global arguments and return the AppConfig instance.
    (Deprecated: Use create_cli_parser() instead)
    """
    parser = argparse.ArgumentParser(description="Global configuration parser")
    parser.add_argument(
        "--workers",
        type=int,
        dest="workers",
        default=1,
    )
    ns, _ = parser.parse_known_args(argv)
    return ns