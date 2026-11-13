---
name: ai-tech-radar
description: AI 技术雷达——当需要了解本机 AI 技术资产、近月 GitHub AI 生态与大模型动态、查找某个赛道的最新项目/技术/学习方法，或要更新技术快照时使用。触发词包括：AI技术雷达、技术快照、最新AI技术、最近两个月AI圈有什么、ai-tech-radar、技术扫描。
---

# AI 技术雷达（ai-tech-radar）

一份**可持续滚动更新**的 AI 技术知识库，按 `KNOWLEDGE-MANIFEST.md` 的协议运行。目标是让任何模型（包括未来更新的模型）都能"分析 → 学会 → 更新"。

## 知识库位置

`C:\Users\14676\.zcode\workspace\draft-75355aed-1fca-4b9c-8a78-748750eb11b8\ai-tech-snapshot-2026-09_11\`

## 使用流程（严格按顺序）

1. **先读** `KNOWLEDGE-MANIFEST.md`（消费/核查/更新三协议）
2. **再读** `tech-index.json`（机器可读主索引；`techniques[].learn` 直接指向学习位置）
3. 按需读 01-07 号文件；**问答式查询**用 `cd <workspace>/rag-lab && python -I raglab.py ask "问题"`
4. 对存疑数据执行核查协议（重放 gh api 命令），**不要用训练记忆覆盖库内数据**

## 常用任务

- **查某个赛道最近有什么**：index 的 `window_new_repos` 按 `cat` 过滤
- **学某项技术**：index 的 `techniques` → `learn` 字段定位到 05/06/07 号文件对应章节
- **继续学习计划**：`gaps_and_learning` 查进度，W3=视频对齐（07§A1 有完整嫁接方案）、W4=记忆升级
- **滚动更新**：`bash <快照目录>/_raw/update-scan.sh <开始日> <结束日>`，然后按 manifest §3 归档

## 硬性约束

- 本机内存常驻仅剩约 2GB、GPU 8GB(Ada)——大模型放显存、keep_alive 短驻留、禁常驻服务、禁 Docker
- 知识入库走 manifest 协议；`~/ai-kb` 的 SQLite 不要直写
- 每次更新后：index `version+1` → manifest changelog 追加一行
