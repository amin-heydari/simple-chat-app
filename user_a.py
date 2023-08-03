import sys
import threading

import zmq
from PyQt5.QtWidgets import QMainWindow, QDialog, QApplication

import new_group_ui
from main_ui import Ui_MainWindow


class ChatApp(QMainWindow, Ui_MainWindow):
    def __init__(self, username, port, partner_ports):
        super().__init__()
        self.setupUi(self)
        self.group_users = []
        self.username = username
        self.port = port
        self.partner_ports = partner_ports
        self.setWindowTitle(username)
        self.listWidget.itemClicked.connect(self.is_clicked)
        self.last_selected_item_text = ''
        self.listWidgetItems = self.listWidget
        self.action_newGroup.triggered.connect(self.add_item)

        self.context = zmq.Context()
        self.socket_send = self.context.socket(zmq.PUB)
        self.socket_send.bind(f"tcp://*:{self.port}")

        self.socket_receive = self.context.socket(zmq.SUB)
        self.socket_receive.setsockopt_string(zmq.SUBSCRIBE, "")

        for partner_port in self.partner_ports:
            self.socket_receive.connect(f"tcp://127.0.0.1:{partner_port}")

        self.send_button.clicked.connect(self.send_message)

        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def add_item(self):
        """Open a dialog to create a new group and send group invitations."""
        a = NewGroup()
        a.exec_()
        self.group_users = a.get_users()
        self.listWidget.addItem('Group')
        for user in self.group_users:
            if user != self.username:
                self.socket_send.send_string(f'group:{self.username}:{user}')

    def is_clicked(self, item):
        """Handle item selection in the list of users/groups."""
        selected_item_text = item.text()
        if self.last_selected_item_text != selected_item_text:
            self.textEdit_show_messages.clear()
            self.last_selected_item_text = selected_item_text

    def send_message(self):
        message_text = self.input_text.toPlainText()
        if not message_text:
            return

        message = f"{self.username}: {message_text}"
        selected_users = self.get_selected_users()
        if selected_users != self.username:
            self.textEdit_show_messages.append(f'{message}')
            self.socket_send.send_string(f"{selected_users}:{message}")
            print(message, 'send')
        self.input_text.clear()

    def get_selected_users(self):
        """Get the selected user/group for sending messages."""
        return self.corresponding_user.text()

    def receive_messages(self):
        while True:
            try:
                message = self.socket_receive.recv_string()
                print(message)
                recipient, sender, text = message.split(":", 2)
                if recipient == 'group' and text == self.username:
                    self.listWidget.addItem('Group')
                if recipient == self.username and self.corresponding_user.text() == sender:
                    self.textEdit_show_messages.append(f"{sender}: {text}")
                elif recipient == 'Group' and self.corresponding_user.text() == 'Group':
                    self.textEdit_show_messages.append(f'{sender}: {text}')
            except zmq.ZMQError as zmq_error:
                print(f"ZMQ Error: {zmq_error}")
            except Exception as e:
                print(f"Error occurred: {e}")

    def closeEvent(self, event):
        """Close the application, closing sockets and terminating context."""
        self.socket_send.close()
        self.socket_receive.close()
        self.context.term()
        super().closeEvent(event)


class NewGroup(new_group_ui.Ui_Dialog, QDialog):
    """Initialize the dialog for creating a new group."""

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.create_btn.clicked.connect(self.close_window)

    def close_window(self):
        """Close the new group dialog."""
        self.close()

    def get_users(self):
        """Get the selected users for a new group."""
        users = []
        if self.user_a.isChecked():
            users.append('User A')
        if self.user_b.isChecked():
            users.append('User B')
        if self.user_c.isChecked():
            users.append('User C')
        return users


if __name__ == '__main__':
    app = QApplication(sys.argv)
    user_a = ChatApp(username='User A', port=5555, partner_ports=[5556, 5557])
    user_a.show()
    sys.exit(app.exec_())
