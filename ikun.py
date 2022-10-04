#知识点：1.python多进程；2.字符帧构造；3.分解视频；合成视频 4.shutil
#参考：https://www.jb51.net/article/250365.htm

import os
import cv2 as cv
from multiprocessing import Process
import sys
import argparse
from PIL import Image,ImageFont,ImageDraw
import math
import time
import shutil

def getChar(pixel):
	charset = 'GHMNADSCVTUIO~^|-,.'
	index_range = len(charset) - 1;
	ratio = pixel/255
	return charset[int(ratio*index_range)]

#frame_path是视频帧的文件夹
def video2frame(cap,frame_path):
	number = 0
	print('正在对视频进行逐帧切片，请稍候')
	if os.path.exists(frame_path):
		files = os.listdir(frame_path)
		number = len(files)
		print('共产生了{}张图片'.format(number))
		return number
	else:
		os.mkdir(frame_path)

	if not cap.isOpened():
		print('视频文件不存在或无法打开')
		exit()

	while True:
		ret, frame = cap.read()
		if not ret:
			break
	    # frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
		cv.imwrite(frame_path+'/{}.jpg'.format(number+1),frame)
		number = number + 1

	print('共产生了{}张图片'.format(number))
	return number

#处理单张视频帧
#img_path是图像路径,char_path是字符帧的文件夹
def generateCharFrame(img_path, char_path):
	filename = os.path.basename(img_path)
	order = filename.split('.')[0]
	im = Image.open(img_path).convert('L')

	w, h = im.size        #原始图像的大小
	font = ImageFont.load_default()
	left, top, right, bottom = font.getbbox('a')  
	nw = int(w / right)
	nh = int(h / bottom)
	im = im.resize((nw,nh),Image.Resampling.NEAREST)      #根据字体大小对图像进行缩放，这里不可以使用crop方法，resize表示降采样

	text = ''
	line_char = ""	#临时存储每一行的字符串

	for i in range(nh):
		for j in range(nw):
			pixel = im.getpixel((j,i))
			line_char += getChar(pixel)
		text += (line_char + '\n')
		line_char = ""
    
	text = text[:-1]
	im_new = Image.new('L',(w,h),255)
	draw = ImageDraw.Draw(im_new)
	draw.text((0,0), text, font=font, spacing=0)

	im_new.save(char_path + "/{}.jpg".format(order))


#字符帧合成为视频
#char_path是字符帧的文件夹，out_path是输出文件夹
def generateVideo(number,char_path, out_path,fps):
	print('开始合成字符视频')
	if not os.path.exists(out_path):
		os.mkdir(out_path)

	video_fourcc = cv.VideoWriter_fourcc(*"MP42") #生成小视频文件编码方式
	im = Image.open(char_path + '/1.jpg')
	char_frame_size = im.size
	video_writer = cv.VideoWriter(out_path + '/a.avi',video_fourcc , fps, char_frame_size)

	for i in range(number):
		im_path = char_path + '/{}.jpg'.format(i+1)
		im = cv.imread(im_path)
		video_writer.write(im)
		end_str = '100%'
		process_bar((i+1)/number,'',end_str)

	video_writer.release()
	print('视频合成完毕！')

class Subprocess(Process):
	#处理[start_number,end_number]之间的图片
	def __init__(self,ThreadID,start_number,end_number,frame_path,char_path):
		super().__init__()
		self.threadID = ThreadID
		self.start_number = start_number
		self.end_number = end_number
		self.frame_path = frame_path
		self.char_path = char_path

	def run(self):
		print('进程{}正在生成字符帧'.format(self.threadID))
		for i in range(self.start_number,self.end_number + 1):
			generateCharFrame(self.frame_path + '/{}.jpg'.format(i),self.char_path)
		print('进程{}结束任务，正在退出...'.format(self.threadID))

def start(number,core_number,frame_path,char_path):
	print('正在开启多进程生成字符帧')

	if not os.path.exists(char_path):
		os.mkdir(char_path)
	else:
		print('字符帧已存在')
		return 

	processes = []

	start_number = 1  #图片编号从1开始
	k = int(number / core_number)
	end_number = k
	for core in range(core_number):
		process = Subprocess(core,start_number,end_number,frame_path,char_path)
		process.start()
		processes.append(process)
		start_number = end_number + 1
		end_number = start_number + k - 1
		if core == core_number:
			end_number = number 
		time.sleep(1)

	return processes

#合并音频
def write_audio(video_path,out_path):

	print('正在合并音频')

	if not os.path.exists(out_path):
		os.mkdir(out_path)

	cmd = 'ffmpeg -i ' + out_path + '/a.avi' + ' -i ' + video_path + ' -c copy -map 0 -map 1:1 -y -shortest ' + out_path + '/videoWithAudio.avi' + ' -y'
	os.system(cmd)
    # 压制成H.264 mp4格式
	cmd2 = 'ffmpeg -i ' + out_path + '/videoWithAudio.avi' + ' -c:v libx264 -strict -2 ' + out_path + '/final_output.mp4' + ' -y'
	os.system(cmd2)

def process_bar(percent, start_str='', end_str='', total_length=15):
	# 进度条
	bar = ''.join("■ " * int(percent * total_length)) + ''
	bar = '\r' + start_str + bar.ljust(total_length) + ' {:0>4.1f}%|'.format(percent * 100) + end_str
	print(bar, end='', flush=True)

if __name__ == '__main__':
	#封装参数
	parser = argparse.ArgumentParser(description='create a char vedio.')
	parser.add_argument('-v','--video_path',type=str,default='ikun.mp4',help='define origin video path (default:"./ikun.mp4").')
	parser.add_argument("--frame_path",type=str,default='frame_path')
	parser.add_argument("--char_path",type=str,default='char_path')
	parser.add_argument('-o',"--out_path",type=str,default='out_path',help='define output path (default:"./out_path").')
	parser.add_argument('-n','--core_number',type=int,default='8',help='the program use multi-process, so you can define the number of cores.')
	args = parser.parse_args()

	cap = cv.VideoCapture(args.video_path)
	number = video2frame(cap,args.frame_path)
	fps = cap.get(cv.CAP_PROP_FPS)
	print(fps)
	#开启多进程生成字符帧
	processes = start(number, args.core_number,args.frame_path,args.char_path) 
	if processes is not None:
		for process in processes:
			process.join()
	cap.release()
	generateVideo(number,args.char_path,args.out_path,fps)
	try:
		write_audio(args.video_path,args.out_path)
	except:
		print('ffmpeg 未找到，请安装后重试')

	try:
		shutil.rmtree(args.frame_path)
		shutil.rmtree(args.char_path)
	except:
		print('frame_path or char_path not found!')
