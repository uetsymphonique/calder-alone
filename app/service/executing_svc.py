import logging
import subprocess
from base64 import b64encode
from datetime import datetime, timezone

from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_result import Result
from app.service.data_svc import DataService
from app.utility.base_service import BaseService


class ExecutingService(BaseService):
    def __init__(self):
        self.log = self.add_service('executing_svc', self)

    def running(self, link: Link):
        """
        Executes a command linked to a link and returns the output.
        :param link: Link object
        :return: Output of the command
        """

        command = link.display["command"]
        shell = link.executor.name
        print(f'Running ability: {link.display["ability"]["name"]}\nCommand: {command} will be ran in {shell}')
        result = self.run_command(command, shell)
        return Result(id=link.id, output=result.stdout,
                      stderr=result.stderr, exit_code=result.returncode,
                      agent_reported_time=datetime.now(timezone.utc))

    @staticmethod
    def run_command(command, shell_type) -> subprocess.CompletedProcess or None:
        shell_map = {
            'psh': ['powershell', '-Command'],
            'pwsh': ['pwsh', '-Command'],
            'sh': ['sh', '-c'],
            'proc': None  # Run directly without any shell
        }

        # Check if shell type is valid
        if shell_type not in shell_map:
            raise ValueError(f"Invalid shell type '{shell_type}'. Choose from 'psh', 'sh', 'pwsh', or 'proc'.")

        # Prepare the command to execute
        if shell_map[shell_type] is None:  # 'proc' case, direct execution
            cmd = command.split()  # Assumes the command is space-separated
        else:
            cmd = shell_map[shell_type] + [command]

        # Execute the command
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            # Return output if successful, otherwise return the error
            return result
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            return None
