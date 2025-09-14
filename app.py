"""
My first application
"""
import importlib.metadata
import sys
import json
import pickle
import sqlite3
import re
import os
import numpy as np
import itertools
import math
import ollama
import mistune
import chardet
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.patches import ConnectionStyle, Polygon
from matplotlib.collections import PatchCollection
from matplotlib import collections
try:
    from importlib import metadata as importlib_metadata
except ImportError:
    # Backwards compatibility - importlib.metadata was added in Python 3.8
    import importlib_metadata

from datetime import datetime
from PySide6.QtGui import QAction, QFont, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QComboBox, QAbstractItemView, QHBoxLayout, QLabel, QMainWindow, QApplication, QMenu, QSizePolicy, QTextBrowser, QTextEdit, QWidget, QToolBar, QFileDialog, QTableView, QVBoxLayout, QHBoxLayout, QWidget, QSlider, QGroupBox, QLabel, QWidgetAction, QPushButton, QSizePolicy, QStackedWidget
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QVariantAnimation, Qt, QTranslator, QLocale, QLibraryInfo

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from PySide6.QtGui import QGuiApplication

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex

from scipy.stats import gmean

plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 'truetype'

# 获取当前文件的绝对路径
current_file_path = os.path.abspath(__file__)

# 获取当前文件的目录
current_directory = os.path.dirname(current_file_path)
working_directory = os.path.dirname(current_file_path)
# 改变当前工作目录
os.chdir(current_directory)


class AgeSelector(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        layout = QVBoxLayout()

        # 创建标签显示当前年龄
        self.age_label = QLabel(f"年龄: 3 岁", self)
        self.age_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.age_label)

        # 创建滑动条
        self.age_slider = QSlider(Qt.Horizontal, self)
        self.age_slider.setMinimum(3)
        self.age_slider.setMaximum(80)
        self.age_slider.setValue(3)
        self.age_slider.valueChanged.connect(self.update_age_label)
        layout.addWidget(self.age_slider)

        self.setLayout(layout)

    def update_age_label(self, value):
        self.age_label.setText(f"年龄: {value} 岁")
        self.main_window.update_age_info(value)


class ChatLocalAndPersistent(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1024, 600)  # 设置窗口尺寸为1024*600

        self.qm_files = []
        # 筛选出.qm文件
        self.output_text_list = []
        self.show_text = ''
        self.messages = []

        self.init_ui()
        self.setLanguage()
        self.show()

    def init_ui(self):
        self.main_frame = QWidget()
        self.toolbar = QToolBar()
        # 设置工具栏的文本大小
        self.toolbar.setStyleSheet("font-size: 18px")
        self.addToolBar(self.toolbar)
        self.translator = QTranslator(self)

        self.new_action = QAction('New Chat', self)
        self.open_action = QAction('Open Chat', self)
        self.save_action = QAction('Save Chat', self)
        self.export_action = QAction('Export Markdown', self)
        self.input_text_edit = QTextEdit()
        self.hidden_text_edit = QTextEdit()  # 隐藏的文本框
        self.hidden_text_edit.setVisible(False)  # 设置为不可见
        self.output_text_edit = QTextEdit()
        self.text_browser = QTextBrowser()
        self.send_button = QPushButton("Send\nCtrl+Enter")
        # self.role_label = QLabel("Role", self)
        # self.role_selector = QComboBox(self)
        self.model_label = QLabel("Model", self)
        self.model_selector = QComboBox(self)
        self.level_label = QLabel("Level",self)
        self.level_selector = QComboBox(self)

        self.toolbar.addAction(self.new_action)
        self.toolbar.addAction(self.open_action)
        self.toolbar.addAction(self.save_action)
        self.toolbar.addAction(self.export_action)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.model_label)
        self.toolbar.addWidget(self.model_selector)
        self.toolbar.addSeparator()
        # self.toolbar.addWidget(self.role_label)
        # self.toolbar.addWidget(self.role_selector)
        # self.toolbar.addSeparator()
        self.toolbar.addWidget(self.level_label)
        self.toolbar.addWidget(self.level_selector)
        self.toolbar.addSeparator()

        # 在工具栏中添加一个New action
        self.new_action.setShortcut('Ctrl+N')  # 设置快捷键为Ctrl+N
        self.new_action.triggered.connect(self.newChat)

        # 在工具栏中添加一个Open action
        self.open_action.setShortcut('Ctrl+O')  # 设置快捷键为Ctrl+O
        self.open_action.triggered.connect(self.openChat)

        # 在工具栏中添加一个Save action
        self.save_action.setShortcut('Ctrl+S')  # 设置快捷键为Ctrl+S
        self.save_action.triggered.connect(self.saveChat)

        # 在工具栏中添加一个Export action
        self.export_action.setShortcut('Ctrl+E')  # 设置快捷键为Ctrl+E
        self.export_action.triggered.connect(self.exportMarkdown)

        # roles = ['user', 'system', 'assistant']
        # self.role_selector.addItems(roles)

        data = ollama.list()
        if 'models' in data:
            names = [model.get('name', 'Unknown') for model in data['models']]
            self.model_selector.addItems(names)



        level = ['Primary School','Middle School','CET4','CET6','PETS3','PETS5','TEM4','TEM8','PTE','TOEFL','IELTS']
        self.level_selector.addItems(level)



        # 创建一个水平布局并添加表格视图和画布
        self.base_layout = QVBoxLayout()
        self.lower_layout = QHBoxLayout()
        self.upper_layout = QHBoxLayout()

        # 创建一个新的字体对象
        font = QFont()
        font.setPointSize(12)
        # 设置字体
        self.input_text_edit.setFont(font)
        self.output_text_edit.setFont(font)
        self.text_browser.setFont(font)

        # 创建一个QPushButton实例
        self.send_button.setShortcut('Ctrl+Return')
        self.send_button.clicked.connect(self.sendMessage)
        # 设置按钮的文本大小
        self.send_button.setStyleSheet("font-size: 14px")

        # 将文本编辑器和按钮添加到布局中
        self.upper_layout.addWidget(self.text_browser)

        self.input_text_edit.setFixedHeight(100)  # 设置文本编辑框的高度为100
        self.send_button.setFixedHeight(100)  # 设置按钮的高度为50
        self.lower_layout.addWidget(self.input_text_edit)
        self.lower_layout.addWidget(self.send_button)

        self.base_layout.addLayout(self.upper_layout)
        self.base_layout.addLayout(self.lower_layout)
        self.base_layout.addWidget(self.hidden_text_edit)  # 添加隐藏的文本框

        # 添加年龄选择器
        self.age_selector = AgeSelector(self)
        self.age_selector.setGeometry(800, 20, 200, 100)  # 设置位置和大小
        self.base_layout.addWidget(self.age_selector)

        # 添加考试按钮
        self.start_exam_button = QPushButton("开始考试", self)
        self.start_exam_button.clicked.connect(self.start_exam)
        self.toolbar.addWidget(self.start_exam_button)

        # 使用 QStackedWidget 管理多个页面
        self.stacked_widget = QStackedWidget()
        self.main_page = QWidget()
        self.main_page.setLayout(self.base_layout)
        self.stacked_widget.addWidget(self.main_page)

        # 设置中心部件为 QStackedWidget
        self.setCentralWidget(self.stacked_widget)

    def setLanguage(self):
        # 加载.qm文件
        qm_files = [f for f in os.listdir(working_directory) if f.endswith('.qm')]
        if qm_files:
            for qm_file in qm_files:
                self.translator.load(qm_file, working_directory)
                QGuiApplication.installTranslator(self.translator)

        # 设置界面文本
        self.setWindowTitle(QApplication.translate('Context', 'Adapt: Chat Local And Persistent. Based on Ollama, a Graphical User Interface for Local Large Language Model Conversations'))
        self.new_action.setText(QApplication.translate('Context', 'New Chat'))
        self.open_action.setText(QApplication.translate('Context', 'Open Chat'))
        self.save_action.setText(QApplication.translate('Context', 'Save Chat'))
        self.export_action.setText(QApplication.translate('Context', 'Export Markdown'))
        self.model_label.setText(QApplication.translate('Context', 'Model'))
        # self.role_label.setText(QApplication.translate('Context', 'Role'))
        self.send_button.setText(QApplication.translate('Context', 'Send') + '\nCtrl+Enter')
        self.start_exam_button.setText(QApplication.translate('Context', 'Start Exam'))

    def resizeEvent(self, event):
        # 获取窗口的新大小
        new_width = event.size().width()
        new_height = event.size().height()
        # 调用父类的resizeEvent方法，以确保其他部件也能正确地调整大小
        super().resizeEvent(event)

    def sendMessage(self):
        # 获取输入框的文本
        user_input_text = self.input_text_edit.toPlainText()
        age_info_text = self.hidden_text_edit.toPlainText()

        if not user_input_text.strip() and not age_info_text.strip():
            return  # 如果输入为空，则不发送消息

        # 调用Ollama的接口，获取回复文本
        model = self.model_selector.currentText()
        # role = self.role_selector.currentText()
        level = self.level_selector.currentText()

        # 将用户输入和年龄信息合并

        user_input_text = '英语难度为'+ level + 'now you must use totally English to answer all the problems below.' + user_input_text

        combined_input = f"{user_input_text}\n\n{age_info_text}"

        self.messages.append({
            'role': 'user',
            'content': combined_input,
        })

        response = ollama.chat(model=model, messages=self.messages)
        self.messages.append({
            'role': 'assistant',
            'content': response['message']['content'],
        })

        output_text = response['message']['content']

        # 获取当前的日期和时间
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')

        self.show_text += (
            f"`model`: {model}\n\n"
            # f"`role`: {role}\n\n"
            f"`input_text`: \n{combined_input}\n\n"
            f"`output_text`: \n{output_text}\n\n"
            f"`timestamp`: {timestamp}\n\n"
        )

        html = mistune.markdown(self.show_text)
        self.text_browser.setHtml(html)

        self.output_text_list.append(
            f"`model`: {model}\n\n"
            # f"`role`: {role}\n\n"
            f"`input_text`: \n{combined_input}\n\n"
            f"`output_text`: \n{output_text}\n\n"
            f"`timestamp`: {timestamp}\n\n"
        )

        # 清空输入框
        self.input_text_edit.clear()

    def newChat(self):
        # 新建对话
        self.output_text_list = []
        self.show_text = ''
        self.messages = []
        self.text_browser.clear()
        self.input_text_edit.clear()
        self.hidden_text_edit.clear()

    def openChat(self):
        # 打开聊天记录
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Text files (*.txt);;All files (*)")
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            with open(file_path, 'r', encoding='utf-8') as file:
                chat_content = file.read()
                self.text_browser.setHtml(mistune.markdown(chat_content))
                self.output_text_list = chat_content.split('\n\n')
                self.show_text = chat_content

    def saveChat(self):
        # 保存聊天记录
        file_dialog = QFileDialog(self)
        file_dialog.setDefaultSuffix('.txt')
        file_dialog.setNameFilter("Text files (*.txt);;All files (*)")
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.show_text)

    def exportMarkdown(self):
        # 导出为Markdown文件
        file_dialog = QFileDialog(self)
        file_dialog.setDefaultSuffix('.md')
        file_dialog.setNameFilter("Markdown files (*.md);;All files (*)")
        if file_dialog.exec_():
            file_path = file_dialog.selectedFiles()[0]
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(self.show_text)

    def start_exam(self):
        # 创建考试场景
        self.exam_layout = QVBoxLayout()

        # 显示考试内容的文本框
        self.exam_content_area = QTextEdit(self)
        self.exam_content_area.setReadOnly(True)

        # 返回按钮
        self.back_button = QPushButton("返回", self)
        self.back_button.clicked.connect(self.return_to_main)

        # 添加控件到考试布局
        self.exam_layout.addWidget(self.exam_content_area)
        self.exam_layout.addWidget(self.back_button)

        # 创建新的页面并设置布局
        self.exam_page = QWidget()
        self.exam_page.setLayout(self.exam_layout)

        # 添加新页面到 QStackedWidget 并切换到该页面
        self.stacked_widget.addWidget(self.exam_page)
        self.stacked_widget.setCurrentWidget(self.exam_page)

        # 获取考试内容
        exam_content = self.get_exam_content()
        self.exam_content_area.setText(exam_content)

    def return_to_main(self):
        # 返回主界面
        self.stacked_widget.setCurrentWidget(self.main_page)

    def get_exam_content(self):
        # 获取当前选择的模型和角色
        model = self.model_selector.currentText()
        # role = self.role_selector.currentText()
        level = self.level_selector.currentText()

        # 获取年龄
        age = int(self.age_selector.age_slider.value())

        # 生成考试内容
        exam_content = self.generate_exam_content(model, age, level)
        return exam_content

    def generate_exam_content(self, model, age,level):
        # 这里可以根据年龄生成不同的考试内容，调用大模型API
        prompt = f"为{age}岁的学习者生成一份难度为{level}外语考试题目。"
        response = ollama.chat(model=model, messages=[{'role': 'user', 'content': prompt}])
        exam_content = response['message']['content']
        return exam_content

    def update_age_info(self, value):
        # 更新隐藏文本框中的年龄信息
        self.hidden_text_edit.setText(f"年龄: {value} 岁")




def main():
    # Linux desktop environments use an app's .desktop file to integrate the app
    # in to their application menus. The .desktop file of this app will include
    # the StartupWMClass key, set to app's formal name. This helps associate the
    # app's windows to its menu item.
    #
    # For association to work, any windows of the app must have WMCLASS property
    # set to match the value set in app's desktop file. For PySide6, this is set
    # with setApplicationName().

    # Find the name of the module that was used to start the app
    app_module = sys.modules["__main__"].__package__
    # Retrieve the app's metadata
    metadata = importlib.metadata.metadata(app_module)

    QApplication.setApplicationName(metadata["Formal-Name"])

    app = QApplication()
    main_window = ChatLocalAndPersistent()
    main_window.show()  # 显示主窗口
    sys.exit(app.exec())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatLocalAndPersistent()
    window.show()
    sys.exit(app.exec())