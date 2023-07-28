import sys
import zmq
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow
from chat_app_ui import Ui_MainWindow


class ChatApp(QMainWindow, Ui_MainWindow):
    def __init__(self, username, port, partner_ports):
        super().__init__()
        self.setupUi(self)
        self.username = username
        self.port = port
        self.partner_ports = partner_ports

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

        self.text_browser.append(username)

    def send_message(self):
        message_text = self.line_edit.text()
        if not message_text:
            return

        message = f"{self.username}: {message_text}"
        selected_users = self.get_selected_users()

        for user in selected_users:
            if user != self.username:  # Avoid sending the message to the sender itself
                self.socket_send.send_string(f"{user}:{message}")

        self.line_edit.clear()

    def get_selected_users(self):
        selected_users = []
        if self.radio_user_a.isChecked():
            selected_users.append("User A")
        if self.radio_user_b.isChecked():
            selected_users.append("User B")
        if self.radio_user_c.isChecked():
            selected_users.append("User C")
        if self.radio_group.isChecked():
            selected_users.append("Group")
        return selected_users

    def receive_messages(self):
        while True:
            try:
                message = self.socket_receive.recv_string()
                recipient, sender, text = message.split(":", 2)
                if recipient == self.username or recipient == "Group":
                    self.text_browser.append(f"{sender}: {text}")
            except zmq.ZMQError:
                break

    def closeEvent(self, event):
        self.socket_send.close()
        self.socket_receive.close()
        self.context.term()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Set up user A
    user_a = ChatApp(username="User A", port=5555, partner_ports=[5556, 5557])
    user_a.show()

    # Set up user B
    user_b = ChatApp(username="User B", port=5556, partner_ports=[5555, 5557])
    user_b.show()

    # Set up user C
    user_c = ChatApp(username="User C", port=5557, partner_ports=[5555, 5556])
    user_c.show()

    sys.exit(app.exec_())
