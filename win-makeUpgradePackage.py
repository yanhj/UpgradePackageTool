import os
import sys
import wget
import subprocess
import shutil
import urllib.request
from ZipBuilder import ZipBuilder

from SMBUtils import SMBUtils

remote_shared_path="http://share.mtlab.meitu.com/share/MCP-beta/vidme-release/"

def post_file(url, file_path):
    #check the file path
    if not os.path.exists(file_path):
        print("Error: file path not exist" + file_path)
        return ""
    print("post file 1 file_path : " + file_path)
    print("post file 2 url : " + url)

    with open(file_path, 'rb') as f:
        response = requests.post(url, files={'file': f})
        #check the response status code
        if response.status_code != 200:
            print("Error: " + response.text)
            return ""

        #parse the response json text,get the file url
        json_data = response.json()
        if "data" not in json_data:
            print("parse json Error: " + response.text)
            return ""

        data_obj = json_data["data"]
        if "url" not in data_obj:
            print("parse json Error: " + response.text)
            return ""
        url = data_obj["url"]

        return url
        #print(response.text)


class SmbService:

    # InnerServer
    # smb服务器共享文件夹
    mount_point = 'mcp_beta'
    # smb服务器地址
    host = '172.16.3.95'

    work_dir = 'vidme-release'
    # smb服务端口
    port = 139
    # 账户名称
    username = 'umcp'
    # 账户密码
    password = 'mcp'

    # 日志target
    log_target = 'mcp-log'

class Builder:
    def __init__(self, binary_path, _package_path):
        self._package_path =_package_path

        self.post_url = "http://vidframe-mtlab-server.meitu-int.com/v1/qms/qmsSoftwareUpgradePkg/uploadSoftwareXML"
        self.binary_path = binary_path

        #url must be end with /
        if not self.binary_path.endswith("/"):
            self.binary_path += "/"

        self.diff_version_file_dir_path = self.binary_path +"package/"

        self.innerServer = None

        pass

    def download_file_from_server(self, url, target_path):
        #check the file path
        if url == "":
            print("Error: url not exist")
            return
        url = url.replace(remote_shared_path, "")
        if self.innerServer is None:
            print("Error: innerServer not init")
            return

        if not self.innerServer.connected():
            print("connect innerServer failed ! ")
            return
        self.innerServer.copy_file(url, target_path, SMBUtils.SERVER_TO_LOCAL)




    def init_server(self):
        self.innerServer = SMBUtils(service_name=SmbService.mount_point,
                               sub_working=SmbService.work_dir,
                               host=SmbService.host,
                               port=SmbService.port,
                               username=SmbService.username,
                               password=SmbService.password,
                               log_target=SmbService.log_target)

        if not self.innerServer.connected():
            print("connect innerServer failed ! ")
            exit(0)
    def filter_file_by_ext(self, path, ext):
        #check the path
        if not os.path.exists(path):
            print("Error: path not exist")
            return ""

        files = os.listdir(path)
        for file in files:
            if file.endswith(ext):
                return os.path.join(path, file)

        return ""
    
    def loginAndDownload(self, url, target_path):
           # URL     
        # 用户名和密码
        username = 'umcp'
        password = 'mcp'

        # 构建包含用户名和密码的认证处理器
        password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, username, password)
        auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

        # 创建 URLopener，并添加认证处理器
        opener = urllib.request.build_opener(auth_handler)

        try:
            # 使用认证处理器打开 URL，并下载文件
            with opener.open(url) as response, open(target_path, 'wb') as out_file:
                out_file.write(response.read())
            print("File downloaded successfully!")
        except URLError as e:
            print("File download failed:", e.reason)
            
    def build(self):
        #remove the make_package directory
        if os.path.exists(self.diff_version_file_dir_path):
            shutil.rmtree(self.diff_version_file_dir_path)

        #if the make_package directory not exist, create it
        if not os.path.exists(self.diff_version_file_dir_path):
            os.makedirs(self.diff_version_file_dir_path)

        #if file is remote url, download it
        if self._package_path.startswith("http"):
            #parse url to get version
            _version = self._package_path.replace(remote_shared_path, "")
            _version = os.path.dirname(_version)
            _version = os.path.dirname(_version)
            _version = _version.replace("/", "-")
            target_path = self.diff_version_file_dir_path + "VidMeCreator-win-" + _version + ".zip"
            print("_package_path: " + self._package_path)
            print("target_path: " + target_path)
            self.download_file_from_server(self._package_path, target_path)
            self._package_path = target_path
            
        #check the target path
        if not os.path.exists(self._package_path):
            print("Error: old package path not exist")
            sys.exit(0)
            return
        
        ZipBuilder(self._package_path).decompress(self.diff_version_file_dir_path)
       
        package_folder = self.diff_version_file_dir_path + "/VidMeCreator"
        compress_cache = self.diff_version_file_dir_path + "/compress_cache"
        json_file = self.diff_version_file_dir_path + "/manifest.json"
        #check the diff_version_file_dir_path
        if not os.path.exists(self.diff_version_file_dir_path):
            print("Error: diff_version_file_dir_path not exist")
            sys.exit(0)
            return
        
        #create the package_folder
        if not os.path.exists(package_folder):
            os.makedirs(package_folder)
        
        # Do something with self.path
        #run command to build the project
        cmd_line="AssetGenerator.exe " + " -v=" + _full_version + " -p=" + package_folder + " -c=" + compress_cache + " -j=" + json_file
        print(cmd_line)
        result = subprocess.run(cmd_line, cwd=self.binary_path, shell=True, check=True, stdout=subprocess.PIPE, text=True)


def format_version(version, build_type, build_number):
    #x.x.x/Beta/4 or x.x.x/Release/4, convert to x.x.x.1.4 or  x.x.x.2.4
    #compare string by case-insensitive
    build_type = build_type.lower()
    if build_type == "alpha":
        version = version + ".0"
    elif build_type == "beta":
        version = version + ".1"
    elif build_type == "release":
        version = version + ".2"
    version = version + "." + build_number
    
    return version

def compare_version(old_version, new_version):
    #compare the version number
    #return 1 if old_version > new_version, return 0 if old_version == new_version, return -1 if old_version < new_version
    #split the version by "."
    old_version = old_version.split(".")
    new_version = new_version.split(".")
    
    #compare the version number
    for i in (0, len(new_version) - 1):
        if old_version[i] == new_version[i]:
            continue
        if old_version[i] > new_version[i]:
            return 1
        else:
            return -1
        
    
    return 0

if __name__ == "__main__":
    #argv[1] package version regular "1.1.2/Beta/4"
    #argv[3] binary path
    #parse the command line arguments
    argv = sys.argv
    if 1:
        pass
        argv.append("1.1.2/Beta/8")
        argv.append("D:/Code/Videme-PC/build-script/make_upgrade_package/")

    if len(argv) != 3:
        print("Error: Invalid arguments")
        exit(0)

    #check version is valid, version must be like "1.1.2/Beta/4"
    if not argv[1].count("/") == 2:
        print("Error: Invalid version, version must be like '1.1.2/Beta/4'")
        exit(0)
        
    #split the version to get the version number
    _full_version = format_version(argv[1].split("/")[0], argv[1].split("/")[1], argv[1].split("/")[2])
    
    print("version: " + _full_version)
        
    _package_path = remote_shared_path + argv[1] + "/win/VidMeCreator.zip"
    binary_path = argv[2]

    #check the old package path
    if not _package_path.startswith("http") and not os.path.exists(_package_path):
        print("Error: old package path not exist")
        exit(0)

    #check the binary path
    if not os.path.exists(binary_path):
        print("Error: binary path not exist")
        exit(0)

    print("_package_path: " + _package_path)
    print("binary_path: " + binary_path)

    builder = Builder(binary_path, _package_path)
    builder.init_server()
    builder.build()
