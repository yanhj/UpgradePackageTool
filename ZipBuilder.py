import os
import zipfile
import shutil
import sys
import subprocess

class ZipBuilder:
    def __init__(self, input_path):
        self.src_path = input_path
    
    def compress(self, dst_zip_path):
        if not os.path.exists(self.src_path):
            print("Source path does not exist!")
            return False
        if os.path.exists(dst_zip_path):
            # 已存在先删除目标文件
            os.remove(dst_zip_path)
        if os.path.isfile(self.src_path):
            self._compress_file(self.src_path, dst_zip_path)
        else:
            self._compress_dir(self.src_path, dst_zip_path)
        return True
    
    def _compress_file(self, src_file, dst_file):
        # 获取目录的上级目录
        base_path = os.path.dirname(src_file)
        self._compress(base_path, dst_file, os.path.basename(src_file))

    def _compress_dir(self, src_file, dst_file):
        # 获取目录的上级目录
        base_path = os.path.dirname(src_file)
        self._compress(base_path, dst_file, os.path.basename(src_file))

    def _compress(self, src_dir, dst_dir, special_file="."):
        # 使用 subprocess.run 执行系统命令
        #判断源文件夹是否存在
        if not os.path.exists(src_dir):
            print("Source path does not exist!")
            return False
        
        #压缩文件夹
        if special_file == "":
            special_file = "."
        
        platform=sys.platform
        if platform == "darwin":
            command = "tar -chzf '" + dst_dir + "' -C '" + src_dir + "' " + special_file
        elif platform == "win32":
            #获取zip.exe文件路径
            zip_path=os.path.dirname(os.path.realpath(__file__)) + "/zip-win/bin/zip.exe"
            #若要压缩文件夹后保持相对路径，需要cd到待压缩文件夹所在目录
            command = zip_path + ' -r "' + dst_dir + '" .'   
        result = subprocess.run(command, cwd=src_dir, shell=True, check=True, stdout=subprocess.PIPE, text=True)
        
        return result.returncode == 0

    def decompress(self, dst_path):
        if not os.path.exists(self.src_path):
            print("Source path does not exist!")
            return False
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        # 使用 subprocess.run 执行系统命令
        platform=sys.platform
        if platform == "darwin":
            command = "tar -xzf '" + self.src_path + "' -C '" + dst_path + "'"
        elif platform == "win32":
            #获取unzip.exe文件路径
            unzip_path=os.path.dirname(os.path.realpath(__file__)) + "/zip-win/bin/unzip.exe"
            command = unzip_path + ' "' + self.src_path + '" -d "' + dst_path + '"'
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)
        return result.returncode == 0


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 3:
        print("Usage: python/python3 ZipBuilder.py input_path dst_zip_path")
        exit(1)

    input_path = args[1]
    dst_zip_path = args[2]
    builder = ZipBuilder(input_path)
    builder.compress(dst_zip_path)
    print("ZipBuilder done!")
    builder = ZipBuilder(dst_zip_path)
    builder.decompress(os.path.dirname(input_path) + '/decompress')
                

