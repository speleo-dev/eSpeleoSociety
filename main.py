import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QDialog, QStatusBar
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QCoreApplication, Qt, QTranslator, QLocale, QLibraryInfo
from config import secret_manager, get_preferred_language
from setup import run_setup, show_pin_dialog
import db, model

# Import navigation panel and content views
from navigation_panel import NavigationPanel
from views.clubs_list_view import ClubsListView
from views.member_search_view import MemberSearchView
from views.ecp_requests_view import ECPRequestsView
from views.members_list_view import MembersListView # Added import
from views.notifications_view import NotificationsView
from views.sepa_import_view import SepaImportView
from views.settings_view import SettingsView # Import new view
from views.reporting_view import ReportingView # Import new ReportingView
from dialogs.club_management_dialog import ClubManagementDialog
from utils import load_logo, show_warning_message, load_all_configs

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(QCoreApplication.translate("MainWindow", "eSpeleoSociety"))
        self.setGeometry(100, 100, 1200, 800)

        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #B0B0B0; /* Top border */
            }
            QStatusBar::item {
                border: none; /* Removes any border around individual items in the statusbar */
            }
        """)

        # # Nastavenie ikonky okna
        # icon_path = os.path.join(os.path.dirname(__file__), "icons", "Logo_sss.ico")
        # if os.path.exists(icon_path):
        #     self.setWindowIcon(QIcon(icon_path))
        
        # self.setStyleSheet("background-color: rgb(100, 140, 240);")

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Creating the navigation panel (left side)
        self.nav_panel = NavigationPanel()
        self.nav_panel.setFixedWidth(300)
        # Loading the logo and setting it in the navigation panel
        logo = load_logo()
        if logo:
            self.nav_panel.set_logo(logo)
        main_layout.addWidget(self.nav_panel)
        
        # Content panel – QStackedWidget for dynamic view switching
        self.content_panel = QStackedWidget()
        main_layout.addWidget(self.content_panel)
        
        # Creating instances of individual views
        self.clubs_list_view = ClubsListView(parent=self)            # List of clubs
        self.members_list_view = MembersListView(parent_window=self, parent=self)        # List of members for a specific club
        self.member_search_view = MemberSearchView()          # Member search
        self.ecp_requests_view = ECPRequestsView()            # eCP requests
        self.notifications_view = NotificationsView()         # SSS messages
        self.sepa_import_view = SepaImportView()              # Import SEPA statement
        self.settings_view = SettingsView()                   # Application settings
        self.reporting_view = ReportingView()                 # Reporting view

        # Adding views to the content panel
        self.content_panel.addWidget(self.clubs_list_view)       
        self.content_panel.addWidget(self.members_list_view)
        self.content_panel.addWidget(self.member_search_view)      
        self.content_panel.addWidget(self.ecp_requests_view)       
        self.content_panel.addWidget(self.notifications_view)      
        self.content_panel.addWidget(self.sepa_import_view)
        self.content_panel.addWidget(self.settings_view) # Adding SettingsView
        self.content_panel.addWidget(self.reporting_view) # Adding ReportingView

        # Connecting signals from the navigation panel with content switching
        self.nav_panel.show_clubs_list_signal.connect(lambda: self.content_panel.setCurrentWidget(self.clubs_list_view))
        self.nav_panel.show_member_search_signal.connect(lambda: self.content_panel.setCurrentWidget(self.member_search_view))
        self.nav_panel.show_ecp_requests_signal.connect(lambda: self.content_panel.setCurrentWidget(self.ecp_requests_view))
        self.nav_panel.show_notifications_signal.connect(lambda: self.content_panel.setCurrentWidget(self.notifications_view))
        self.nav_panel.show_sepa_import_signal.connect(lambda: self.content_panel.setCurrentWidget(self.sepa_import_view))
        self.nav_panel.show_settings_signal.connect(lambda: self.content_panel.setCurrentWidget(self.settings_view)) # Connecting the signal
        self.nav_panel.show_reporting_signal.connect(lambda: self.content_panel.setCurrentWidget(self.reporting_view)) # Connecting the signal for Reporting

        # Connecting the signal from ClubsListView to display members
        self.clubs_list_view.navigateToMembers.connect(self.display_members_for_club)

        self.status_bar.showMessage(QCoreApplication.translate("MainWindow", "Ready"))

    def open_club_management(self, club: model.Club):
        """Opens the club management dialog and updates the views."""
        dlg = ClubManagementDialog(club=club, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            # Always refresh the list of clubs, as club details may have changed
            self.clubs_list_view.load_data()

            # If MembersListView is currently displayed and shows the club being edited,
            # refresh its data.
            if self.content_panel.currentWidget() == self.members_list_view and \
               self.members_list_view.current_club and \
               self.members_list_view.current_club.club_id == club.club_id:
                
                updated_club_data = db.db_manager.fetch_club_by_id(club.club_id)
                if updated_club_data:
                    self.members_list_view.load_data_for_club(updated_club_data)
                else:
                    # If the club was not found after editing (e.g., it was deleted by another process in the meantime)
                    show_warning_message(QCoreApplication.translate("MainWindow", f"Club with ID {club.club_id} could not be loaded after editing."))
                    # Return to the list of clubs
                    self.content_panel.setCurrentWidget(self.clubs_list_view)

    def display_members_for_club(self, club_id: int):
        club = db.db_manager.fetch_club_by_id(club_id)
        if club:
            self.current_club = club # Set the current club in MainWindow
            self.members_list_view.load_data_for_club(club)
            self.content_panel.setCurrentWidget(self.members_list_view)
        else:
            show_warning_message(QCoreApplication.translate("MainWindow", f"Club with ID {club_id} not found."))

if __name__ == "__main__":
    # Aktivácia podpory pre High DPI scaling
    # This must be called before creating the QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    # translations
    pref_language = get_preferred_language() 

    qt_translator = QTranslator()
    qt_translation_path = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(pref_language), "qt", "_", qt_translation_path):
        app.installTranslator(qt_translator)
    else:
        print(f"Warning: Could not load Qt base translations for locale '{pref_language}' from '{qt_translation_path}'.")

    app_translator = QTranslator()
    translation_file = os.path.join("translate", f"{pref_language}.qm")
    if os.path.exists(translation_file):
        if app_translator.load(translation_file):
            app.installTranslator(app_translator)
        else:
            print(f"Error: Failed to load application translation file: {translation_file}")
    
    # Setting the global style for QPushButton
    app.setStyleSheet("""
        QPushButton {
            border: 1px solid #8f8f91;
            border-radius: 6px; /* This sets rounded corners */
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #f6f7fa, stop: 1 #dadbde);
            min-width: 50px; /* Reduced minimum button width */
            padding: 5px; /* Inner margin for text */
        }
        QPushButton:hover {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #dadbde, stop: 1 #f6f7fa);
        }
        QPushButton:pressed {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #dadbde, stop: 1 #BEBEBE);
        }
    """)

    default_font = QFont() # You can also specify the family, e.g., QFont("Arial")
    default_font.setPointSize(9) # <-- CHANGE THIS VALUE as needed (e.g., 8, 9, 10)
    app.setFont(default_font)

    # Application icon
    icon_path = os.path.join(os.path.dirname(__file__), "images", "logo.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        warning_message = QCoreApplication.translate("Main", "Warning: Icon file not found in path %1")
        print(warning_message.replace("%1", icon_path))
    
    # If no secrets.properties exist run setup
    if not os.path.exists(secret_manager.properties_file):
        run_setup(app)
        if not secret_manager.secrets:
            error_message = QCoreApplication.translate("Main", "Error: Secrets was not saved.")
            print(error_message)
            sys.exit()
    else:
        # check PIN if secrets are found
        if not show_pin_dialog(app):
            error_message = QCoreApplication.translate("Main", "Error: PIN was not entered.")
            print(error_message)
            sys.exit()
        if not secret_manager.secrets:
            error_message = QCoreApplication.translate("Main", "Error: Secrets was not loaded.")
            print(error_message)
            sys.exit()
    
    # Loading application and library configurations
    load_all_configs()

    # DB Init
    db.db_manager = db.DatabaseManager()
    
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())
