# Interview Assets

把三阶段流程的静态资源统一放在 `app/static/interview-assets/` 下。

这样做的原因：
- 该目录已经由 FastAPI 通过 `/static/...` 暴露，前端可以直接访问。
- movie / reading / interview 的资源结构统一，便于后续前端按阶段加载。

推荐结构：

```text
app/static/interview-assets/
├── movie/
│   ├── positive/
│   ├── neutral/
│   └── negative/
├── reading/
│   ├── positive/
│   ├── neutral/
│   └── negative/
└── interview/
    ├── 1.txt
    ├── 2.txt
    └── ...
```

示例：
- 电影素材可放在 `app/static/interview-assets/movie/positive/` 等目录
- 朗读文本可放在 `app/static/interview-assets/reading/positive/` 等目录
- 问答阶段题目文本可放在 `app/static/interview-assets/interview/` 下

后续前端可通过类似路径访问：
- `/static/interview-assets/movie/positive/<file>`
- `/static/interview-assets/reading/positive/<file>`
- `/static/interview-assets/interview/<file>`
