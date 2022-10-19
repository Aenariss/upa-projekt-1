## A file to download the data from the server
# UPA Project 1
# Author: Vojtech Fiala <xfiala61>

import urllib.request
import re
import os
from sys import argv

# Class to download files
# Usage is: import the class and use the getFiles method
class Downloader:
    def __createFolder(self, folder):
        if not (os.path.exists(folder)):
            os.mkdir(folder)

    def __args(self):
        if len(argv) > 1:
            return (argv[1] == '-v')
        return 0

    def __init__(self):
        self.__resource_folder = os.path.dirname(os.path.realpath(__file__)) + '/resources/'
        self.__url = 'https://portal.cisjr.cz/pub/draha/celostatni/szdc/2022/'
        self.__base_url = 'https://portal.cisjr.cz'

        self.__verbose = self.__args()
        self.__createFolder(self.__resource_folder)
    
    # function to download a page, takes an argument that specifies the url to download
    def __downloadPage(self, url):
        page = urllib.request.urlopen(url)
        content = page.read()
        return content
    
    # function to get subpages where wanted files are located
    def __subpages(self, url):
        cnt = self.__downloadPage(url)
        folders = re.findall(b"HREF=\"(.*?)\"", cnt)
        if len(folders) > 0:
            # delete the first link cuz it leads to parent directory
            folders.pop(0)
        return folders

    def __filesInFolder(self, folder):
        # https://stackoverflow.com/a/3207973/13279982
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        return files
    
    def __fileExistsInFolder(self, file, folder):
        return (file in folder)

    def __getFilename(self, file):
        x = re.match('^.*\/(.*)?$', file)
        return x[1]

    def __verbosePrint(self, message):
        if self.__verbose:
            print(message)

    def __downloadFileIfNotExists(self, folder, files_in_folder, url, destination, verbose):
        file = self.__getFilename(folder)
        if not (self.__fileExistsInFolder(file, files_in_folder)):
            urllib.request.urlretrieve(url, destination)
            self.__verbosePrint(verbose + " has been downloaded")
        else:
            self.__verbosePrint(file + " already exists!")

    # function that downloads files from the webpage if theyre not already downlaoded
    def getFiles(self):
        folders = self.__subpages(self.__url)
        files_in_folder = self.__filesInFolder(self.__resource_folder)

        for folder in folders:
            folder = folder.decode('utf-8')
            # it's not a folder, its a file
            if (folder[-3:] == 'zip'):
                self.__downloadFileIfNotExists(folder, files_in_folder, self.__base_url + folder, self.__resource_folder + file, self.__resource_folder + file)
            
            # its an actual folder
            else:
                if (self.__verbose):
                    print("going through files in " + self.__base_url + folder)

                folder_name = self.__resource_folder + self.__getFilename(folder[:-1])
                self.__createFolder(folder_name)
                train_files = self.__subpages(self.__base_url + folder)
                files_in_subfolder = self.__filesInFolder(folder_name)

                for file in train_files:
                    file = file.decode('utf-8')
                    if (file[-3:] == 'zip'):  # if its actually a file
                        file_name = self.__getFilename(file)
                        self.__downloadFileIfNotExists(file, files_in_subfolder, self.__base_url + file, folder_name + '/' +  file_name, self.__base_url + file)
