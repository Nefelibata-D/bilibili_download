# Bilibili-Download

一个基于python编写的B站视频下载器

[![Security Status](https://www.murphysec.com/platform3/v31/badge/1676795760900915200.svg)](https://www.murphysec.com/console/report/1676795760733143040/1676795760900915200)

## 1. 项目使用的第三方库

* requests
* qrcode
* rich

安装项目所需第三方库：

    pip install requests, qrcode, rich

## 2. 使用说明

### 2.1 相关参数

    -h, --help     查看帮助信息
    -b, --bvid     视频BV号
    -n, --name     视频重新命名
    -l, --login    仅登录, 生成config.json文件
    -t, --thread   下载视频线程数, 默认为8线程, 支持线程数为[2, 4, 8, 16, 32]
    -o, --output   允许ffmpeg输出视频合并日志
    -s, --ssid     番剧下载提供的ssid
    -e, --epid     课程下载中任意课程的epid
    -k, --keep     继续上次意外退出未完成的任务

### 2.3 使用方法

    python bilibili.py [OPTIONS]
    
    examples:
        python bilibili.py -b BV1A54y1F7v6 
        python bilibili.py -b BV1A54y1F7v6 -n test -t 16 -o
        python bilibili.py -s 35220  # https://www.bilibili.com/bangumi/play/ss35220
        python bilibili.py -e 6174   # https://www.bilibili.com/cheese/play/ep6174
        python bilibili.py -k  # 启用断点续传

## 3. Tips

* 使用该工具，需要登录B站账号，本下载器无破解功能，只能下载本身你的账号能看到的东西；若账号非VIP，则无法下载高质量视频
* 电影下载：在网页端找到对应视频， 将浏览器全屏后，下翻至电影简介处，可以找到BV号<br/>
* 番剧下载：在网页端搜索番剧名称，从搜索界面点击进入番剧观看页，此时地址栏便能找到类似于“ss35220”的ssid
* 课程下载：在课程观看页，任意点击一个非当前正在播放的课程，之后地址栏便能刷选出类似于“ep6174”的epid，提供任意epid均可以获取全部课程信息
* 断点续传：目前有一类视频是一个bvid下有多个视频分集，这种情况断点续传无法保存之前的选择状态，但仍可以完成程序意外关闭前正在进行的下载任务；
          除此之外，其余视频均可以正常断点续传
* 杜比音效 & Hi-Res：目前未发现B站有可以批量下载的此类视频，所以无法做测试，暂不支持