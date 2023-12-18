import os
import sys
import shutil
import hashlib

#定义一个文件节点
class FileNode:
    def __init__(self, absolutePath, relativePath, md5):
        self.absolutePath = absolutePath
        self.relativePath = relativePath
        self.md5 = md5

#定义一个比较类
class FolderCompare:
    #初始化
    def __init__(self, oldPath, newPath):
        self.old_path = oldPath
        self.new_path = newPath
        self.diff_dict = []

    #比较两个文件夹
    def compare(self):
        #获取两个文件夹的文件列表
        list1 = self.getFileList(self.old_path)
        list2 = self.getFileList(self.new_path)
        #分别计算文件md5值
        old_dict = self.getMD5(list1, self.old_path)
        new_dict = self.getMD5(list2, self.new_path)
        #通过md5值比较两个文件夹的文件
        self.diff_dict = self.getDiff(old_dict, new_dict)

    #获取文件列表
    def getFileList(self, directory):
        # 获取指定目录中的所有文件和文件夹
        file_names = os.listdir(directory)

        #去除隐藏文件
        for i in file_names:
            if i.startswith('.'):
                file_names.remove(i)

        #递归遍历所有文件夹
        for i in range(len(file_names)):
            file_names[i] = os.path.join(directory, file_names[i])
            if os.path.isdir(file_names[i]):
                file_names.extend(self.getFileList(file_names[i]))

        # 使用 os.path.join 获取文件的绝对路径
        absolute_paths = [os.path.join(directory, file_name) for file_name in file_names]

        # 过滤出只是文件而不是文件夹的路径
        absolute_file_paths = [path for path in absolute_paths if os.path.isfile(path)]

        return absolute_file_paths
    
    #获取文件md5值
    def getMD5(self, list, base_path):
        file_dict = {}
        #遍历文件列表
        for i in list:
            #获取文件路径
            filePath = i
            #判断是否是文件
            if os.path.isfile(filePath):
                #获取文件md5值
                md5 = self.calculate_md5(filePath)
                #根据绝对路径获取相对路径
                relativePath = filePath[len(base_path):].strip(os.sep)
                #把md5值放入文件列表中
                file_dict[relativePath] = FileNode(filePath, relativePath, md5)
            #判断是否是文件夹
            elif os.path.isdir(filePath):
                #递归调用
                self.getMD5(self.getFileList(filePath), filePath)
        return file_dict
    
    #获取文件md5值【静态函数】
    @staticmethod
    def calculate_md5(file_path, buffer_size=8192):
        md5_hash = hashlib.md5()
        
        
        with open(file_path, "rb") as file:
            buffer = file.read(buffer_size)
            while buffer:
                md5_hash.update(buffer)
                buffer = file.read(buffer_size)

        return md5_hash.hexdigest()
    
    #通过md5值比较两个文件夹的文件
    @staticmethod
    def getDiff(oldDict, newDict):
        #定义一个列表用于存放不同的文件
        diff = {}
        #遍历文件列表2
        for i in newDict:
            #判断列表2中的文件是否在列表1中
            if i not in oldDict:
                #把不同的文件放入列表中
                diff[i] = newDict[i]
            else:
                #判断文件是否被修改
                if newDict[i].md5 != oldDict[i].md5:
                    #把不同的文件放入列表中
                    diff[i] = newDict[i]

        return diff
    

    def copyDiff(self, diff_dest_path):
        self._copyDiff(self.diff_dict, diff_dest_path)

    #拷贝不同的文件
    def _copyDiff(self, diff_dict, diff_dest_path):
        #遍历文件列表
        for i in diff_dict:
            #获取文件路径
            src_path = os.path.join(self.new_path, i)
            dst_path = os.path.join(diff_dest_path, i)
            #判断是否是文件
            if os.path.isfile(src_path):
                #判断文件夹是否存在
                if not os.path.exists(os.path.dirname(dst_path)):
                    #创建文件夹
                    os.makedirs(os.path.dirname(dst_path))
                #拷贝文件
                shutil.copy(src_path, dst_path)
            #判断是否是文件夹
            elif os.path.isdir(src_path):
                #创建文件夹
                os.mkdir(dst_path)
                #拷贝文件夹
                shutil.copytree(src_path, dst_path)


#main函数
if __name__ == '__main__':
    args = sys.argv
    if len(args) != 4:
        print('Usage: python FolderCompare.py oldPath newPath exportPath')
        sys.exit(1)
    
    previous_path = args[1]
    current_path = args[2]
    export_path = args[3]

    #创建一个比较类
    compare = FolderCompare(previous_path, current_path)
    #调用比较方法
    compare.compare()
    #调用拷贝方法
    compare.copyDiff(export_path)
    #打印结果
    print('diff file count: ', len(compare.diff_dict))
    #打印差异文件列表
    for i in compare.diff_dict:
        print(i)