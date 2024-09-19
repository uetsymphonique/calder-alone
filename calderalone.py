import argparse
import asyncio
import glob
import logging
import sys

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

from app.ascii_banner import no_color, ASCII_BANNER, print_rich_banner
from app.objects.c_agent import Agent
from app.objects.c_obfuscator import Obfuscator
from app.objects.c_objective import Objective
from app.objects.c_operation import Operation
from app.objects.secondclass.c_goal import Goal
from app.service.data_svc import DataService
from app.service.file_svc import FileService
from app.service.knowledge_svc import KnowledgeService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.utility.base_world import BaseWorld


def setup_logger(level=logging.DEBUG):
    format = "%(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    if no_color():
        logging.basicConfig(level=level, format=format, datefmt=datefmt)
    else:
        console = Console(theme=Theme({"logging.level.warning": "yellow"}))
        logging.basicConfig(
            level=level,
            format=format,
            datefmt=datefmt,
            handlers=[RichHandler(rich_tracebacks=True, markup=True, console=console)]
        )

    for logger_name in logging.root.manager.loggerDict.keys():
        if logger_name in ("aiohttp.server", "asyncio"):
            continue
        else:
            logging.getLogger(logger_name).setLevel(100)
    logging.getLogger("markdown_it").setLevel(logging.WARNING)
    logging.captureWarnings(True)


def get_parser():
    parser = argparse.ArgumentParser(
        description=ASCII_BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-l",
        "--log",
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
        default="INFO",
    )

    parser.add_argument(
        "-O",
        "--obfuscate",
        dest="obfuscator",
        choices=["plain-text", "base64", "base64jumble", "caesar cipher", "base64noPadding", "steganography"],
        help="Set the obfuscator",
        default="plain-text",
    )

    return parser


async def load_data(services):
    data_svc = services["data_svc"]
    await data_svc.load_adversary_file('data/adversary.yml')
    await data_svc.load_source_file('data/source.yml')
    # await data_svc.load_objective_file('data/objective.yml')
    await data_svc.load_planner_file('data/planner.yml')
    await data_svc.store(
        Objective(id='495a9828-cab1-44dd-a0ca-66e58177d8cc', name='default', goals=[Goal()])
    )
    for abilities_folder in glob.glob('data/abilities/*'):
        for ability_file in glob.glob(f'{abilities_folder}/*'):
            # print(f, type(f))
            await data_svc.load_ability_file(ability_file)
    await data_svc.store(
        Obfuscator(name='plain-text',
                   description='Does no obfuscation to any command, instead running it in plain text',
                   module='plugins.stockpile.app.obfuscators.plain_text')
    )
    await data_svc.store(
        Obfuscator(name='base64',
                   description='Obfuscates commands in base64',
                   module='plugins.stockpile.app.obfuscators.base64_basic')
    )
    await data_svc.store(
        Obfuscator(name='base64jumble',
                   description='Obfuscates commands in base64, then adds characters to evade base64 detection. '
                               'Disclaimer: this may cause duplicate links to run.',
                   module='plugins.stockpile.app.obfuscators.base64_jumble')
    )
    await data_svc.store(
        Obfuscator(name='caesar cipher',
                   description='Obfuscates commands through a caesar cipher algorithm, which uses a randomly selected '
                               'shift value.',
                   module='plugins.stockpile.app.obfuscators.caesar_cipher')
    )
    await data_svc.store(
        Obfuscator(name='base64noPadding',
                   description='Obfuscates commands in base64, then removes padding',
                   module='plugins.stockpile.app.obfuscators.base64_no_padding')
    )
    await data_svc.store(
        Obfuscator(name='steganography',
                   description='Obfuscates commands through image-based steganography',
                   module='plugins.stockpile.app.obfuscators.steganography')
    )


if __name__ == "__main__":
    sys.path.append("")

    parser = get_parser()
    args = parser.parse_args()
    setup_logger(getattr(logging, args.logLevel))
    main_config_path = "conf/default.yml"
    BaseWorld.apply_config("main", BaseWorld.strip_yml(main_config_path)[0])
    logging.info("Using main config from %s" % main_config_path)
    BaseWorld.apply_config("agents", BaseWorld.strip_yml("conf/agents.yml")[0])
    BaseWorld.apply_config("payloads", BaseWorld.strip_yml("conf/payloads.yml")[0])
    print_rich_banner()

    services = dict(
        data_svc=DataService(),
        planning_svc=PlanningService(),
        file_svc=FileService(),
        knowledge_svc=KnowledgeService(),
        rest_svc=RestService()
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(load_data(services))
    adversary = services["data_svc"].ram["adversaries"][0]
    abilities = services["data_svc"].ram["abilities"]
    source = services["data_svc"].ram["sources"][0]
    planner = services["data_svc"].ram["planners"][0]
    objective = services["data_svc"].ram["objectives"][0]
    agent = Agent(platform="linux", executors=("sh",))
    operation = Operation(adversary=adversary, planner=planner, source=source, agents=[agent],
                          obfuscator=args.obfuscator)
    loop.run_until_complete(operation.run(services))
