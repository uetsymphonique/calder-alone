import itertools
import logging
import subprocess
import sys
import threading
import time
import os
import platform
import ctypes
from datetime import datetime, timezone

from colorama import Fore, init
from tqdm import tqdm

init(autoreset=True)

from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_result import Result
from app.utility.base_service import BaseService


def spinner_animation():
    spinner = itertools.cycle(['|', '/', '-', '\\'])
    while not stop_spinner_event.is_set():
        sys.stdout.write(f"\r{Fore.YELLOW}Running... {next(spinner)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r")


class ExecutingService(BaseService):
    def __init__(self):
        self.log = self.add_service('executing_svc', self)

    def running(self, link: Link) -> Result:
        """
        Executes a command linked to a link and returns the output.
        :param link: Link object
        :return: Output of the command
        """

        command = link.display["command"]
        shell = link.executor.name
        os = link.executor.platform
        print(f'--------------------------------------------------------\n'
              f'{Fore.YELLOW}Running procedure: {link.display["ability"]["name"]}\n'
              f'{link.display["ability"]["tactic"].capitalize()}: '
              f'{link.display["ability"]["technique_name"]} ({link.display["ability"]["technique_id"]})\n'
              f'Description: {link.display["ability"]["description"]}\n\n{Fore.MAGENTA}{os}-{shell}> {command}')
        result = self.run_command(command, shell, link.executor.timeout)
        logging.debug(f'Result:\n{result.stdout + result.stderr}')
        print(f'Exit code: {result.returncode}')
        return Result(id=link.id, output=result.stdout,
                      stderr=result.stderr, exit_code=result.returncode,
                      agent_reported_time=datetime.now(timezone.utc))

    @staticmethod
    def run_command(command, shell_type, timeout=1) -> subprocess.CompletedProcess:
        shell_map = {
            'psh': ['powershell', '-Command'],
            'pwsh': ['pwsh', '-Command'],
            'sh': ['sh', '-c'],
            'cmd': ['cmd', '/c'],  # Added support for cmd shell type
            'proc': None  # Run directly without any shell
        }

        # Check if shell type is valid
        if shell_type not in shell_map:
            raise ValueError(f"Invalid shell type '{shell_type}'. Choose from 'psh', 'sh', 'pwsh', 'cmd', or 'proc'.")

        # Prepare the command to execute
        if shell_map[shell_type] is None:  # 'proc' case, direct execution
            cmd = command.split()  # Assumes the command is space-separated
        else:
            cmd = shell_map[shell_type] + [command]

        # Simple fake loading using dots
        print(f"{Fore.CYAN}Preparing to execute command", end="", flush=True)
        for _ in range(4):
            time.sleep(0.5)  # Simulate fake loading with sleep
            print(f"{Fore.CYAN}.", end="", flush=True)
        print("\n")  # Move to the next line after loading

        # Start command execution using Popen
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
        except Exception as e:
            print(f"\n{Fore.RED}An error occurred during command execution: {e}")
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout='', stderr=str(e))

        start_time = time.time()

        global stop_spinner_event
        stop_spinner_event = threading.Event()
        spinner_thread = threading.Thread(target=spinner_animation)
        spinner_thread.start()

        try:
            # Wait for the process to complete with timeout
            stdout, stderr = process.communicate(timeout=timeout)
            result = subprocess.CompletedProcess(cmd, returncode=process.returncode, stdout=stdout, stderr=stderr)
        except subprocess.TimeoutExpired:
            # If the process exceeds the timeout, terminate it
            process.kill()
            stdout, stderr = process.communicate()  # Fetch any output after killing the process
            result = subprocess.CompletedProcess(cmd, returncode=-1, stdout=stdout,
                                                 stderr=f"Command timed out after {timeout} seconds.")
        except Exception as e:
            print(f"\n{Fore.RED}An error occurred during command execution: {e}")
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout='', stderr=str(e))
        finally:
            # Stop the spinner animation
            stop_spinner_event.set()
            spinner_thread.join()

        # Print the final result after the progress bar has been closed
        if result.returncode == 0:
            print(f"{Fore.GREEN}Command executed successfully in {time.time() - start_time:.2f} seconds.")
        else:
            print(f"{Fore.RED}An error occurred during command execution: {result.stderr}")

        return result

    @staticmethod
    def is_admin_windows():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception as e:
            logging.debug(f"An error occurred during checking Windows privileges: {e}")
            return False

    @staticmethod
    def is_root_linux():
        try:
            return os.geteuid() == 0
        except AttributeError as e:
            logging.debug(f"An error occurred during checking Linux privileges: {e}")
            return False

    def check_privileged(self, current_platform=platform.system().lower()):
        ret = False
        if current_platform == 'windows':
            ret = self.is_admin_windows()
        elif current_platform == 'linux':
            ret = self.is_root_linux()
        if ret:
            logging.info(f'Privilege at {current_platform} was escalated successfully')
        else:
            logging.warning(f'Privilege at {current_platform} was not escalated')
        return ret