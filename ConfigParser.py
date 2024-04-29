import os
import sys
import json

#定义一个版本节点
class VersionNode:
    def __init__(self, platform, pre_version, cur_version, server_url, package_name):
        self.platform = platform
        self.previous_version = pre_version
        self.current_version = cur_version
        self.server_url = server_url
        self.package_name = package_name
    
    def get_previous_url(self):
        #返回上个版本包的url
        return self.server_url + "/" + self.previous_version + "/" + ConfigParser.platform_key() + "/" + self.package_name
    
    def get_current_url(self):
        #返回当前版本包的url
        return self.server_url + "/" + self.current_version + "/"  + ConfigParser.platform_key() + "/" + self.package_name
    
    def get_diff_name(self):
        #组装差异包名称 old_version_new_version.zip
        #字符串替换.替换为-， /\ 替换为_
        pre_version=self.previous_version
        pre_version=pre_version.replace("/", "-")
        pre_version=pre_version.replace("\\", "-")
        
        cur_version=self.current_version
        cur_version=cur_version.replace("/", "-")
        cur_version=cur_version.replace("\\", "-")
        
        diff_package_name=pre_version + "~" + cur_version + ".zip"
        
        return diff_package_name
    
    def get_diff_dir_url(self):
        dir_url=self.server_url + "/" + self.current_version + "/" + ConfigParser.platform_key()
        #移除尾部的斜杠
        while dir_url.endswith("/"):
            dir_url = dir_url[:-1]
        return dir_url
    
    def get_diff_url(self):
        #返回版本差异包的url
        return self.get_diff_dir_url()  + "/" + self.get_diff_name()

#解析 config.json 文件
class ConfigParser:
    def __init__(self, config_path):
        self.config_path = config_path
        self.version_dict = {}

    def __init__(self):
        #获取当前文件路径
        self.config_path = os.path.dirname(os.path.realpath(__file__)) + "/config.json"
        self.version_dict = {}
        
    @staticmethod
    def platform_key():
        platform=sys.platform
        if platform == "darwin":
            return "mac"
        elif platform == "win32":
            return "win"
        else:
            return "linux"
        
    def parse(self):
        #读取文件
        with open(self.config_path, 'r', -1, "utf-8") as f:
            config_json = json.load(f)
        #获取当前系统类型
        system_type = ConfigParser.platform_key()
        print("system_type: " + system_type)
        
        #解析文件
        for param in config_json["params"]:
            if 'platform' not in param:
                continue
            if param["platform"] != system_type:
                continue
            platform = param["platform"]
            server_url=""
            if 'server_url' in param:
                server_url = param["server_url"]
            previous_version = param["previous_version"]
            current_version = param["current_version"]
            package_name = param["package_name"]
            #循环移除尾部的斜杠
            while server_url.endswith("/"):
                server_url = server_url[:-1]
            node = VersionNode(platform, previous_version, current_version, server_url, package_name)
            self.version_dict[platform] = node

    #打印解析结果
    def print(self):
        for platform in self.version_dict:
            node = self.version_dict[platform]
            print("paltform: " + node.platform + " previous_version: " + node.previous_version +  "current_version" + node.current_version + " server_url: " + node.server_url)

    def get_param_dict(self):
        return self.version_dict
    
    def get_param(self):
        return self.version_dict[ConfigParser.platform_key()]
    

