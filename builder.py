import os
import shutil
from ConfigParser import ConfigParser
from FolderCompare import FolderCompare
from Utils import Utils
from ZipBuilder import ZipBuilder
from DmgHelper import DmgHelper
from publish.SmbService import SmbService
from publish.SMBUtils import SMBUtils

class builder:
    def __init__(self):
        build_path=os.path.dirname(os.path.realpath(__file__)) + "/build/"
        self.previous=build_path + "previous/"
        self.current=build_path + "current/"
        self.export_path=build_path + "export/"
        self.export_diff_file=""
        self.package_path=build_path + "package/"
        self.mount_path=build_path + "mount/"
        self.mount_path_previous=self.mount_path + "previous/app"
        self.mount_path_current=self.mount_path + "current/app"
        
        self.configParser=ConfigParser()
        self.previousDmgHelper=None
        self.currentDmgHelper=None

    def init_package(self):
        #从共享区拉去包，包括上个版本和当前版本包
        #解析 config.json 文件
        self.configParser.parse()
        self.configParser.print()
        #解压版本包
        if not os.path.exists(self.package_path):
            os.makedirs(self.package_path)
        #拉取 previous 版本包
        previous_package_path=self.package_path + "previous/"
        if not os.path.exists(previous_package_path):
            os.makedirs(previous_package_path)
        previous_file=self._pull_package("previous", previous_package_path)
        if previous_file == "":
            return False
        #拉取 current 版本包
        current_package_path=self.package_path + "current/"
        if not os.path.exists(current_package_path):
            os.makedirs(current_package_path)
        current_file=self._pull_package("current", current_package_path)
        if current_file == "":
            return False
        
        #如果是dmg文件，挂载
        if previous_file.endswith(".dmg"):
            return self._mount_dmg(previous_file, current_file)
        elif previous_file.endswith(".zip"):
            return self._unzip(previous_file, current_file)
        elif previous_file.endswith(".exe"):
            return self._mount_exe(previous_file, current_file)
        
        return False 
    
    def _mount_dmg(self, previous_file, current_file):
        #挂载 previous 版本包
        if not os.path.exists(self.mount_path_previous):
            os.makedirs(self.mount_path_previous)
        previous_mount_path=self.mount_path_previous
        if not os.path.exists(previous_mount_path):
            os.makedirs(previous_mount_path)
        self.previousDmgHelper=DmgHelper(previous_file, previous_mount_path)
        self.previousDmgHelper.mount()
        
        #挂载 current 版本包
        if not os.path.exists(self.mount_path_current):
            os.makedirs(self.mount_path_current)
        current_mount_path=self.mount_path_current
        if not os.path.exists(current_mount_path):
            os.makedirs(current_mount_path)
        self.currentDmgHelper=DmgHelper(current_file, current_mount_path)
        self.currentDmgHelper.mount()
        return True
    
    #解压 zip 文件
    def _unzip(self, previous_file, current_file):
        #解压 previous 版本包
        ZipBuilder(previous_file).decompress(self.mount_path_previous)
        #解压 current 版本包
        ZipBuilder(current_file).decompress(self.mount_path_current)
        return True
    
    #挂载 exe 文件
    def _mount_exe(self, previous_file, current_file):
        #挂载 previous 版本包
        if not os.path.exists(self.mount_path_previous):
            os.makedirs(self.mount_path_previous)
        previous_mount_path=self.mount_path_previous
        if not os.path.exists(previous_mount_path):
            os.makedirs(previous_mount_path)
        #TODO ....
        #挂载 current 版本包
        if not os.path.exists(self.mount_path_current):
            os.makedirs(self.mount_path_current)
        current_mount_path=self.mount_path_current
        if not os.path.exists(current_mount_path):
            os.makedirs(current_mount_path)
        #TODO ....
        
        return True
        
    def _pull_package(self, type, package_path):
        #拉取版本包
        #拉取 previous 版本包
        param=self.configParser.get_param(type)
        file_path=""
        #判断是 git 还是共享地址
        if param.pull_url.startswith("git@"):
            #拉取 git 包
            pass
        else:
            #拉取共享地址包
            file_path = Utils.download(param.pull_url, package_path)

        return file_path
    
    def build(self):
        #判断路径是否存在
        if not os.path.exists(self.mount_path_previous):
            print("previous path does not exist!")
            return False
        if not os.path.exists(self.mount_path_current):
            print("current path does not exist!")
            return False
        
        #构建
        folderCompare=FolderCompare(self.mount_path_previous, self.mount_path_current)
        folderCompare.compare()
        #调用拷贝方法
        diff_path=self.export_path+"diff/"
        folderCompare.copyDiff(diff_path)
        #把 export 文件夹打包成 zip
        diff_package_name=self.configParser.get_param("diff").package_name
        if not diff_package_name.endswith(".zip"):
            diff_package_name + ".zip"
        #判断下是否只有一个子文件夹，如果只有一个子文件夹，那么把子文件夹的名字作为 zip 的名字
        child_path=diff_path
        lstChild = os.listdir(child_path)
        lstChild = builder.remove_invalid_file(lstChild)
        if len(lstChild) == 1:
            child_path+=lstChild[0]
        zipBuilder=ZipBuilder(child_path)
        diff_package_path=os.path.dirname(self.export_path) + "/package/" + diff_package_name
        if zipBuilder.compress(diff_package_path):
            self.export_diff_file=diff_package_path
            return True
        
        return False

    @staticmethod
    def remove_invalid_file(file_list):
        #移除.DS_Store文件
        filter_list=[item for item in file_list if not item.endswith(".DS_Store")]
        return filter_list
        
    def upload(self):
        #上传
        print("begin upload.....")
        #判断待上传文件是否存在
        if not os.path.exists(self.export_diff_file):
            print("export_diff_file does not exist!")
            return False
        
        server=SmbService()
        try:
            pushState = server.push(os.path.dirname(self.export_diff_file), self.configParser.get_param("diff").push_url)
        except:
            pushState = False
            
        print("end upload.....")
        
        return pushState

    def clear(self):
        #清理
        #清理 package 文件夹
        if os.path.exists(self.package_path):
            shutil.rmtree(self.package_path)
        #清理 export 文件夹
        if os.path.exists(self.export_path):
            shutil.rmtree(self.export_path)
        #清理 previous 文件夹
        if os.path.exists(self.previous):
            shutil.rmtree(self.previous)
        #清理 current 文件夹
        if os.path.exists(self.current):
            shutil.rmtree(self.current)
        #卸载 previous dmg 文件
        if self.previousDmgHelper != None:
            self.previousDmgHelper.unmount()
        #卸载 current dmg 文件
        if self.currentDmgHelper != None:
            self.currentDmgHelper.unmount()
            
        #清理 mount 文件夹
        if os.path.exists(self.mount_path):
            shutil.rmtree(self.mount_path)
        print("clear success!")



if __name__ == '__main__':
    builder = builder()
    builder.clear()
    if not builder.init_package():
        builder.clear()
        exit(1)
    if not builder.build():
        builder.clear()
        exit(1)
    if not builder.upload():
        builder.clear()
        exit(1)
    builder.clear()