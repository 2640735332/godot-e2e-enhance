# GodotE2E v1.1.0 — 现有能力评估报告

> 评估日期：2026-05-07
> 评估人：基于 Fork 后的代码库全面审查
> 原始项目：[RandallLiuXin/godot-e2e](https://github.com/RandallLiuXin/godot-e2e)
> License：Apache 2.0

---

## 一、总体评价

**评分：7.0 / 10**

GodotE2E 是目前 Godot 生态中唯一真正意义上的进程外 E2E 测试框架。其架构设计合理（TCP + JSON + 状态机），代码质量良好，但作为 v1.1.0 的早期项目，功能覆盖面有限，存在大量可增强的空间。**适合作为基础进行 Fork 和增强开发。**

---

## 二、架构概览

```
pytest (Python) ←→ TCP (localhost, length-prefixed JSON) ←→ AutomationServer (Godot Autoload)
```

### 两进程架构

| 层 | 组件 | 语言 | 文件 | 行数 | 职责 |
|----|------|------|------|------|------|
| **测试端** | GodotE2E | Python | `python/godot_e2e/commands.py` | 235 | 高级测试 API |
| **测试端** | GodotClient | Python | `python/godot_e2e/client.py` | 129 | TCP 客户端，带锁线程安全 |
| **测试端** | GodotLauncher | Python | `python/godot_e2e/launcher.py` | 205 | 进程启动、端口分配、token生成 |
| **测试端** | CLI | Python | `python/godot_e2e/cli.py` | 46 | pytest 包装器 |
| **测试端** | Fixtures | Python | `python/godot_e2e/fixtures.py` | 131 | pytest fixtures |
| **测试端** | Types | Python | `python/godot_e2e/types.py` | 177 | 类型系统 + 序列化 |
| **游戏端** | AutomationServer | GDScript | `addons/godot_e2e/automation_server.gd` | 447 | TCP 服务器 + 状态机 |
| **游戏端** | CommandHandler | GDScript | `addons/godot_e2e/command_handler.gd` | 489 | 命令执行器 |
| **游戏端** | JsonSerializer | GDScript | `addons/godot_e2e/json_serializer.gd` | 149 | 类型序列化 |
| **游戏端** | Config | GDScript | `addons/godot_e2e/config.gd` | 71 | 命令行参数解析 |
| **游戏端** | Plugin | GDScript | `addons/godot_e2e/plugin.gd` | 19 | 编辑器插件入口 |

**总代码量：~2,100 行**（非常精简）

---

## 三、已有能力清单

### 3.1 核心通信
- [x] TCP 长度前缀帧协议 (4字节 Big-Endian U32 header + UTF-8 JSON body)
- [x] Token 认证握手 (`hello` 命令必须第一个发送)
- [x] 单调递增命令 ID 用于请求/响应匹配
- [x] 连接断开自动重置，返回 LISTENING 状态
- [x] 本地回环绑定 (127.0.0.1)，安全隔离

### 3.2 状态机 (AutomationServer)
- [x] 5 状态：LISTENING → IDLE → EXECUTING/WAITING → DISCONNECTED
- [x] 7 种等待类型：PROCESS_FRAMES, PHYSICS_FRAMES, SECONDS, NODE_EXISTS, SIGNAL_EMITTED, PROPERTY_VALUE, SCENE_CHANGE
- [x] 超时机制（所有等待类型支持 wall-clock timeout）
- [x] 连接健康检测（每帧 poll 连接状态）

### 3.3 节点操作 (即时命令)
- [x] `node_exists` — 检查节点是否存在
- [x] `get_property` — 读取属性（支持点路径如 `position:x`）
- [x] `set_property` — 设置属性
- [x] `call_method` — 调用 GDScript 方法（`callv`）
- [x] `find_by_group` — 按组查找节点
- [x] `query_nodes` — 按名称模式/组查询节点
- [x] `get_tree` — 获取场景树快照（可配置深度）
- [x] `batch` — 批量执行多个即时命令（一次往返）

### 3.4 输入模拟 (延迟命令)
- [x] `input_key` — 键盘输入（支持 keycode 和 physical_keycode）
- [x] `input_action` — 命名动作输入（支持 strength 参数）
- [x] `input_mouse_button` — 鼠标按钮（位置、按钮索引、按下/释放）
- [x] `input_mouse_motion` — 鼠标移动（绝对位置 + 相对位移）
- [x] `click_node` — 点击节点（自动计算 Control/Node2D 屏幕位置）
- [x] 所有输入命令自动等待 2 个物理帧（确保输入被处理）
- [x] 高级辅助：`press_key`, `press_action`, `click`

### 3.5 帧同步
- [x] `wait_process_frames(N)` — 等待 N 个 `_process` 帧
- [x] `wait_physics_frames(N)` — 等待 N 个 `_physics_process` 帧
- [x] `wait_seconds(T)` — 等待 T 秒游戏时间（受 `Engine.time_scale` 影响）
- [x] `wait_for_node(path, timeout)` — 等待节点出现
- [x] `wait_for_signal(path, signal, timeout)` — 等待信号发射
- [x] `wait_for_property(path, prop, value, timeout)` — 等待属性等于期望值

### 3.6 场景管理
- [x] `get_scene` — 获取当前场景路径
- [x] `change_scene(path)` — 切换场景（异步，等待新场景加载完成）
- [x] `reload_scene` — 重新加载当前场景（异步）

### 3.7 截图与诊断
- [x] `screenshot(path?)` — 截取视口截图，返回 PNG 文件路径
- [x] 测试失败自动截图（pytest ScreenshotOnFailure 插件）
- [x] 超时时附带场景树 dump（`TimeoutError.scene_tree`）

### 3.8 类型序列化
- [x] `_t` 类型标签系统，双向序列化
- [x] 支持：Vector2/2i, Vector3/3i, Rect2/2i, Color, Transform2D, NodePath
- [x] 支持：PackedVector2Array, PackedFloat32Array, PackedInt32Array, PackedStringArray
- [x] 数组、字典递归序列化
- [x] 未知类型标记为 `_unknown` 并通过

### 3.9 进程管理
- [x] 自动查找 Godot 可执行文件 (GODOT_PATH env → PATH)
- [x] 随机 Token 生成 (`secrets.token_hex(16)`)
- [x] 动态端口分配 (`--e2e-port=0` + port file)
- [x] 多实例并行支持
- [x] 优雅关闭 (quit 命令 → terminate → kill)
- [x] 超时连接重试

### 3.10 pytest 集成
- [x] `game` fixture — 函数级别，场景重载策略（默认，最快）
- [x] `game_fresh` fixture — 函数级别，新进程策略（最强隔离）
- [x] Module-scoped `_game_instance` fixture — 进程复用
- [x] Session-scoped fixture 支持
- [x] 项目路径自动检测（marker → pytest.ini → 环境变量 → 目录扫描）
- [x] 失败自动截图插件

### 3.11 CI/CD
- [x] GitHub Actions CI (Linux + Windows)
- [x] Linux: Xvfb 无头运行
- [x] Windows: 直接运行
- [x] 测试产物上传 (test_output artifacts)
- [x] Code linting (py_compile + ruff)

### 3.12 文档与示例
- [x] README (EN + zh-CN)
- [x] ROADMAP (EN + zh-CN)
- [x] Architecture 文档
- [x] API Reference 文档
- [x] Getting Started 文档
- [x] Testing Patterns 文档
- [x] 3 个示例项目：minimal, platformer, ui_testing
- [x] 内部测试套件 42 个测试

---

## 四、缺陷与问题清单

### 4.1 功能性缺陷

| # | 严重程度 | 问题 | 影响 |
|---|---------|------|------|
| 1 | **中** | 仅支持同步 API，无法并行等待多个条件 | 复杂测试场景受限 |
| 2 | **中** | 测试必须使用绝对路径 (`/root/Main/Player`)，场景重构会破坏测试 | 维护成本高 |
| 3 | **中** | 缺少游戏端错误/日志捕获，`push_error` 等对测试不可见 | 测试可能通过但游戏报错 |
| 4 | **中** | 断言无自动重试机制，需手动 `wait_for_property` | 时序问题导致 flaky tests |
| 5 | **低** | 输入模拟仅支持键盘+鼠标+动作，不支持触摸、手柄、滚轮 | 移动端/主机游戏测试受限 |
| 6 | **低** | `click_node` 无遮挡检测 — 弹窗/覆盖层可能拦截点击而不报错 | 点击测试不可靠 |
| 7 | **低** | `batch` 不支持延迟命令 | 无法批量执行输入+查询 |

### 4.2 测试基础设施缺陷

| # | 严重程度 | 问题 | 影响 |
|---|---------|------|------|
| 8 | **中** | 无 FPS/帧时间/内存使用等性能指标收集 | 无法做性能回归测试 |
| 9 | **中** | 无截图对比功能（视觉回归测试） | UI 变更需人工检查 |
| 10 | **低** | 无多 Godot 实例编排能力 | 无法测试多人/网络游戏 |
| 11 | **低** | 无操作录制/回放功能 | 手动编写测试效率低 |

### 4.3 CI/DevOps 缺陷

| # | 严重程度 | 问题 | 影响 |
|---|---------|------|------|
| 12 | **中** | 无预构建 Docker 镜像 | CI 中每次需手动安装 Godot |
| 13 | **中** | 无 macOS CI runner | macOS 平台未覆盖 |
| 14 | **低** | 无 HTML 测试报告 | 报告可读性一般 |

### 4.4 技术债务

| # | 严重程度 | 问题 | 影响 |
|---|---------|------|------|
| 15 | **低** | `State.EXECUTING` 枚举定义但实际未使用（命令执行是瞬时的） | 代码可读性小问题 |
| 16 | **低** | Python 端 `GodotE2E.launch()` 返回 `self` 而非 context manager 实例 — 实际上 `__init__` 创建的实例和 `launch` 返回的实例有细微差别 | 使用时需要理解内部细节 |
| 17 | **低** | GDScript 端 `_cmd_wait_for_signal` 使用 `CONNECT_ONE_SHOT` + Callable，GDScript 4.x 的 Callable 在信号断开方面可能存在边界情况 | 潜在内存泄漏 |

---

## 五、缺失能力清单（改进机会）

### 5.1 高优先级（对标 Roadmap）
这些在原始项目的 ROADMAP.md 中已经规划，可以直接开始实现：

1. **Locator 查询系统** — 多策略节点定位（name, group, text, script, type），解耦测试与场景结构
2. **引擎日志捕获** — 捕获 `push_error`/`push_warning` 并在 pytest 报告中展示
3. **`expect()` 自动重试断言** — 链式断言 API，自动轮询直到条件满足
4. **Step API + 轻量级追踪** — 按步骤捕获截图、场景树快照、命令日志
5. **遮挡检测** — 利用 `Viewport.gui_get_hovered_control()` 检测点击是否被拦截

### 5.2 中优先级（增强框架能力）
6. **异步 API** — 提供 async/await 接口，支持并行等待
7. **pytest Fixture 图** — `scene_fixture`、`player_fixture` 等可组合 fixture
8. **Gamepad/触摸输入** — `InputEventJoypadButton`、`InputEventJoypadMotion`、`InputEventScreenTouch`
9. **性能指标收集** — FPS 监控、帧时间分布、内存使用追踪
10. **视觉回归测试** — 截图对比（SSIM/像素差异），渲染变更检测
11. **HTML 测试报告** — pytest-html 集成，含截图嵌入

### 5.3 低优先级（长期目标）
12. **模糊测试** — 随机输入序列自动化测试
13. **多人/网络测试** — 多 Godot 实例编排，网络同步验证
14. **录制回放** — 手动操作录制 + 自动回放
15. **Docker 镜像** — 预构建的 Godot + godot-e2e CI 镜像
16. **VSCode/IDE 扩展** — 测试资源管理器集成

---

## 六、兼容性评估

| 维度 | 现状 | 目标 |
|------|------|------|
| **Godot 版本** | 4.x (CI 测试 4.4) | 保持 4.x 兼容，跟进 4.5/4.6 |
| **Python 版本** | 3.9 – 3.13 | 维持 |
| **操作系统** | Linux ✅, Windows ✅, macOS ❓ | 补充 macOS 支持 |
| **渲染后端** | 任何 (视口无关) | 维持 |
| **导出构建** | 不支持 (需要 `--e2e` flag) | 不计划支持（安全考虑） |

---

## 七、代码质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构设计** | 8/10 | 清晰的二进程分离，状态机模式正确，延迟命令设计合理 |
| **代码可读性** | 8/10 | 命名清晰，函数短小，注释适量 |
| **错误处理** | 7/10 | 连接断开、超时、认证失败都有处理，但缺少重试机制 |
| **测试覆盖** | 7/10 | 42 个内部测试 + 13 个示例 E2E 测试 |
| **文档质量** | 9/10 | 双语文档，架构图，API 参考，快速开始指南齐全 |
| **安全性** | 8/10 | Token 认证、本地绑定、`--e2e` flag 生产禁用 |

---

## 八、总结：Fork 后的优先行动项

基于此评估，建议 Fork 后按以下优先级执行：

### 第一批（立即开始，1-2周）
1. Fork 到个人 GitHub 账号，重命名项目
2. 修复 README 和 pyproject.toml 中的项目引用
3. 搭建本地开发环境（Godot 4.4+ + Python 3.10+）
4. 运行现有测试套件，确认无回归

### 第二批（ROADMAP 已有规划，2-4周）
5. 实现 Locator 查询系统（ROADMAP #1）
6. 实现引擎日志捕获（ROADMAP #2）
7. 实现 `expect()` 自动重试断言（ROADMAP #3）

### 第三批（自主增强，4-8周）
8. 异步 API 支持
9. Gamepad/触摸输入模拟
10. 性能指标收集
11. 视觉回归测试
12. HTML 测试报告

### 长期（8周+）
13. Docker CI 镜像
14. 多人/网络测试支持
15. 录制回放
16. IDE 扩展
