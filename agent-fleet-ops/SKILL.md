---
name: agent-fleet-ops
description: 三端 Agent 舰队运维——连接本机 Claude Code / Codex / ZCode,搭建统一知识库中枢(~/ai-kb)与自动化脚本(ai-doctor 体检、sync-skills 四端同步发布),接线 CLAUDE.md/AGENTS.md 共享上下文。当用户要求"连接各个AI工具"、"搭建自动化体系"、"优化知识库"、"技能同步"、"agent 体检"时使用。
---

# Agent 舰队运维

把一台机器上的多个 agent CLI 变成共享知识、共享技能、可体检、可一键发布的一个舰队。

## 架构原则

1. **单一事实来源**:自定义技能只在一个 git 仓库维护(如 GitHub 上的 skills 仓库),其余目录全部是部署副本
2. **知识同源**:各 agent 的知识文件(CLAUDE.md / AGENTS.md)指向同一套注册表、记忆库、中枢文档,而不是各写一份
3. **部署副本可丢弃**:任何 skills 目录损坏,从源头重刷即可——所以脚本敢用 `rm -rf` 重建副本

## 执行流程

### Phase 1 — 盘点(先摸清再动手)

```bash
command -v claude/codex/gh/zcode && 各自 --version
gh auth status                      # GitHub 登录态
ls ~/.claude/skills ~/.agents/skills ~/.zcode/skills ~/.codex/skills 2>/dev/null | 统计计数
cat ~/.claude/CLAUDE.md ~/.codex/AGENTS.md   # 现有知识文件,后续接线要保留其内容
```

产出:agent 矩阵表(端/版本/知识文件/模型路由)。

### Phase 2 — 建中枢 `~/ai-kb/`

```
~/ai-kb/
├── KNOWLEDGE.md     # 矩阵表 + 知识地图(谁存什么)+ 脚本用法 + 待办缺口
└── bin/
    ├── ai-doctor    # 全链路体检(见 resources/ai-doctor)
    └── sync-skills  # 技能同步发布(见 resources/sync-skills)
```

从本 skill 的 `resources/` 复制两个脚本,按目标机器改 `SKILLS_SRC`(技能源仓库路径)。`git init` 提交。

### Phase 3 — 接线共享上下文

- **Codex**(`~/.codex/AGENTS.md`):保留原有内容(如 CodeGraph 段),追加:行为底线引用、技能注册表路径、经验记忆路径、中枢文档路径、两个脚本用法
- **Claude**(`~/.claude/CLAUDE.md`):只追加一小节「跨端中枢」指向 `~/ai-kb/KNOWLEDGE.md`,不动其余内容
- 原则是**追加不重写**——这些文件可能被用户的其他系统(Operating System/hooks)管理

### Phase 4 — 技能四端同步

- 把技能源仓库里每个含 `SKILL.md` 的文件夹,刷到 `~/.claude/skills`、`~/.agents/skills`、`~/.zcode/skills`、`~/.codex/skills`
- 差异分析先行:`comm` 对比目录列表,补缺不删多——**尊重各端的精选策略**(有的端故意只放子集,别强灌全量)
- Codex 的 skills 目录通常为空,只放自定义核心技能

### Phase 5 — 体检验证(必须全绿才算完)

```bash
bash ~/ai-kb/bin/ai-doctor        # CLI/GitHub/模型路由/技能/知识文件/代理 全检查
bash ~/ai-kb/bin/sync-skills "init"  # 空跑验证 no-op 路径
```

## 质量门

- ai-doctor 输出中,除"用户待提供"项(如 API key)外必须全 ✓
- 接线后的 CLAUDE.md / AGENTS.md 原有内容一字不丢
- sync-skills 空跑必须输出"无改动,跳过"

## 注意事项

- 技能目录三份冗余可用 Windows junction 合并(`mklink /J`),但涉及多端写入冲突,**必须用户确认后执行**
- 含个人环境信息的中枢仓库推 GitHub 用**私有仓库**
- 凭据永不写入技能仓库;OAuth/加密 token 无法跨端复用时,如实告知用户需要新 key
