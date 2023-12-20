import os
import sys
import json

#定义一个版本节点
class VersionNode:
    def __init__(self, type, version, pull_url, push_url, package_name):
        self.type = type
        self.version = version
        self.pull_url = pull_url
        self.push_url = push_url
        self.package_name = package_name

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
            if 'platform' in param:
                if param["platform"] != system_type:
                    continue
            for package in param["packages"]:
                type = package["type"]
                pull_url=""
                push_url=""
                if 'pull_url' in package:
                    pull_url = package["pull_url"]
                if 'push_url' in package:
                    push_url = package["push_url"]
                version = package["version"]
                package_name = package["package_name"]
                #循环移除尾部的斜杠
                while push_url.endswith("/"):
                    push_url = push_url[:-1]
                node = VersionNode(type, version, pull_url, push_url, package_name)
                self.version_dict[type] = node

    #打印解析结果
    def print(self):
        for type in self.version_dict:
            node = self.version_dict[type]
            print("type: " + node.type + " version: " + node.version + " pull_url: " + node.pull_url + " push_url: " + node.push_url)

    def get_param_dict(self):
        return self.version_dict
    
    def get_param(self, type):
        return self.version_dict[type]
    

