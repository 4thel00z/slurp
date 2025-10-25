import asyncio
import logging
import multiprocessing
import os
import sys
from multiprocessing import Process

from slurp.adapters.asyncio import consume_async_gen
from slurp.domain.config import create_cli_parser
from slurp.usecases.scraper import ScrapeUsecase
from slurp.usecases.worker import WorkerUsecase


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def run_scraper_process():
    """
    Target function for multiprocessing.Process to run a single scraper.
    """
    asyncio.run(ScrapeUsecase().run())


def scraper(workers: int = 1):
    """
    Runs the document scraper to produce tasks.
    """
    processes = []
    for i in range(workers):
        print(f"Starting scraper process {i + 1}/{workers}")
        process = Process(target=run_scraper_process)
        processes.append(process)
        process.start()

    for process in processes:
        process.join()  # Wait for all scraper processes to complete


def handle(generation):
    for qa in generation.question_answers:
        logger.info(f"""Q: {qa.question}
                A: {qa.answer}
                   ---""")


async def worker_main():
    usecase = WorkerUsecase()
    await consume_async_gen(usecase.run(), handle)


def run_worker_process():
    """
    Target function for multiprocessing.Process to run a single worker.
    """

    asyncio.run(worker_main())


def worker(workers: int = 1):
    """
    Runs the document worker to consume tasks.
    """
    processes = []
    for i in range(workers):
        print(f"Starting worker process {i + 1}/{workers}")
        process = Process(target=run_worker_process)
        processes.append(process)
        process.start()

    for process in processes:
        process.join()  # Wait for all worker processes to complete


if __name__ == "__main__":
    # Use fork method for multiprocessing (Linux/macOS only)
    multiprocessing.set_start_method("fork", force=True)

    parser = create_cli_parser()
    args = parser.parse_args()

    match args.command:
        case "scraper":
            scraper(args.workers)
        case "worker":
            worker(args.workers)
        case _:
            print(f"Unknown command: {args.command}")
            sys.exit(os.EX_USAGE)
