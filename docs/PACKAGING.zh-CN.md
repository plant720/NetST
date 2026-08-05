# NetST 跨平台打包指南

NetST 使用 PyInstaller 生成原生发布包。PyInstaller 不是跨平台编译器：macOS 包必须在 Apple Silicon macOS 上构建，Windows 包必须在 64 位 x86-64 Windows 上构建。

## 1. 构建原则

- 使用独立的 Python 3.10、3.11 或 3.12 虚拟环境，不复用日常开发环境。
- 安装 `requirements-build.txt`，不要手工挑选依赖。该文件固定了 PyQt6、QtWebEngine、chardet 和 PyInstaller 版本。
- 统一通过 `python scripts/build.py` 构建。脚本会检查平台、CPU、依赖、内置工具和 macOS 执行权限，调用 PyInstaller，并验证产物结构及资源。
- RMST、McAN、fastHaN、MAFFT 和 MUSCLE 均以目标平台二进制存放在 `lib/`；应用打包不会现场编译这些引擎。
- 自定义 PyInstaller hook 只保留 QtWebEngine 加载本地 tcsBU 页面所需的原生依赖，不复制未使用的完整 QML/Quick 3D 模块树。spec 移除 WebEngine 语言包、未加载的 Qt `.qm` 翻译、DevTools、图像格式、网络/TLS、定位、触摸、图标引擎和额外样式插件。应用图标只嵌入可执行文件/app bundle，不再作为运行时静态资源重复复制。
- Windows 推荐目录模式。NetST 内含 QtWebEngine 和约 70 MB 的 MAFFT 工具树，单文件模式每次启动都要解压，而且更容易被杀毒软件误报。

## 2. macOS Apple Silicon

```bash
cd /path/to/NetST-py
python3.11 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python scripts/build.py
```

输出为 `dist/NetST.app`。构建脚本会验证 QtWebEngine helper/resources、`static/`、`lib/mac_arm64/` 和代码签名结构。

本地测试或内部分发可以使用 PyInstaller 的 ad-hoc 签名。公开分发建议使用 Developer ID：

```bash
python scripts/build.py \
  --codesign-identity "Developer ID Application: Your Name (TEAMID)"

ditto -c -k --sequesterRsrc --keepParent dist/NetST.app NetST-macOS-arm64.zip
xcrun notarytool submit NetST-macOS-arm64.zip \
  --keychain-profile NETST_NOTARY --wait
xcrun stapler staple dist/NetST.app
ditto -c -k --sequesterRsrc --keepParent dist/NetST.app NetST-macOS-arm64.zip
```

`scripts/macos-entitlements.plist` 包含 QtWebEngine JIT 所需权限。公证凭据应保存在 macOS Keychain 或 CI secrets 中，不能提交到仓库。

## 3. Windows x86-64

在 64 位 Windows PowerShell 中执行：

```powershell
cd C:\path\to\NetST-py
py -3.11 -m venv .venv-build
.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python scripts\build.py
```

仓库中的 `lib\win\McAN.exe` 与 `lib\win\netst-rmst.exe` 已是静态运行库的 x86-64 构建，仅依赖 Windows 系统 DLL。升级原生引擎时，应在其独立源码项目中构建并验证，再替换 `lib\win` 或 `lib\mac_arm64` 中的对应文件。

推荐输出为 `dist\NetST\`，启动文件为 `dist\NetST\NetST.exe`。发布时必须打包整个目录：

```powershell
Compress-Archive -Path dist\NetST -DestinationPath NetST-Windows-x86_64.zip -Force
```

确实需要单文件时可以使用：

```powershell
python scripts\build.py --onefile
```

其输出为 `dist\NetST.exe`。单文件模式启动较慢，首次运行或升级后可能触发安全软件扫描。

如有代码签名证书，可在构建后签署主程序：

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /a dist\NetST\NetST.exe
```

## 4. 常用参数

```text
python scripts/build.py --version 2.0.0     指定应用版本
python scripts/build.py --onefile           Windows 可选单文件模式
python scripts/build.py --codesign-identity macOS Developer ID 签名
```

不要直接用系统中任意一个 `pyinstaller` 命令。使用 `python -m PyInstaller`（构建脚本已这样做）可确保 PyInstaller 与当前虚拟环境一致。

## 5. 故障定位

- `Packaging environment is incomplete`：当前 Python 环境缺依赖。执行该环境的 `python -m pip install -r requirements-build.txt`。
- `No module named chardet`：旧构建环境漏装运行依赖。重新安装完整构建依赖并执行干净构建。
- QtWebEngine 启动失败：确认 PyQt6 与 PyQt6-WebEngine 次版本一致；当前 spec 使用 PyInstaller 官方 hooks，并在构建后检查 `QtWebEngineProcess`、`.pak` 资源和语言包。
- macOS 包在其他机器被拦截：这是签名/公证问题；使用 Developer ID 构建并完成 notarization，而不是关闭 Gatekeeper。
- Windows 包启动后找不到 MAFFT/McAN：确认发布的是整个 `dist\NetST\` 目录，或改用 `--onefile`；不要只复制目录模式中的 `NetST.exe`。

每次升级 PyQt6、PyQt6-WebEngine 或 PyInstaller 后，都应在两种目标系统上重新执行完整构建和真实数据流程测试。
