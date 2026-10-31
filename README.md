# Python 中文教程

写给有编程经验的开发者的 Python 教程。基于官方文档精简为 11 章，每个知识点都和熟悉的语言对比。

## 使用

```bash
python3 build.py                        # 生成网站
python3 -m http.server 4173 -d dist     # 本地预览，打开 http://localhost:4173
```

构建产物有两份：

- `dist/` 是完整网站，每章一个独立页面，部署时上传这个目录
- `preview/artifact.html` 是全站合并成的单文件，用于发布为 Claude Artifact，也可以双击打开

代码高亮来自 cdnjs 上的 highlight.js，由浏览器在加载后上色。离线时代码显示为无高亮的纯文本，正文不受影响。

## 目录

```text
content/          各章内容，Markdown 格式，章数不固定，按文件名排序
languages.json    对比语言注册表
build.py          解析内容，生成页面、sitemap、robots.txt 和 llms.txt，只依赖标准库
render.py         页面结构，所有 HTML 都在这里生成
src/              页面外壳、样式和交互，app.js 只负责交互
tools/verify.py   运行全部示例，核对 `=>` 注释里的结果
```

## 部署

网站部署在 Cloudflare Pages 上，地址是 <https://pythonzh.pages.dev/>。在 Cloudflare 控制台里连接 GitHub 仓库时这样填：

| 配置项 | 内容 |
| --- | --- |
| 项目名称 | `pythonzh`，也就是 `pages.dev` 前面的名字 |
| 构建命令 | `python3 build.py` |
| 构建输出目录 | `dist` |
| 环境变量 | `SITE_URL` = `https://pythonzh.pages.dev/` |

一定要设置 `SITE_URL`，否则不会生成 canonical、og:url 和 `sitemap.xml`。之后每次推送到 `main` 都会自动重新部署。

章节 `id` 不能用 `functions`，Cloudflare Pages 上传时会忽略这个目录，`build.py` 的 `RESERVED_PAGES` 会直接报错。

Google Search Console 的验证码在 `build.py` 的 `GOOGLE_VERIFICATION`，Google 会在首页检查这个标签。验证通过后也要保留，删掉会失去所有权。

## 添加一门对比语言

以 Go 为例，代码不用改。

1. 在 `languages.json` 里注册。`hljs` 是 highlight.js 的语言名，常见语言都已包含。

   ```json
   { "id": "go", "name": "Go", "hljs": "go", "color": "#007d9c", "colorOnDark": "#5dd3ee" }
   ```

2. 在 `content/*.md` 的对比块里加代码，并给异同表加一列。单元格写 `=` 表示和 Python 相同。

   ````markdown
   :::compare 程序入口
   ```python
   print("Hello")
   ```
   ```go
   fmt.Println("Hello")
   ```

   | 对比项 | python | go |
   | --- | --- | --- |
   | 程序入口 | 文件顶层语句直接执行 | `main` 函数 |
   | 语句结尾 | 不写分号 | = |

   > 要点: 这句总结显示在卡片底部。
   :::
   ````

3. 在对照表里加一列，列名就是语言 id。

   ```markdown
   :::map 容器类型
   | python | java | kotlin | go | note |
   | --- | --- | --- | --- | --- |
   | `list` | `ArrayList` | `MutableList` | `[]T` | |
   :::
   ```

4. 运行 `python3 build.py`。输出里能看到每门语言的覆盖率，比如 `go 代码 3/59 异同表 3/59`。

还没写到的地方，卡片里不会出现这门语言的选项，所以可以一章一章慢慢补。卡片右栏在不超过 4 门语言时用分段标签，超过时自动换成下拉选择。语言切换器、配色、搜索和速查表都会自动带上新语言。想让校验脚本也运行它，在 `tools/verify.py` 的 `RUNNERS` 里加一个函数。

## 内容语法

普通 Markdown 支持标题、段落、列表、代码块、行内代码、粗体和链接，另有下面这些容器。

| 语法 | 用途 |
| --- | --- |
| `:::compare 标题` | 对比卡片，放各语言代码块、异同表和 `> 要点: 总结` |
| `:::map 标题` | 对照表，列名用语言 id，`note` 列是说明 |
| `:::tip 标题` / `:::warn 标题` | 提示和警告 |
| `:::more 标题` | 默认折叠的选读内容，放不常用的知识点 |
| `:::recap` | 章末要点 |

小节标题必须带锚点，比如 `## 字典 {#dicts}`。

异同表的第一列是对比项，其余列名是语言 id。写 `=` 的单元格会和 Python 合并成一行并标记「相同」。页面上不同点排在前面，相同点排在后面。只和某门语言有关的说明写成 `> java: 说明`，选中这门语言时才显示。

代码块的几个约定：

- 以 `§ ` 开头的行不展示，只在校验时运行，用来放 import 或准备数据
- 紧跟一个 ` ```output ` 块可以展示输出，校验时要求完全一致
- `# => 值` 和 `// => 值` 表示运行结果，页面上显示为绿色，校验时会比对
- ` ```python no-run ` 跳过校验，用于需要第三方依赖的片段
- ` ```java:xml ` 表示放在 Java 一栏，按 XML 高亮

## 校验示例

```bash
python3.12 tools/verify.py                  # 校验全部语言
python3.12 tools/verify.py python           # 只校验 Python
```

Java 示例用了 record 和 switch 模式匹配，`PATH` 里的 `jshell` 要来自 JDK 21 或更高版本。

## 站名和搜索引擎信息

站名、首页标题、描述和关键词在 `build.py` 顶部。每章的搜索信息写在 Markdown 文件头部：

```text
id: control-flow            章节网址，上线后不要再改
title: 控制流               页面上显示的章节标题
seo_title: Python 控制流：if、for、range 和 match，对比 Java switch 与 Kotlin when
seo_description: 搜索结果里显示的摘要
```

`seo_title` 和 `seo_description` 只出现在浏览器标签和搜索结果里，改它们不会影响页面上看到的标题和正文。

## 内容来源

内容改写自 [Python 3.12 官方中文教程](https://docs.python.org/zh-cn/3.12/tutorial/index.html)，原文版权归 Python 软件基金会所有。
