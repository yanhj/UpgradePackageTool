import os
import zipfile
import shutil
import sys
import subprocess

class ZipBuilder:
    def __init__(self, input_path, dst_zip_path):
        self.src_path = input_path
        self.dst_path = dst_zip_path
    
    def compress(self):
        if not os.path.exists(self.src_path):
            print("Source path does not exist!")
            return False
        if os.path.exists(self.dst_path):
            # 已存在先删除目标文件
            os.remove(self.dst_path)
        if os.path.isfile(self.src_path):
            self._compress_file(self.src_path, self.dst_path)
        else:
            self._compress_dir(self.src_path, self.dst_path)
        return True
    
    def _compress_file(self, src_file, dst_file):
        # 获取目录的上级目录
        base_path = os.path.dirname(src_file)
        self._compress(base_path, dst_file, os.path.basename(src_file))

    def _compress_dir(self, src_file, dst_file):
        # 获取目录的上级目录
        base_path = os.path.dirname(src_file)
        self._compress(base_path, dst_file, os.path.basename(src_file))

    def _compress(self, src_dir, dst_dir, special_file='.'):
        # 使用 subprocess.run 执行系统命令
        #压缩文件夹
        command = "tar -chzf '" + dst_dir + "' -C '" + src_dir + "' " + special_file
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)

    def decompress(self):
        if not os.path.exists(self.src_path):
            print("Source path does not exist!")
            return False
        if not os.path.exists(self.dst_path):
            os.makedirs(self.dst_path)
        # 使用 subprocess.run 执行系统命令
        command = "tar -xzf '" + self.src_path + "' -C '" + self.dst_path + "'"
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)
        return True


if __name__ == '__main__':
    args = sys.argv
    if len(args) < 3:
        print("Usage: python/python3 ZipBuilder.py input_path dst_zip_path")
        exit(1)
        
    input_path = args[1]
    dst_zip_path = args[2]
    builder = ZipBuilder(input_path, dst_zip_path)
    builder.compress()
    print("ZipBuilder done!")
    builder = ZipBuilder(dst_zip_path, os.path.dirname(input_path) + '/decompress')
    builder.decompress()
                

