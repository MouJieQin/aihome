import subprocess
import sys
import time
from libs.log_config import logger


class VirtualBoxController:
    """
    A class for controlling a VirtualBox virtual machine.

    Attributes:
        vm_uuid (str): The UUID of the virtual machine.
    """

    def __init__(self, vm_uuid):
        """
        Initializes the VirtualBox controller with the given VM UUID.

        Args:
            vm_uuid (str): The UUID of the virtual machine.
        """
        self.vm_uuid = vm_uuid

    def _run_vboxmanage(self, command):
        """
        Execute a VBoxManage command and handle exceptions.

        Args:
            command (list): A list containing the command and its arguments.

        Returns:
            str: The standard output of the command, stripped of whitespace.
        """
        try:
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.exception(f"Error: {e.stderr.strip()}")
            sys.exit(1)

    def _check_vm_status(self, status_checker):
        """
        Check the VM status using a provided checker function and print a message.

        Args:
            status_checker (callable): A function that returns a boolean indicating VM status.

        Returns:
            bool: The result of the status check.
        """
        status = status_checker()
        if status:
            logger.debug("The virtual machine is already running")
        return status

    def is_vm_running(self):
        """
        Check if the virtual machine is currently running.

        Returns:
            bool: True if the VM is running, False otherwise.
        """
        output = self._run_vboxmanage(["VBoxManage", "list", "runningvms"])
        return self.vm_uuid in output or f'"{self.vm_uuid}"' in output

    def start_vm(self):
        """
        Start the virtual machine if it's not already running.
        """
        if self._check_vm_status(self.is_vm_running):
            return

        logger.info("Starting the virtual machine...")
        self._run_vboxmanage(
            ["VBoxManage", "startvm", self.vm_uuid, "--type", "headless"]
        )
        logger.info("The virtual machine has been started")

    def _wait_for_vm_to_stop(self, max_wait=30):
        """
        Wait for the virtual machine to stop running.

        Args:
            max_wait (int, optional): Maximum wait time in seconds. Defaults to 30.
        """
        for _ in range(max_wait):
            if not self.is_vm_running():
                break
            time.sleep(1)
        else:
            logger.warning(
                "Warning: Timed out waiting for the virtual machine to save its state"
            )

    def save_vm_state(self):
        """
        Save the current state of the virtual machine if it's running.
        """
        if not self.is_vm_running():
            logger.warning(
                "The virtual machine is not running. No need to save the state."
            )
            return

        logger.info("Saving the virtual machine state...")
        self._run_vboxmanage(["VBoxManage", "controlvm", self.vm_uuid, "savestate"])
        self._wait_for_vm_to_stop()
        logger.info("The virtual machine state has been saved")
