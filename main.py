import sys
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton,
    QFileDialog, QMessageBox, QProgressBar, QSizePolicy, QScrollArea,
    QSpinBox, QFrame, QSlider, QStyledItemDelegate
)

class BackgroundDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        bg_color = index.data(Qt.ItemDataRole.BackgroundRole)
        if bg_color and isinstance(bg_color, QBrush):
            painter.fillRect(option.rect, bg_color)
        super().paint(painter, option, index)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QBrush, QColor
from qt_material import apply_stylesheet
from PIL import Image
import imagehash

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._pixmap = None

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        super().setPixmap(self._scaledPixmap())

    def resizeEvent(self, event):
        if self._pixmap is not None:
            super().setPixmap(self._scaledPixmap())
        super().resizeEvent(event)

    def _scaledPixmap(self):
        if self._pixmap is None or self._pixmap.isNull():
            return QPixmap()
        return self._pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )

class ImagePreviewPanel(QWidget):
    delete_requested = pyqtSignal(str)

    def __init__(self, title, bg_color="#1e1e1e", parent=None):
        super().__init__(parent)
        self.filepath = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.title_label = QLabel(f"<b>{title}</b>")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setMinimumWidth(1)
        layout.addWidget(self.title_label)

        self.image_container = QFrame()
        self.image_container.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 1px solid #333; border-radius: 4px; }}")
        container_layout = QVBoxLayout(self.image_container)
        container_layout.setContentsMargins(15, 15, 15, 15)

        self.image_label = ImageLabel()
        self.image_label.setStyleSheet("background-color: transparent; border: none;")
        container_layout.addWidget(self.image_label)
        
        layout.addWidget(self.image_container, stretch=1)

        info_layout = QVBoxLayout()
        self.name_label = QLabel("Name: -")
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumWidth(1)
        self.res_label = QLabel("Resolution: -")
        self.res_label.setMinimumWidth(1)
        self.size_label = QLabel("Size: -")
        self.size_label.setMinimumWidth(1)
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.res_label)
        info_layout.addWidget(self.size_label)
        layout.addLayout(info_layout)

        self.delete_btn = QPushButton("Delete Image")
        self.delete_btn.setStyleSheet("background-color: #d32f2f; color: white; font-weight: bold;")
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)

    def clear(self):
        self.filepath = None
        self.image_label.setPixmap(QPixmap())
        self.name_label.setText("Name: -")
        self.res_label.setText("Resolution: -")
        self.size_label.setText("Size: -")
        self.delete_btn.setEnabled(False)

    def set_image(self, filepath):
        if not filepath or not os.path.exists(filepath):
            self.clear()
            return
            
        self.filepath = filepath
        
        # Load image details
        try:
            stat = os.stat(filepath)
            size_kb = stat.st_size / 1024
            size_str = f"{size_kb:.2f} KB"
            if size_kb > 1024:
                size_str = f"{size_kb/1024:.2f} MB"
                
            self.size_label.setText(f"Size: {size_str}")
            self.name_label.setText(f"Name: {os.path.basename(filepath)}")
            
            with Image.open(filepath) as img:
                self.res_label.setText(f"Resolution: {img.width}x{img.height}")
            
            # Load pixmap
            pixmap = QPixmap(filepath)
            if pixmap.isNull():
                self.clear()
                self.name_label.setText(f"Name: {os.path.basename(filepath)} (Failed to load)")
                return
                
            self.image_label.setPixmap(pixmap)
            self.delete_btn.setEnabled(True)
        except Exception as e:
            self.clear()
            self.name_label.setText(f"Name: {os.path.basename(filepath)} (Error: {str(e)})")

    def on_delete_clicked(self):
        if self.filepath:
            self.delete_requested.emit(self.filepath)

def hash_image(filepath):
    try:
        with Image.open(filepath) as img:
            return filepath, imagehash.phash(img)
    except Exception:
        return filepath, None

class ScannerWorker(QThread):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    finished_scan = pyqtSignal(dict)

    def __init__(self, directory, parent=None):
        super().__init__(parent)
        self.directory = directory
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run(self):
        self.status.emit("Finding image files...")
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        image_files = []
        for root, _, files in os.walk(self.directory):
            if not self._is_running:
                return
            for file in files:
                if Path(file).suffix.lower() in valid_extensions:
                    image_files.append(os.path.join(root, file))

        total = len(image_files)
        if total == 0:
            self.finished_scan.emit({})
            return

        self.status.emit(f"Hashing {total} images...")
        hashes_dict = {}
        processed = 0
        
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            for filepath, phash in executor.map(hash_image, image_files):
                if not self._is_running:
                    return
                if phash is not None:
                    hashes_dict[filepath] = phash
                processed += 1
                if processed % max(1, total // 100) == 0 or processed == total:
                    self.progress.emit(processed, total)

        self.status.emit("Done.")
        self.finished_scan.emit(hashes_dict)

class DuplicateFinderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Similar Image Finder")
        self.resize(1100, 700)
        
        self.groups = []
        self.hashes_dict = {}
        self.worker = None

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Top bar
        top_layout = QHBoxLayout()
        self.btn_select_dir = QPushButton("Select Directory to Scan")
        self.btn_select_dir.clicked.connect(self.select_directory)
        top_layout.addWidget(self.btn_select_dir)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setMinimumWidth(150)
        top_layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        sp = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sp.setRetainSizeWhenHidden(True)
        self.progress_bar.setSizePolicy(sp)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        top_layout.addWidget(self.progress_bar)

        top_layout.addWidget(QLabel("Similarity Threshold (%):"))
        
        self.slider_threshold = QSlider(Qt.Orientation.Horizontal)
        self.slider_threshold.setRange(1, 100)
        self.slider_threshold.setValue(93)
        self.slider_threshold.setFixedWidth(150)
        top_layout.addWidget(self.slider_threshold)

        self.spin_threshold = QSpinBox()
        self.spin_threshold.setRange(1, 100)
        self.spin_threshold.setValue(93)
        self.spin_threshold.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        top_layout.addWidget(self.spin_threshold)

        self.slider_threshold.valueChanged.connect(self.spin_threshold.setValue)
        self.spin_threshold.valueChanged.connect(self.slider_threshold.setValue)
        self.slider_threshold.valueChanged.connect(self.on_threshold_changed)
        
        main_layout.addLayout(top_layout)

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter, stretch=1)

        # Left pane: Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setItemDelegate(BackgroundDelegate(self.tree_widget))
        self.tree_widget.setHeaderLabels(["Similar Images Groups"])
        self.tree_widget.setStyleSheet("QTreeWidget::item:selected { background-color: #2e0f0f; color: white; }")
        self.tree_widget.itemSelectionChanged.connect(self.on_tree_selection)
        self.splitter.addWidget(self.tree_widget)

        # Right pane: Comparison Area
        self.right_pane = QWidget()
        right_layout = QHBoxLayout(self.right_pane)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview1 = ImagePreviewPanel("Image 1 (Group Reference)", bg_color="#0f2e0f")
        self.preview2 = ImagePreviewPanel("Image 2 (Selected)", bg_color="#2e0f0f")
        
        self.preview1.delete_requested.connect(self.delete_image)
        self.preview2.delete_requested.connect(self.delete_image)

        right_layout.addWidget(self.preview1)
        right_layout.addWidget(self.preview2)
        
        self.splitter.addWidget(self.right_pane)
        self.splitter.setSizes([300, 800])

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.start_scan(directory)

    def start_scan(self, directory):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        self.tree_widget.clear()
        self.preview1.clear()
        self.preview2.clear()
        self.groups = []
        self.hashes_dict = {}
        
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.btn_select_dir.setEnabled(False)
        
        self.worker = ScannerWorker(directory)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.lbl_status.setText)
        self.worker.finished_scan.connect(self.on_scan_finished)
        self.worker.start()

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def on_scan_finished(self, hashes_dict):
        self.btn_select_dir.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.hashes_dict = hashes_dict
        
        if not hashes_dict:
            QMessageBox.information(self, "Scan Complete", "No images found.")
            self.lbl_status.setText("Ready")
            return
            
        self.update_groups()
        self.lbl_status.setText("Ready")

    def on_threshold_changed(self):
        if hasattr(self, 'hashes_dict') and self.hashes_dict:
            self.update_groups()
            
    def update_groups(self):
        threshold_pct = self.spin_threshold.value()
        
        groups = []
        visited = set()
        paths = list(self.hashes_dict.keys())
        
        for i, path1 in enumerate(paths):
            if path1 in visited:
                continue
            
            current_group = [(path1, 100.0)]
            visited.add(path1)
            hash1 = self.hashes_dict[path1]
            
            for j in range(i+1, len(paths)):
                path2 = paths[j]
                if path2 in visited:
                    continue
                hash2 = self.hashes_dict[path2]
                
                distance = hash1 - hash2
                similarity = (64 - distance) / 64 * 100.0
                
                if similarity >= threshold_pct:
                    current_group.append((path2, similarity))
                    visited.add(path2)
                    
            if len(current_group) > 1:
                current_group[1:] = sorted(current_group[1:], key=lambda x: x[1], reverse=True)
                groups.append(current_group)

        self.groups = groups
        self.rebuild_tree()

    def rebuild_tree(self):
        self.tree_widget.clear()
        
        for i, group in enumerate(self.groups):
            if len(group) < 2:
                continue
            first_image_name = os.path.basename(group[0][0])
            group_item = QTreeWidgetItem(self.tree_widget, [f"{first_image_name} ({len(group)} images)"])
            group_item.setData(0, Qt.ItemDataRole.UserRole, i) # Store group index
            
            for filepath, sim in group[1:]:
                child_item = QTreeWidgetItem(group_item, [f"{os.path.basename(filepath)} ({sim:.1f}%)"])
                child_item.setData(0, Qt.ItemDataRole.UserRole, filepath) # Store file path
                child_item.setToolTip(0, filepath)
                
        self.tree_widget.expandAll()

    def on_tree_selection(self):
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if isinstance(data, int): # It's a group item
            if item.childCount() > 0:
                self.tree_widget.setCurrentItem(item.child(0))
            return

        # Reset backgrounds
        root = self.tree_widget.invisibleRootItem()
        for i in range(root.childCount()):
            grp_item = root.child(i)
            grp_item.setBackground(0, QBrush())
            for j in range(grp_item.childCount()):
                grp_item.child(j).setBackground(0, QBrush())
        
        green_brush = QBrush(QColor("#0f2e0f"))

        if isinstance(data, str): # It's a file item
            filepath = data
            parent = item.parent()
            group_idx = parent.data(0, Qt.ItemDataRole.UserRole)
            if group_idx < len(self.groups):
                group_files = self.groups[group_idx]
                
                parent.setBackground(0, green_brush)
                
                # Left image is always first in the group
                self.preview1.set_image(group_files[0][0])
                # Right image is the selected file
                self.preview2.set_image(filepath)

    def delete_image(self, filepath):
        reply = QMessageBox.question(self, 'Confirm Deletion',
                                     f"Are you sure you want to delete this image?\n\n{filepath}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(filepath)
                self.remove_file_from_model(filepath)
                QMessageBox.information(self, "Deleted", "Image successfully deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete file:\n{str(e)}")

    def remove_file_from_model(self, filepath):
        if hasattr(self, 'hashes_dict') and filepath in self.hashes_dict:
            del self.hashes_dict[filepath]
            
        self.update_groups()
        
        if self.preview1.filepath == filepath:
            self.preview1.clear()
        if self.preview2.filepath == filepath:
            self.preview2.clear()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme='dark_teal.xml')
    window = DuplicateFinderApp()
    window.show()
    sys.exit(app.exec())