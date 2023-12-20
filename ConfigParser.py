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

    def parse(self):
        #读取文件
        with open(self.config_path, 'r') as f:
            config_json = json.load(f)
        #解析文件
        for param in config_json["params"]:
            type = param["type"]
            pull_url=""
            push_url=""
            if 'pull_url' in param:
                pull_url = param["pull_url"]
            if 'push_url' in param:
                push_url = param["push_url"]
            version = param["version"]
            package_name = param["package_name"]
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
    

