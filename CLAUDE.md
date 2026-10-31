# Python 与 AI 开发教程

公开的中文教程网站，线上地址 <https://pythonzh.pages.dev/>，目标是教有 Java、Kotlin 或 Android 经验的开发者做 AI Agent 应用。使用方法和内容语法见 `README.md`。

## 常用命令

```bash
python3 build.py                         # 生成网站，构建只能依赖标准库
.venv/bin/python tools/verify.py         # 运行全部示例
.venv/bin/python tools/verify.py python  # 只运行 Python 示例
.venv/bin/python tools/check_jvm.py       # 编译 no-run 的 Java 和 Kotlin 示例
```

## 内容范围

大类在 `categories.json` 里注册：Python 语言、Python 服务端、大模型基础、Agent 开发、评测与安全。章节按学习顺序编号，没有章节的大类不显示。

## 来源规则

- 网站公开且接入了 Google 搜索。章节用自己的话写，附来源链接，不整段搬运。
- 不放付费课程的内容。
- 各来源的许可不同，写章节前核实来源网址、许可和文档版本。
- 不放个人项目的设计笔记、面试准备、招聘数据和雇主信息，也不提交这类资料到仓库。

## 章节写法

- 精简优先：先讲最常用的写法，不常用的知识放进 `:::more` 或略过。
- 每节穿插 Java、Kotlin 对照。服务端章节的 Java 用 Spring Boot，Kotlin 用 Android 或服务端写法，大模型和 Agent 章节用 OpenAI Java SDK 和 LangChain4j。确实没有对应写法时才省略。
- `seo_title` 不带站名，宽度控制在 30 个汉字以内。引用其他章节时写「章节名」，构建会自动加上链接。
- 对照只是写法相似时要写明差别。比如 Retrofit 是客户端，FastAPI 是服务端。
- 第三方库更新快，这类章节用 `versions` 写明依据的版本，并和 `tools/requirements.txt` 保持一致。
- 示例都要通过 `tools/verify.py`，只有校验环境里跑不了的代码才标 `no-run`。调用大模型的示例用 `tools/fakellm.py` 的假服务运行，不写死具体模型名。
- 标了 `no-run` 的 Java 和 Kotlin 代码用 `tools/check_jvm.py` 对照真实依赖编译。代码片段缺的声明写成 `§` 隐藏行。

## 发布规则

- 推送到 `main` 会自动部署到线上，推送前先征得用户同意。
- 已上线章节的 `id` 就是网址，不能改。
- 不能删除 `build.py` 里的 `GOOGLE_VERIFICATION`，否则会失去 Search Console 的所有权。
- 换域名要重做 Cloudflare 和 Google 的配置，默认保留 `pythonzh.pages.dev`。
