import itertools
import logging
import subprocess
import time
from datetime import datetime, timezone

import psutil
from colorama import Fore, init
from tqdm import tqdm

init(autoreset=True)

from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_result import Result
from app.utility.base_service import BaseService


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
              f'Running procedure: {link.display["ability"]["name"]}\n'
              f'{link.display["ability"]["tactic"].capitalize()}: '
              f'{link.display["ability"]["technique_name"]} ({link.display["ability"]["technique_id"]})\n'
              f'Description: {link.display["ability"]["description"]}\n\n{os}-{shell}> {command}')
        result = self.run_command(command, shell, link.executor.timeout)
        logging.debug(f'Result:\n{result.stdout + result.stderr}')
        print(f'Exit code: {result.returncode}')
        return Result(id=link.id, output=result.stdout,
                      stderr=result.stderr, exit_code=result.returncode,
                      agent_reported_time=datetime.now(timezone.utc))

    @staticmethod
    def kill_process_and_children(pid):
        """
        Kill a process and all its children using psutil.
        """
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except psutil.NoSuchProcess:
            pass

    def run_command(self, command, shell_type, timeout=1) -> subprocess.CompletedProcess or None:
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

        # Start command execution using Popen
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=False)
        except Exception as e:
            print(f"\n{Fore.RED}An error occurred during command execution: {e}")
            return subprocess.CompletedProcess(cmd, returncode=-1, stdout='', stderr=str(e))

        start_time = time.time()
        spinner = itertools.cycle(['|', '/', '-', '\\'])  # Spinner characters
        logging.debug("Starting command execution...")

        # Create a progress bar using tqdm
        with tqdm(desc=f"{Fore.BLUE}Loading", ncols=75, ascii=True) as pbar:
            while True:
                # Check if the process has completed
                if process.poll() is not None:
                    break  # Break the loop if process has finished

                elapsed_time = time.time() - start_time
                spin_char = next(spinner)  # Get next spinner character

                # Update the progress bar and set postfix with rounded elapsed time
                pbar.set_postfix_str(f"{spin_char} {elapsed_time:.2f} s")
                pbar.update(0.1)  # Increment progress bar slightly with each loop

                # Check if the elapsed time exceeds the timeout
                if elapsed_time > timeout:
                    print(f"\n{Fore.RED}Command timed out after {timeout} seconds.")
                    self.kill_process_and_children(process.pid)  # Kill the process and all its children
                    stdout, stderr = process.communicate()  # Capture the remaining output
                    return subprocess.CompletedProcess(cmd, returncode=-1, stdout=stdout, stderr='Command timed out.')

                time.sleep(0.1)  # Sleep for a short interval to prevent busy-waiting

        pbar.close()  # Close the progress bar once the command execution is complete

        # Wait for process to complete and capture output
        stdout, stderr = process.communicate()

        # Create CompletedProcess result to return
        result = subprocess.CompletedProcess(cmd, returncode=process.returncode, stdout=stdout, stderr=stderr)

        # Print the final result after the progress bar has been closed
        if result.returncode == 0:
            print(f"{Fore.GREEN}Command executed successfully in {time.time() - start_time:.2f} seconds.")
        elif result.returncode == -1:
            print(f"{Fore.RED}{result.stderr}")
        else:
            print(f"{Fore.RED}An error occurred during command execution: {result.stderr}")

        return result
