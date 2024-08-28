from PySide6.QtWidgets import QPushButton, QWidget


# FUNCTIONS
class MainFunctions:

    @staticmethod
    def set_page(self, page: QWidget):
        self.load_pages.pages.setCurrentWidget(page)

    # GET TITLE BUTTON BY OBJECT NAME
    @staticmethod
    def get_title_bar_btn(self, object_name):
        return self.title_bar_frame.findChild(QPushButton, object_name)
