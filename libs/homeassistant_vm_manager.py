import subprocess
import sys
import time

class VirtualBoxController:
    def __init__(self, vm_uuid):
        self.vm_uuid = vm_uuid

    def _run_vboxmanage(self, command):
        try:
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error: {e.stderr.strip()}")
            sys.exit(1)

    def is_vm_running(self):
        """检查虚拟机是否正在运行"""
        output = self._run_vboxmanage(["VBoxManage", "list", "runningvms"])
        return self.vm_uuid in output or f'"{self.vm_uuid}"' in output

    def start_vm(self):
        """启动虚拟机"""
        if self.is_vm_running():
            print("虚拟机已经在运行中")
            return

        print("正在启动虚拟机...")
        self._run_vboxmanage(["VBoxManage", "startvm", self.vm_uuid, "--type", "headless"])
        print("虚拟机已启动")

    def save_vm_state(self):
        """保存虚拟机状态"""
        if not self.is_vm_running():
            print("虚拟机没有运行，无需保存状态")
            return

        print("正在保存虚拟机状态...")
        self._run_vboxmanage(["VBoxManage", "controlvm", self.vm_uuid, "savestate"])
        
        # 等待虚拟机完全停止
        max_wait = 30
        for _ in range(max_wait):
            if not self.is_vm_running():
                break
            time.sleep(1)
        else:
            print("警告: 等待虚拟机保存状态超时")
            
        print("虚拟机状态已保存")

if __name__ == "__main__":
    VM_UUID = "54bd44fe-3940-43f1-9078-ab9f1f5ec7bb"
    controller = VirtualBoxController(VM_UUID)

    if len(sys.argv) < 2:
        print("用法: python virtualbox_controller.py [start|save|status]")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        controller.start_vm()
    elif command == "save":
        controller.save_vm_state()
    elif command == "status":
        print("虚拟机正在运行" if controller.is_vm_running() else "虚拟机没有运行")
    else:
        print("未知命令，请使用 start, save 或 status")
        sys.exit(1)    