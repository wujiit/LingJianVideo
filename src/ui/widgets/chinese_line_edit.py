"""
Custom QLineEdit with Chinese context menu
"""
from PySide6.QtWidgets import QLineEdit, QMenu
from PySide6.QtGui import QAction


class ChineseLineEdit(QLineEdit):
    """QLineEdit with Chinese context menu"""
    
    def contextMenuEvent(self, event):
        """Override to create Chinese context menu"""
        menu = QMenu(self)
        
        # 撤销
        undo_action = QAction("撤销", self)
        undo_action.setEnabled(self.isUndoAvailable())
        undo_action.triggered.connect(self.undo)
        menu.addAction(undo_action)
        
        # 重做
        redo_action = QAction("重做", self)
        redo_action.setEnabled(self.isRedoAvailable())
        redo_action.triggered.connect(self.redo)
        menu.addAction(redo_action)
        
        menu.addSeparator()
        
        # 剪切
        cut_action = QAction("剪切", self)
        cut_action.setEnabled(self.hasSelectedText())
        cut_action.triggered.connect(self.cut)
        menu.addAction(cut_action)
        
        # 复制
        copy_action = QAction("复制", self)
        copy_action.setEnabled(self.hasSelectedText())
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)
        
        # 粘贴
        paste_action = QAction("粘贴", self)
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)
        
        # 删除
        delete_action = QAction("删除", self)
        delete_action.setEnabled(self.hasSelectedText())
        delete_action.triggered.connect(self._delete_selected)
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        # 全选
        select_all_action = QAction("全选", self)
        select_all_action.setEnabled(len(self.text()) > 0)
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)
        
        menu.exec(event.globalPos())
    
    def _delete_selected(self):
        """Delete selected text"""
        if self.hasSelectedText():
            self.del_()
