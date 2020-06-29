# /usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Nop
# @Date:   2020-06-28 14:23:03
# @Last Modified by:   song-10
# @Last Modified time: 2020-06-29 10:18:24

# this file could downlaod the ts file which use index.m3u8 instead of other file

import threading
import requests
import re
import os
from Crypto.Cipher import AES
from urllib import parse

flag = False
num_done = 0

# download function(without decode)
def download_direct(cwd, length, addr, ts_list, starts, num):
	global num_done
	# print(ts_list)
	for i in range(length):
		try:
			res = requests.get(addr+'/'+ts_list[i])
			# print('get content!')
			while True:
				try:
					with open(cwd+'/'+str(starts+i)+'.ts','wb') as file:
						file.write(res.content)
						file.flush()
						file.close()
				except Exception as err:
					# print(err)
					pass
				if os.path.getsize(cwd+'/'+str(starts+i)+'.ts') != 0:
					num_done += 1
					break
		except:
			pass


# download and decode function
def download_decode(cwd, length, addr, ts_list, starts, num):
	global num_done
	key = open(cwd+"/key.key",'r').read().encode('utf-8')
	cryptor = AES.new(key,AES.MODE_CBC,key)
	for i in range(length):
		try:
			res = requests.get(addr+'/'+ts_list[i])
			while True:
				try:
					with open(cwd+'/'+str(starts+i)+'.ts','wb') as file:
						file.write(cryptor.decrypt(res.content))
						file.flush()
						file.close()
				except Exception as err:
					# print(err)
					pass
				if os.path.getsize(cwd+'/'+str(starts+i)+'.ts') != 0:
					num_done += 1
					break
		except:
			pass


# show download status
def download_bar(percent, start_str='', total_length=0):
	bar = ''.join(["\033[1;37;47m%s\033[0m"%'   '] * int(percent * total_length)) + ''
	bar = '\r'+' {:0>4.1f}% complete| '.format(percent*100) + start_str + bar.ljust(total_length, ' ')
	print(bar, end='', flush=True)


# combine and remove temp file
def combine():
	file = open('filelist.txt','a+')
	current_path = os.getcwd()+'\\'
	dir_list = []
	for i in os.listdir('.'):
		if i.endswith('ts'):
			dir_list.append(int(i[:-3]))
		else:
			continue
	temp = sorted(dir_list)
	dir_list =[]
	for i in temp:
		dir_list.append(str(i)+'.ts')
		file.write('file	\''+current_path+str(i)+'.ts'+'\'\n')
	file.close()

	os.system('ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4')
	os.system('rm *.ts')
	os.system('rm *.m3u8')
	os.system('rm *.key')
	os.system('rm *.txt')


# get url from html
# This way is only suitable for a small number of websites
def get_url(url):
	req = requests.get(url)
	p = re.compile('http.*.index.m3u8')
	addr = re.findall(p, req.text)[0]
	address = parse.unquote(addr)[:-10]
	req = requests.get(parse.unquote(addr))
	p = re.compile('.*.index.m3u8')
	temp = re.findall(p, req.text)
	if temp:
		address += temp[0][:-10]
	print(address)  
	return address


# thread class
class ThreadDownload(threading.Thread):
	def __init__(self, addr, starts, ts_list, cwd, thread_num, flag):
		threading.Thread.__init__(self)
		self.num = thread_num
		self.addr = addr
		self.starts = starts
		self.ts_list = ts_list
		self.cwd = cwd
		self.length = len(ts_list)
		self.flag = flag
	def run(self):
		if self.flag:
			download_decode(self.cwd, self.length, self.addr, self.ts_list, self.starts, self.num)
		else:
			download_direct(self.cwd, self.length, self.addr, self.ts_list, self.starts, self.num)


# main class
class GetDownload:
	def __init__(self, addr, threadNum):
		self.num = threadNum
		self.addr = addr
		self.cwd = str(os.getcwd())

	def get_index(self):
		res = requests.get(self.addr + '/index.m3u8')
		with open(self.cwd+'/index.m3u8','wb') as file:
			file.write(res.content)
			file.close()
		print('get index successfully!')

	def get_key(self):
		global flag
		try:
			res = requests.get(self.addr + '/key.key', timeout=30)
			if not res.content.startswith('<html>'):
				with open(self.cwd+'/key.key','wb') as file:
					file.write(res.content)
					file.close()
				print('get file key successfully!')
				flag = True
			else:
				flag = False
		except Exception as err:
			# print(err)
			print('this video may be not encoded!')
			flag = False

	# get the rest of files
	def download_rest(self, cwd, length, addr, ts_list, starts, num, flag):
		if flag:
			download_decode(cwd, length, addr, ts_list, starts, num)
		else:
			download_direct(cwd, length, addr, ts_list, starts, num)


	def begin(self):
		global flag
		global num_done
		self.get_index()
		self.get_key()
		with open(self.cwd+'/index.m3u8','r') as file:
			data = file.read()
			file.close()
		pattern = re.compile('.*.ts')
		index_data = re.findall(pattern,data)
		total_length = len(index_data)
		part_length = total_length//self.num
		self.download_rest(self.cwd, len(index_data[self.num*part_length:]), self.addr, index_data[self.num*part_length:], self.num*part_length, 0, flag)
		for i in range(self.num):
			starts = i*part_length
			stop = starts + part_length
			part_list = index_data[starts:stop]
			td = ThreadDownload(self.addr, starts, part_list, self.cwd, i+1, flag)
			td.start()
		# os.system('clear')
		print("downloading...")
		print('-'*63) 
		while True:
			if num_done == total_length-1:
				print("\ndownload has finished!\n")
				combine()
				break
			else:
				download_bar(num_done/total_length,  start_str='', total_length=15)

if __name__ == '__main__':
	addr = input('video address: ')
	addr = get_url(str(addr))
	# print(addr)
	num_thread = int(input('thread you want: '))
	t = GetDownload(addr,num_thread)
	t.begin()
