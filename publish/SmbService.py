# -*- coding: utf-8 -*-

import logging
import os
import sys
from .SMBUtils import SMBUtils

logging.getLogger().setLevel(logging.INFO)
logging.getLogger('SMB.SMBConnection').setLevel(logging.WARNING)
logging.getLogger('SMBUtils').setLevel(logging.WARNING)


class SmbService:
    # InnerServer
    # smb服务器共享文件夹
    mount_point = 'mcp_beta'
    # smb服务器地址
    host = '172.16.3.95'

    work_dir = ''
    # smb服务端口
    port = 139
    # 账户名称
    username = 'umcp'
    # 账户密码
    password = 'mcp'

    # 日志target
    log_target = 'SMBUtils'
    
    server= None
    
    def __init__(self, work_dir='') -> None:
        if(work_dir != ''):
            self.work_dir = work_dir
        
        self.server = SMBUtils(service_name=self.mount_point,
                        sub_working=self.work_dir,
                        host=self.host,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                        log_target=self.log_target)
           
    #获取连接状态        
    def isConnected(self)->bool:
        return self.server.connected()

    def checkRemoteDir(self, remoteDir)->bool:
        if self.isConnected():
            if not self.server.is_exists(remoteDir):
                logging.info("remoteDir not exist create it")
                if not self.server.make_dir(remoteDir):
                    logging.error("create remoteDir failed")
                    return False
        else:
            logging.error("connect failed ! ")
            return False

        if not self.server.is_dir(remoteDir):
            logging.error("remoteDir is not dir ! ")
            return False
        
        print("checkRemoteDir success :" + remoteDir)
        return True


    # 上传文件
    def push(self, localDir, remoteDir)->bool:
        print("localDir=" + localDir)
        print("remoteDir=" + remoteDir)
        
        if not self.isConnected():
            logging.error("connect remote server failed ! ")
            return False
            
        if not self.checkRemoteDir(remoteDir):
            return False
        
        if not self.server.make_dir(remoteDir) :
            logging.error("make_dir: failed")
            return False

        print("push 【" + localDir + "】 to server dir:【" + remoteDir + "】")
        if self.server.copy_dir(localDir, remoteDir, SMBUtils.LOCAL_TO_SERVER, overwrite=True):
            logging.info("copy_dir SMBUtils.LOCAL_TO_SERVER: pass")
            return True
        
        logging.error("copy_dir SMBUtils.LOCAL_TO_SERVER: failed")
        return False

        
if __name__ == '__main__':

    if(not len(sys.argv) == 3):
        print("python publish.py localDir remoteDir")
        exit(-1)

    localDir = sys.argv[1]
    remoteDir = sys.argv[2]

    print("localDir=" + localDir)
    print("remoteDir=" + remoteDir)

    innerServer = SmbService("")

    innerServer.push(localDir, remoteDir)

