# WeiboCrawler

WeiboCrawler是一个Python写的爬虫，主要用来抓取新浪微博的数据。

包括以下组件：

- Scheduler：一个简单的调度器，主要作用分配UID给每个worker，并响应Monitor指令。

- Monitor：监控程序，收集各个worker程序的心跳，并有一个web接口。用户可以在Monitor进行设置。

- Crawler: 爬虫worker程序，每个worker从Scheduler拿到UID，就去抓取这个微博用户数据。
