# 沈校亮学术主页

正式网站为 [xlshen.cn](https://xlshen.cn/)。新闻收录在[学术动态](https://xlshen.cn/news.html)，学生可从[课程实验](https://xlshen.cn/course-lab.html)进入信息接收分布实验室。

## 更新网站

编辑 `site/` 中对应的 HTML。首页与学术动态各保留一份按日期倒序排列的新闻列表。新闻附件存放在 `site/assets/`，使用相对链接。

运行 `python3 tools/build_release.py` 生成 `site.zip` 和 `release.json`。将网页源文件、附件以及这两个发布文件一并提交到 `main`。武汉服务器约每十分钟读取一次分支，在完整性和课程资源检查通过后切换版本。

新闻日期使用事件日期。2026 年全球前 2% 顶尖科学家年度科学影响力榜单于 10 月 7 日发布，附件保留了上传的 PDF 原件。
