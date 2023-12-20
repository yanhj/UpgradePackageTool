import os
import subprocess
import sys
import shutil

#定义 dmg 文件的一些操作
class DmgHelper:
    def __init__(self, dmg_path, mount_path):
        self.dmg_path = dmg_path
        self.mount_path = mount_path
        self.volume_path = ""
        
    #挂载 dmg 文件
    def mount(self):
        #判断路径是否存在
        if not os.path.exists(self.dmg_path):
            print("dmg path does not exist!")
            return False
        
        #使用 hdiutil 挂载 dmg 文件
        command = "hdiutil attach '" + self.dmg_path + "'" + " -nobrowse -readonly "
        if self.mount_path != "":
            command += " -mountpoint '" + self.mount_path + "'"
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)
        return result.returncode == 0
    
    #卸载 dmg 文件
    def unmount(self):
        #判断路径是否存在
        if not os.path.exists(self.mount_path):
            print("mount path does not exist!")
            return False
        
        #使用 hdiutil 卸载 dmg 文件
        command = "hdiutil detach '" + self.mount_path + "'"
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)
        except:
            print("unmount failed!")
            return False
        return True
    
    