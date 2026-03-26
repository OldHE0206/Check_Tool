# _*_ coding:utf-8 _*_
__author__ = 'Old_He'
################################################################################
# 这是一个Maya场景检查工具，能帮助创作者更方便的发现场景中的问题。
# 包含7大功能模块：场景大纲、模型拓补、模型UV、材质、灯光渲染、骨骼绑定和动画。
################################################################################

import os
import pymel.core as pm

class MayaCheckTool:
    def __init__(self):  # 初始化函数
        self.toolShelf = 'Tool'
        self.checkTool = 'Maya Check Tool'
        self.mayaCheckTool = 'Maya_Check_Tool'
        self.ConflictWarningWindow = 'Conflict warning window'
        self.windowText = '冲突警告'
        self.tool_rack()  # 创建工具架函数

    def warning_of_cnflict(self):  # 创建冲突警告弹窗
        self.window = pm.window(self.ConflictWarningWindow, title=self.windowText, widthHeight=(250, 30))
        # 创建一个窗口
        with pm.columnLayout():
            pm.iconTextButton(style='textOnly', label='工具架按钮命名冲突，请删除后重试！')
            # 创建一个窗口，只显示文字，文字为"工具架按钮命名冲突，请删除后重试！"
        self.window.show()  # 显示窗口

    def tool_rack(self):  # 创建工具架
        self.shelfNames = pm.shelfTabLayout('ShelfLayout', q=True, tl=True)  # 获取Maya所有工具架的名称
        if not self.toolShelf in self.shelfNames:  # 如果没有'Tool'
            pm.shelfLayout(self.toolShelf, p='ShelfLayout')  # 新建一个"Tool"选项卡
            self.tool_shelf_button()  # 创建子工具按钮
        else:
            self.toolHolderButton = pm.shelfLayout(self.toolShelf, q=True, ca=True)  # 获取选项卡所有子按钮
            if self.toolHolderButton is None:  # 如果子按钮等于None
                self.tool_shelf_button()  # 创建子按钮
            else:  # 否则
                if not self.mayaCheckTool in self.toolHolderButton:  # 如果没有叫'Maya_Check_Tool'的子按钮
                    self.tool_shelf_button()  # 创建子工具按钮
                else:  # 否则
                    self.warning_of_cnflict()  # 创建冲突警告窗口

    def tool_shelf_button(self):  # 创建子工具按钮
        mayaPath = os.environ.get('MAYA_LOCATION')  # 获取maya安装路径
        
        # 使用os.path.join构建跨平台路径
        icon_dir = os.path.join(mayaPath, 'bin', 'plug-ins', 'Old_He_Check_Tool')
        iconPath = os.path.join(icon_dir, 'Maya_Check_Tool.png')
        
        # 工具命令 - 使用正确的字符串格式化
        command = f"""
# _*_ coding:utf-8 _*_
import sys
import os

# 添加工具路径到系统路径
tool_dir = r"{icon_dir}"
if tool_dir not in sys.path:
    sys.path.append(tool_dir)

try:
    # 尝试导入检查工具模块
    # 注意：这里需要确保实际模块文件名正确
    try:
        from Maya_Check_Tool_V_251009_OldHe import ModelCheckerUI
        module_name = "Maya_Check_Tool_V_251009_OldHe"
    except ImportError:
        # 如果上面的导入失败，尝试其他可能的模块名
        try:
            from Maya_Check_Tool import ModelCheckerUI
            module_name = "Maya_Check_Tool"
        except ImportError:
            # 列出目录中的所有文件来帮助调试
            files = os.listdir(tool_dir) if os.path.exists(tool_dir) else []
            python_files = [f for f in files if f.endswith('.py')]
            raise ImportError(f"无法找到检查工具模块。目录中的Python文件: {{python_files}}")
    
    # 声明全局变量
    global model_checker_ui
    
    # 检查是否已经存在实例，如果存在则删除
    if 'model_checker_ui' in globals():
        try:
            model_checker_ui.close()
            model_checker_ui.deleteLater()
            # 设置为None以释放引用
            model_checker_ui = None
        except:
            pass
    
    # 创建新的UI实例
    model_checker_ui = ModelCheckerUI()
    model_checker_ui.show()
    
except Exception as e:
    import traceback
    error_msg = "加载Maya检查工具时出错:\\n{{}}\\n{{}}".format(str(e), traceback.format_exc())
    print(error_msg)
    from maya import cmds
    cmds.confirmDialog(title="错误", message=error_msg, button=["确定"])
"""
        
        # 检查图标文件是否存在，如果不存在使用默认图标
        if not os.path.exists(iconPath):
            print(f"警告: 图标文件不存在: {iconPath}")
            # 使用None让Maya使用默认图标
            iconPath = None
        
        pm.shelfButton(  # 创建一个工具架按钮
            self.checkTool,
            p=self.toolShelf,
            i=iconPath,
            l='Maya检查工具',
            command=command
        )

# 创建工具实例
try:
    MayaCheckTool()
    print("Maya检查工具安装完成")
except Exception as e:
    print(f"安装Maya检查工具时出错: {e}")
