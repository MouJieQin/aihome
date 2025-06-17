import subprocess
import sys
import time
from homeassistant_api import Client
from libs.log_config import logger
from typing import Dict, Any, Optional


class SingletonMeta(type):
    """
    Metaclass for implementing the Singleton pattern.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class VirtualBoxController(metaclass=SingletonMeta):
    """
    A class for controlling a VirtualBox virtual machine.

    Attributes:
        vm_uuid (str): The UUID of the virtual machine.
    """

    def __init__(self, config: Optional[Dict[str, Any]]):
        """
        Initializes the VirtualBox controller with the given VM UUID.

        Args:
            vm_uuid (str, optional): The UUID of the virtual machine.
        """
        # Ensure initialization only happens once
        if not hasattr(self, "_initialized"):
            if config is None:
                raise ValueError("config must be provided on first initialization")
            self.config: Dict[str, Any] = config
            self._init()
            self._initialized = True

    def _init(self):
        self.vm_uuid = self.config["virtualbox"]["ha_vm_uuid"]
        ha_config = self.config["home_assistant"]
        api_url = f"http://{ha_config['host']}:{ha_config['port']}/api"
        self.client = Client(api_url, ha_config["long_lived_access_token"])

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

    def check_ready(self) -> bool:
        """
        Check if the Home Assistant virtual machine is ready.

        Returns:
            bool: True if the VM is ready, False otherwise.
        """
        try:
            for devices in self.config["smart_home_appliances"].values():
                for id in devices["entity_id"].values():
                    self.client.get_state(entity_id=id)
            return True
        except Exception as e:
            logger.warning(f"Check Home Assistant virtual machine ready failed: {e}")
            return False

    def start_ha_vm_until_ready(self, max_retries=5) -> bool:
        """
        Start the Home Assistant virtual machine and wait until it's ready.

        Args:
            max_retries (int, optional): Maximum number of retries. Defaults to 5.
        """
        self.start_vm()
        for _ in range(max_retries):
            if self.check_ready():
                return True
            time.sleep(3)
        else:
            logger.error("Check Home Assistant virtual machine ready timeout.")
            return False

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
