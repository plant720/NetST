# 单倍型网络分析工具 / Haplotype Network Analysis Tool

基于PyQt6的单倍型网络分析工具，从VB.NET版本重构而来。

A PyQt6-based haplotype network analysis tool, refactored from the VB.NET version.

## 项目结构 / Project Structure

```
haplotype-tool-python-refactored/
├── main_form.py              # 主窗口业务逻辑 / Main window business logic
├── requirements.txt          # Python依赖 / Python dependencies
├── README.md                 # 项目说明 / Project documentation
│
├── ui/                       # UI组件模块 / UI components module
│   ├── __init__.py          # 模块初始化 / Module initialization
│   ├── main_window_ui.py    # 主窗口UI基类 / Main window UI base class
│   ├── menu_bar.py          # 菜单栏构建器 / Menu bar builder
│   ├── tool_bar.py          # 工具栏构建器 / Toolbar builder
│   ├── status_bar.py        # 状态栏组件 / Status bar widget
│   ├── data_tab_widget.py   # 数据标签页组件 / Data tab widget
│   └── log_tab_widget.py    # 日志标签页组件 / Log tab widget
│
├── model/                    # 数据模型模块 / Data models module
│   ├── __init__.py
│   ├── taxon_data.py        # Taxon数据类 / Taxon data class
│   └── taxon_table_model.py # 表格模型 / Table model
│
└── service/                  # 服务层模块 / Service layer module
    ├── __init__.py
    ├── file_service.py      # 文件服务 / File service
    └── analysis_service.py  # 分析服务 / Analysis service
```

## 架构设计 / Architecture Design

本项目采用清晰的分层架构，将UI设计与业务逻辑分离：

The project adopts a clear layered architecture, separating UI design from business logic:

```
┌─────────────────────────────────────────────────────────────┐
│                     MainForm (main_form.py)                  │
│  - 业务逻辑实现 / Business logic implementation              │
│  - 菜单/工具栏回调 / Menu/toolbar callbacks                  │
│  - 数据处理 / Data processing                               │
└─────────────────────────────────────────────────────────────┘
                              │ 继承 / Inherits
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MainWindowUI (ui/main_window_ui.py)       │
│  - UI布局定义 / UI layout definition                         │
│  - 组件初始化 / Component initialization                     │
└─────────────────────────────────────────────────────────────┘
                              │ 使用 / Uses
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              UI Components (ui/*.py)                         │
│  MenuBarBuilder | ToolBarBuilder | StatusBarWidget           │
│  DataTabWidget  | LogTabWidget                               │
└─────────────────────────────────────────────────────────────┘
```

### UI层 / UI Layer (`ui/`)

负责所有界面组件的创建和布局，不包含任何业务逻辑。

Responsible for creating and laying out all UI components, without any business logic.

| 组件 / Component | 描述 / Description |
|------------------|---------------------|
| `MainWindowUI` | 主窗口UI基类，定义窗口布局和组件 |
| `MenuBarBuilder` | 菜单栏构建器，参考VB.NET原始设计 |
| `ToolBarBuilder` | 工具栏构建器 |
| `StatusBarWidget` | 状态栏组件（进度条+状态文本） |
| `DataTabWidget` | 数据表格标签页（表格视图+工具栏） |
| `LogTabWidget` | 日志标签页（日志显示+辅助信息面板） |

### 业务逻辑层 / Business Logic Layer (`main_form.py`)

继承UI基类，实现所有业务功能：

Inherits from UI base class, implements all business functions:

- 文件操作（载入/保存FASTA、CSV）/ File operations
- 数据编辑（全选/取消选择）/ Data editing
- 网络分析（TCS/MJN/MSN）/ Network analysis
- 序列比对（MAFFT/MUSCLE）/ Sequence alignment
- 其他分析功能 / Other analysis functions

### 数据模型层 / Model Layer (`model/`)

| 类 / Class | 描述 / Description |
|------------|---------------------|
| `TaxonData` | 单个序列/分类单元的数据类 |
| `TaxonTableModel` | Qt表格模型，用于数据显示和编辑 |

### 服务层 / Service Layer (`service/`)

| 服务 / Service | 描述 / Description |
|----------------|---------------------|
| `FileService` | 文件读写服务（FASTA/CSV） |
| `AnalysisService` | 分析功能服务（网络构建等） |

## 菜单设计 / Menu Design

菜单设计参考VB.NET原始版本：

### 文件菜单 / File Menu (文件(&F))
| 菜单项 / Menu Item | 快捷键 / Shortcut | 功能 / Function |
|--------------------|-------------------|------------------|
| 载入序列 | Ctrl+O | 从FASTA文件载入序列 |
| 载入表格 | Ctrl+Shift+O | 从CSV文件载入数据 |
| 增加序列 | - | 添加更多序列数据 |
| 导出表格 | Ctrl+S | 保存数据到CSV |
| 导出序列 | - | 导出为FASTA格式 |
| 退出 | Ctrl+Q | 退出程序 |

### 编辑菜单 / Edit Menu (编辑(&E))
| 菜单项 / Menu Item | 快捷键 / Shortcut | 功能 / Function |
|--------------------|-------------------|------------------|
| 全选 | Ctrl+A | 选择所有序列 |
| 清除选择 | - | 取消所有选择 |

### 分析菜单 / Analysis Menu (分析(&A))
| 菜单项 / Menu Item | 功能 / Function |
|--------------------|------------------|
| MSN单倍型网络 | 构建最小生成网络 |
| MJN单倍型网络 | 构建中间连接网络 |
| TCS单倍型网络 | 构建TCS网络 |
| 序列比对-MAFFT | MAFFT序列比对子菜单 |
| 序列比对-MUSCLE | MUSCLE序列比对子菜单 |
| 网络图可视化 | 可视化网络图 |
| 拓扑结构分析 | 分析网络拓扑 |
| 社区检测 | 社区检测分析子菜单 |
| 序列分析 | 序列统计分析 |
| 群体信息统计 | 群体遗传多样性分析 |
| 性状关联分析 | 单倍型-性状关联分析 |

### 浏览菜单 / View Menu (浏览(&V))
| 菜单项 / Menu Item | 快捷键 / Shortcut | 功能 / Function |
|--------------------|-------------------|------------------|
| 前进 | Alt+Right | 浏览器前进 |
| 后退 | Alt+Left | 浏览器后退 |
| 分析记录 | - | 查看历史分析记录 |

### 工具菜单 / Tools Menu (工具(&T))
| 菜单项 / Menu Item | 功能 / Function |
|--------------------|------------------|
| 清理序列 | 清理无效字符 |
| 获取序列信息 | 显示序列详细信息 |
| 日期转换数字 | 日期格式转数值 |
| 语言 | 语言切换（中文/English） |

### 帮助菜单 / Help Menu (帮助(&H))
| 菜单项 / Menu Item | 快捷键 / Shortcut | 功能 / Function |
|--------------------|-------------------|------------------|
| 关于 | - | 显示关于信息 |
| 帮助文档 | F1 | 显示帮助文档 |

## 安装和运行 / Installation and Running

### 安装依赖 / Install Dependencies

```bash
pip install -r requirements.txt
```

### 运行程序 / Run Application

```bash
python main_form.py
```

## 代码注释规范 / Code Comment Standards

本项目采用双语注释（中文/英文），便于不同语言背景的开发者理解：

This project uses bilingual comments (Chinese/English) for developers with different language backgrounds:

```python
def _load_sequence(self):
    """
    从FASTA文件载入序列数据
    Load sequence data from FASTA file
    """
    # 获取分隔符
    # Get delimiter
    delimiter, ok = QInputDialog.getText(...)
```

## 扩展开发 / Extension Development

### 添加新的菜单项 / Adding New Menu Items

1. 在 `ui/menu_bar.py` 的相应位置添加菜单项定义
2. 在 `main_form.py` 的 `_get_callbacks()` 方法中添加回调函数映射
3. 在 `main_form.py` 中实现回调函数

### 添加新的UI组件 / Adding New UI Components

1. 在 `ui/` 目录下创建新的组件文件
2. 在 `ui/__init__.py` 中导出新组件
3. 在 `MainWindowUI` 或 `MainForm` 中使用新组件

## 版本历史 / Version History

- **v2.0.0** - PyQt6重构版本，UI与业务逻辑分离
- **v1.0.0** - VB.NET原始版本Python移植

## 许可证 / License

MIT License
