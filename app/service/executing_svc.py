import itertools
import logging
import subprocess
import threading
import time
from datetime import datetime, timezone

from tqdm import tqdm
from colorama import Fore, Style, init

# Initialize colorama for colored output
init(autoreset=True)

from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_result import Result
from app.utility.base_service import BaseService


class ExecutingService(BaseService):
    def __init__(self):
        self.log = self.add_service('executing_svc', self)

    def running(self, link: Link, timeout=600):
        """
        Executes a command linked to a link and returns the output.
        :param link: Link object
        :param timeout: Timeout in seconds for the command to complete, default is 600 seconds
        :return: Output of the command
        """

        command = link.display["command"]
        shell = link.executor.name
        os = link.executor.platform
        print(f'--------------------------------------------------------\n'
              f'Running procedure: {link.display["ability"]["name"]}\n'
              f'{link.display["ability"]["tactic"].capitalize()}: '
              f'{link.display["ability"]["technique_name"]} ({link.display["ability"]["technique_id"]})\n'
              f'Description: {link.display["ability"]["description"]}\n\n{os}-{shell}> {command}')
        result = self.run_command(command, shell, timeout)
        logging.debug(f'Result:\n{result.stdout + result.stderr}')
        print(f'Exit code: {result.returncode}')
        return Result(id=link.id, output=result.stdout,
                      stderr=result.stderr, exit_code=result.returncode,
                      agent_reported_time=datetime.now(timezone.utc))

    @staticmethod
    def run_command(command, shell_type, timeout=600) -> subprocess.CompletedProcess or None:
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

        # Define a function to run the command and capture the output
        def execute_command():
            nonlocal result
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=timeout)
            except subprocess.TimeoutExpired:
                result = subprocess.CompletedProcess(cmd, returncode=-1, stdout='', stderr='Command timed out.')
            except Exception as e:
                result = subprocess.CompletedProcess(cmd, returncode=-1, stdout='', stderr=str(e))

        # Start command execution in a separate thread
        result = None
        command_thread = threading.Thread(target=execute_command)
        start_time = time.time()
        command_thread.start()

        # Fake loading with spinner and progress bar during command execution
        spinner = itertools.cycle(['|', '/', '-', '\\'])
        logging.debug("Starting command execution...")

        # Use tqdm to create a progress bar with blue color for loading
        with tqdm(desc=f"{Fore.BLUE}Executing", ncols=75, ascii=True) as pbar:
            while command_thread.is_alive():
                command_thread.join(timeout=0.1)  # Wait for a small interval
                elapsed_time = time.time() - start_time
                spin_char = next(spinner)  # Get next spinner character
                # Round elapsed time to 2 decimal places
                pbar.set_postfix_str(f"{spin_char} {elapsed_time:.2f} s")
                pbar.update(0.1)  # Increment progress bar slightly with each loop

            # Close the progress bar once the command execution is complete
            pbar.close()

        # Ensure command thread has finished before exiting
        command_thread.join()

        # Print the final result after the progress bar has been closed
        if result:
            if result.returncode == 0:
                print(f"{Fore.GREEN}Command executed successfully in {time.time() - start_time:.2f} seconds.")
            elif result.returncode == -1:
                print(f"{Fore.RED}{result.stderr}")
            else:
                print(f"{Fore.RED}An error occurred during command execution: {result.stderr}")
        else:
            print(f"{Fore.RED}Command execution failed or timed out.")

        return result

