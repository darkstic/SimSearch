import sys
from PyQt6.QtCore import Qt, QSize, QUrl, QPoint, QMimeData, QPropertyAnimation
from PyQt6.QtGui import QIcon, QPixmap, QDrag, QDropEvent, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QScrollArea, QGridLayout, QStackedLayout, QFileDialog, QMenu, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

DEFAULT_SEARCH_URL = "https://www.google.com"

class CircularTabButton(QWidget):
    def __init__(self, simsearch_ref, icon=None, label="", on_click=None, on_close=None, on_right_click=None):
        super().__init__()
        self.simsearch = simsearch_ref
        self.setFixedSize(80, 100)
        self.setAcceptDrops(True)
        self.on_right_click = on_right_click

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.layout)

        self.button = QPushButton()
        self.button.setIcon(icon if icon else QIcon())
        self.button.setIconSize(QSize(48, 48))
        self.button.setFixedSize(64, 64)
        self.button.setStyleSheet("border-radius: 32px; border: 2px solid gray;")

        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(16, 16)
        self.close_button.setStyleSheet("QPushButton { background-color: red; color: white; border: none; border-radius: 8px; font-size: 10px; }")
        self.close_button.setParent(self.button)
        self.close_button.move(48, 0)
        self.close_button.raise_()
        if on_close:
            self.close_button.clicked.connect(on_close)

        self.label = QLabel(label[:20])
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setFixedWidth(80)
        self.label.setStyleSheet("font-size: 10px;")

        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)

        if on_click:
            self.button.clicked.connect(lambda: on_click())

    def set_active(self, active):
        if active:
            self.button.setStyleSheet("border-radius: 32px; border: 3px solid blue;")
        else:
            self.button.setStyleSheet("border-radius: 32px; border: 2px solid gray;")

    def set_icon(self, icon):
        if icon and not icon.isNull():
            self.button.setIcon(icon)

    def set_label(self, text):
        self.label.setText(text[:20])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(id(self)))
            drag.setMimeData(mime_data)
            drag.setHotSpot(event.pos())
            drag.exec()
        elif event.button() == Qt.MouseButton.RightButton and self.on_right_click:
            self.on_right_click(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            self.setStyleSheet("background-color: lightblue;")
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        source_id = int(event.mimeData().text())
        self.simsearch.reorder_tabs_by_id(source_id, id(self))
        self.setStyleSheet("")
        event.acceptProposedAction()

class SimSearch(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimSearch")
        self.setGeometry(100, 100, 1200, 800)

        self.tabs = []
        self.active_tab_index = -1
        self.tab_buttons = []
        self.favorites = []

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QHBoxLayout(self.central_widget)
        self.view_stack = QStackedLayout()

        self.sidebar = self._build_sidebar()
        self.main_layout.addLayout(self.view_stack)
        self.main_layout.addWidget(self.sidebar)

        self.add_new_tab(DEFAULT_SEARCH_URL)

    def _build_sidebar(self):
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar_container)

        fav_label = QLabel("Favorites")
        fav_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        sidebar_layout.addWidget(fav_label)

        self.fav_grid = QGridLayout()
        self.fav_grid.setSpacing(5)
        fav_widget = QWidget()
        fav_widget.setLayout(self.fav_grid)
        fav_scroll = QScrollArea()
        fav_scroll.setWidgetResizable(True)
        fav_scroll.setWidget(fav_widget)
        fav_scroll.setFixedHeight(150)
        fav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        fav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_layout.addWidget(fav_scroll)

        tab_label = QLabel("Tabs")
        tab_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        sidebar_layout.addWidget(tab_label)

        self.tab_grid = QGridLayout()
        self.tab_grid.setSpacing(5)
        self.tab_container = QWidget()
        self.tab_container.setLayout(self.tab_grid)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.tab_container)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_layout.addWidget(scroll)

        new_tab_btn = QPushButton("+ New Tab")
        new_tab_btn.setStyleSheet("font-weight: bold; background-color: #007bff; color: white; padding: 8px; font-size: 16px;")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab(DEFAULT_SEARCH_URL))
        sidebar_layout.addWidget(new_tab_btn)

        open_html_btn = QPushButton("Open HTML File")
        open_html_btn.setStyleSheet("font-size: 10px; padding: 2px; margin-top: 5px;")
        open_html_btn.clicked.connect(self.open_html_file)
        sidebar_layout.addWidget(open_html_btn)

        sidebar_layout.addStretch()
        return sidebar_container

    def add_new_tab(self, url):
        browser = QWebEngineView()
        browser.setUrl(QUrl(url))
        self.tabs.append(browser)
        self.view_stack.addWidget(browser)
        index = len(self.tabs) - 1

        def on_click():
            current_index = self.tab_buttons.index(tab_button)
            self.switch_to_tab(current_index)

        def on_close():
            current_index = self.tab_buttons.index(tab_button)
            self.close_tab(current_index)

        tab_button = CircularTabButton(self, QIcon(), f"Tab {index + 1}", on_click=on_click, on_close=on_close)
        self.tab_buttons.append(tab_button)
        self._rebuild_tab_grid()

        browser.loadFinished.connect(lambda ok, b=browser, t=tab_button: self._update_tab_info(b, t))
        browser.titleChanged.connect(lambda title, t=tab_button: t.set_label(title))
        browser.iconChanged.connect(lambda icon, t=tab_button: t.set_icon(icon))

        def context_menu(point):
            menu = QMenu()
            add_fav = menu.addAction("Add to Favorites")
            action = menu.exec(browser.mapToGlobal(point))
            if action == add_fav:
                self.add_to_favorites(tab_button.label.text(), browser.url().toString(), browser.icon())

        browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        browser.customContextMenuRequested.connect(context_menu)

        self.switch_to_tab(index)

    def _update_tab_info(self, browser, tab_button):
        icon = browser.icon()
        title = browser.title()
        if not icon.isNull():
            tab_button.set_icon(icon)
        if title:
            tab_button.set_label(title[:20])

    def switch_to_tab(self, index):
        if 0 <= index < len(self.tabs):
            self.active_tab_index = index
            self.view_stack.setCurrentIndex(index)
            for i, btn in enumerate(self.tab_buttons):
                btn.set_active(i == index)

    def close_tab(self, index):
        if 0 <= index < len(self.tabs):
            widget = self.tabs.pop(index)
            self.view_stack.removeWidget(widget)
            widget.deleteLater()
            self.tab_buttons.pop(index)
            self._rebuild_tab_grid()
            if self.tabs:
                self.switch_to_tab(min(index, len(self.tabs) - 1))

    def add_to_favorites(self, label, url, icon):
        fav_index = len(self.favorites)

        def remove_fav(btn):
            for i in range(self.fav_grid.count()):
                if self.fav_grid.itemAt(i).widget() == btn:
                    self.fav_grid.itemAt(i).widget().setParent(None)
                    self.favorites.pop(i)
                    self._rebuild_fav_grid()
                    break

        btn = CircularTabButton(self, icon, label, on_click=lambda: self.add_new_tab(url), on_right_click=remove_fav)
        self.favorites.append((label, url, btn))
        self._rebuild_fav_grid()

    def _rebuild_fav_grid(self):
        for i in reversed(range(self.fav_grid.count())):
            self.fav_grid.itemAt(i).widget().setParent(None)
        for index, (_, _, btn) in enumerate(self.favorites):
            row, col = divmod(index, 3)
            self.fav_grid.addWidget(btn, row, col)

    def _rebuild_tab_grid(self):
        for i in reversed(range(self.tab_grid.count())):
            self.tab_grid.itemAt(i).widget().setParent(None)
        for index, btn in enumerate(self.tab_buttons):
            row, col = divmod(index, 3)
            self.tab_grid.addWidget(btn, row, col)

    def reorder_tabs_by_id(self, source_id, target_id):
        source_index = next((i for i, btn in enumerate(self.tab_buttons) if id(btn) == source_id), None)
        target_index = next((i for i, btn in enumerate(self.tab_buttons) if id(btn) == target_id), None)
        if source_index is not None and target_index is not None and source_index != target_index:
            self.tab_buttons.insert(target_index, self.tab_buttons.pop(source_index))
            self.tabs.insert(target_index, self.tabs.pop(source_index))
            widget = self.view_stack.widget(source_index)
            self.view_stack.removeWidget(widget)
            self.view_stack.insertWidget(target_index, widget)
            self._rebuild_tab_grid()
            self.switch_to_tab(target_index)

    def open_html_file(self):
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("HTML Files (*.html *.htm)")
        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            self.add_new_tab(QUrl.fromLocalFile(selected_file).toString())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SimSearch()
    win.show()
    sys.exit(app.exec())
