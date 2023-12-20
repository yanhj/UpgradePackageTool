import wget
import os
import sys

#定义一个下载类
class Utils:
    #使用 wget下载文件
    @staticmethod
    def download(url, path):
        file_path=wget.download(url, path)
        if not os.path.exists(path):
            print("download failed of url: " + url)
            print("download failed of path: " + file_path)
        else:
            print("download success of url: " + url)
            print("download success of path: " + file_path)
            
        return file_path
    
            
        