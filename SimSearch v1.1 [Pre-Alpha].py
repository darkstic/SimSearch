import sys
import os
import json
from PyQt6.QtCore import Qt, QSize, QUrl, QPoint, QMimeData, QPropertyAnimation
from PyQt6.QtGui import QIcon, QPixmap, QDrag, QDropEvent, QAction
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QLabel, QScrollArea, QGridLayout, QStackedLayout, QFileDialog, QMenu, QFrame, QToolBar, QLineEdit,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView

DEFAULT_SEARCH_URL = "https://www.google.com"
PERSISTENCE_FILE = "simsearch_state.json"

class CircularTabButton(QWidget):
    def __init__(self, simsearch_ref, icon=None, label="", on_click=None, on_close=None, on_right_click=None):
        super().__init__()
        self.simsearch = simsearch_ref
        self.setFixedSize(80, 100)
        self.setAcceptDrops(True)
        self.on_right_click = on_right_click

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.button = QPushButton()
        self.button.setIcon(icon if icon else QIcon())
        self.button.setIconSize(QSize(48, 48))
        self.button.setFixedSize(64, 64)
        self.button.setStyleSheet("border-radius: 32px; border: 2px solid gray;")

        self.close_button = QPushButton("X")
        self.close_button.setFixedSize(16, 16)
        self.close_button.setStyleSheet("QPushButton { background-color: red; color: white; border: none; border-radius: 8px; font-size: 10px; }")
        self.close_button.setParent(self)
        self.close_button.move(60, 0)
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
        self.setLayout(self.layout)

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

        self.main_layout = QVBoxLayout(self.central_widget)

        self.toolbar = QToolBar()
        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Enter URL...")
        self.address_bar.returnPressed.connect(self.load_address)
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_url)

        self.toolbar.addWidget(QLabel("URL: "))
        self.toolbar.addWidget(self.address_bar)
        self.toolbar.addWidget(copy_button)
        self.main_layout.addWidget(self.toolbar)

        self.content_layout = QHBoxLayout()
        self.view_stack = QStackedLayout()

        self.sidebar = self._build_sidebar()
        self.content_layout.addLayout(self.view_stack)
        self.content_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.content_layout)

        self.load_state()

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
        new_tab_btn.setStyleSheet("font-weight: bold; background-color: #007bff; color: white; padding: 5px; font-size: 14px;")
        new_tab_btn.clicked.connect(lambda: self.add_new_tab(DEFAULT_SEARCH_URL))
        sidebar_layout.addWidget(new_tab_btn)

        open_html_btn = QPushButton("Open HTML File")
        open_html_btn.setStyleSheet("font-size: 10px; padding: 2px;")
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
        browser.urlChanged.connect(lambda url, b=browser: self._update_address_bar_if_active(b, url))

        def context_menu(point):
            menu = QMenu()
            add_fav = menu.addAction("Add to Favorites")
            reload_page = menu.addAction("Reload Tab")
            close_tab = menu.addAction("Close Tab")
            action = menu.exec(browser.mapToGlobal(point))
            if action == add_fav:
                self.add_to_favorites(tab_button.label.text(), browser.url().toString(), browser.icon())
            elif action == reload_page:
                browser.reload()
            elif action == close_tab:
                on_close()

        browser.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        browser.customContextMenuRequested.connect(context_menu)

        self.switch_to_tab(index)
        self.save_state()

    def _update_tab_info(self, browser, tab_button):
        icon = browser.icon()
        title = browser.title()
        if not icon.isNull():
            tab_button.set_icon(icon)
        if title:
            tab_button.set_label(title[:20])

    def _update_address_bar_if_active(self, browser, url):
        index = self.tabs.index(browser)
        if index == self.active_tab_index:
            self.address_bar.setText(url.toString())

    def switch_to_tab(self, index):
        if 0 <= index < len(self.tabs):
            self.active_tab_index = index
            self.view_stack.setCurrentIndex(index)
            for i, btn in enumerate(self.tab_buttons):
                btn.set_active(i == index)
            # Update address bar to match the new active tab
            current_url = self.tabs[index].url().toString()
            self.address_bar.setText(current_url)

    def close_tab(self, index):
        if 0 <= index < len(self.tabs):
            widget = self.tabs.pop(index)
            self.view_stack.removeWidget(widget)
            widget.deleteLater()
            self.tab_buttons.pop(index)
            self._rebuild_tab_grid()
            self.switch_to_tab(min(index, len(self.tabs) - 1))
            self.save_state()

    def add_to_favorites(self, label, url, icon):
        fav_index = len(self.favorites)

        def remove_fav(btn):
            for i in range(self.fav_grid.count()):
                if self.fav_grid.itemAt(i).widget() == btn:
                    self.fav_grid.itemAt(i).widget().setParent(None)
                    self.favorites.pop(i)
                    self._rebuild_fav_grid()
                    self.save_state()
                    break

        btn = CircularTabButton(self, icon, label, on_click=lambda: self.add_new_tab(url), on_right_click=remove_fav)
        self.favorites.append((label, url, btn))
        self._rebuild_fav_grid()
        self.save_state()

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
            self.save_state()

    def open_html_file(self):
        file_dialog = QFileDialog()
        file_dialog.setNameFilter("HTML Files (*.html *.htm)")
        if file_dialog.exec():
            selected_file = file_dialog.selectedFiles()[0]
            self.add_new_tab(QUrl.fromLocalFile(selected_file).toString())

    def save_state(self):
        state = {
            "tabs": [self.tabs[i].url().toString() for i in range(len(self.tabs))],
            "favorites": [(label, url) for label, url, _ in self.favorites]
        }
        try:
            with open(PERSISTENCE_FILE, "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Error saving state: {e}")

    def load_state(self):
        if os.path.exists(PERSISTENCE_FILE):
            try:
                with open(PERSISTENCE_FILE, "r") as f:
                    state = json.load(f)
                for url in state.get("tabs", [DEFAULT_SEARCH_URL]):
                    self.add_new_tab(url)
                for label, url in state.get("favorites", []):
                    self.add_to_favorites(label, url, QIcon())
            except Exception as e:
                print(f"Error loading state: {e}")
        else:
            self.add_new_tab(DEFAULT_SEARCH_URL)

    def clear_all_data(self):
        if os.path.exists(PERSISTENCE_FILE):
            os.remove(PERSISTENCE_FILE)
        QApplication.quit()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def load_address(self):
        url = self.address_bar.text()
        if not url.startswith("http"):
            url = "https://" + url
        if self.active_tab_index != -1:
            self.tabs[self.active_tab_index].setUrl(QUrl(url))

    def copy_url(self):
        if self.active_tab_index != -1:
            url = self.tabs[self.active_tab_index].url().toString()
            clipboard = QApplication.clipboard()
            clipboard.setText(url)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SimSearch()
    win.show()
    sys.exit(app.exec())
