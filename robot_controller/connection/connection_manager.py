import serial
import threading
import core
import time
import logger
import controller_board_manager
from connection.interface.connection_interface import ConnectionInterface
from connection.interface.serial_interface import SerialInterface
from connection.interface.network_interface import NetworkInterface
from connection.output_packets import OutputPacket
from connection.input_packets import *
from connection.packet_event_listener import PacketEventListener


connection_interface: ConnectionInterface = NetworkInterface()  # 通信インターフェース（シリアルorネットワーク）
event_listener = PacketEventListener()
initialized = False  # Arduinoのシリアルポートが初期化されたかどうか
sending_stopped = False  # Arduinoへのパケット送信が可能かどうか
packet_key_queue = []  # パケット（rand_id）のキュー
packet_queue = {}  # パケットのキュー


# 初期化
def init():
    logger.info("Initializing connection interface...")
    connection_interface.init()

    logger.info("Starting packet receiver...")
    th = threading.Thread(target=_await_packets)
    th.start()

    logger.info("Starting packet sender...")
    th1 = threading.Thread(target=_send_packets)
    th1.start()


# SensorManagerを保持
def add_sensor_manager(rand_id, sensor_manager):
    event_listener.add_manager(rand_id, sensor_manager)


# キューにパケットを追加する
def data_packet(packet: OutputPacket):
    packet.encode()
    packet_key_queue.insert(0, packet.rand_id)
    packet_queue[packet.rand_id] = packet


# パケット送信のキューイング
def _send_packets():
    while core.running:
        if not sending_stopped and not len(packet_key_queue) == 0:
            rand_id = packet_key_queue.pop()
            pk = packet_queue[rand_id]
            _send_packet(pk)

        time.sleep(0.01)  # 10ms待つ


# パケットを送信
def _send_packet(pk):
    if core.debug:
        logger.send("(" + str(len(pk.data)) + ") " + str(pk.data))
        logger.state(str(core.instance.state))

    controller_board_manager.green_led_on()
    connection_interface.send_data(pk.data)


# パケット受信待機
def _await_packets():
    global initialized
    while core.running:
        if connection_interface.is_waiting():
            continue

        controller_board_manager.blue_led_on()

        raw = connection_interface.read_data()
        raw_hex = raw.hex()

        if core.debug:
            logger.receive("(" + str(len(raw)) + ") " + raw_hex)

        # 通信開始
        if (not initialized) and bytearray("Transmission Start", encoding='utf8').hex() in raw_hex:
            initialized = True
            event_listener.on_connection_start()
            continue

        # データサイズエラー
        if "Invalid data size" in raw_hex:
            logger.error("Invalid Data Size Error")
            continue

        # 受信データを\r\nで区切って処理
        split = str(raw_hex).split("0d0a")
        global sending_stopped

        for text in split:
            array = bytearray.fromhex(text)
            string = ""

            try:
                string = array.decode(encoding='utf8')
            except UnicodeDecodeError:
                pass

            # パケット送信停止命令
            if string == "Stop":
                sending_stopped = True
                continue

            # 受信信号（rand_id）
            elif string.isdecimal() and len(string) == 4:
                sending_stopped = False  # パケット送信停止解除
                del packet_queue[int(string)]
                continue

            # Arduino to Raspberry Pi Packet
            # TODO RaspberryPiPacket to ArduinoPacket
            elif len(array) > InputPacket.PACKET_LENGTH:
                byte_ids = array[InputPacket.PACKET_LENGTH:]
                ids = [0, 0, 0, 0]
                i = 0
                for b in byte_ids:
                    ids[i] = str(int(b))
                    i = i + 1

                # キューからパケットを削除
                if len(ids) == 4:
                    sending_stopped = False  # パケット送信停止解除
                    del packet_queue[int("".join(ids))]

                _process_packet(array[0:InputPacket.PACKET_LENGTH - 1])

            elif len(array) == InputPacket.PACKET_LENGTH:
                _process_packet(array)

            # 予期しないパケットのとき
            else:
                logger.error("Unexpected Packet Error (" + string + ")")
                continue


# 受信パケットの処理
def _process_packet(pk_data):
    try:
        packet = InputPacket(pk_data)
        packet.decode()

        if packet.packet_id == RightSteppingMotorAlertPacket.ID:
            pk = RightSteppingMotorAlertPacket(packet.data)
            pk.decode()
            event_listener.on_right_stepping_motor_alerted(pk)

        elif packet.packet_id == RightSteppingMotorFeedbackPacket.ID:
            pk = RightSteppingMotorFeedbackPacket(packet.data)
            pk.decode()
            event_listener.on_right_stepping_motor_feedback(pk)

        elif packet.packet_id == LeftSteppingMotorAlertPacket.ID:
            pk = LeftSteppingMotorAlertPacket(packet.data)
            pk.decode()
            event_listener.on_left_stepping_motor_alerted(pk)

        elif packet.packet_id == LeftSteppingMotorFeedbackPacket.ID:
            pk = LeftSteppingMotorFeedbackPacket(packet.data)
            pk.decode()
            event_listener.on_left_stepping_motor_feedback(pk)

        elif packet.packet_id == DistanceSensorResultPacket.ID:
            pk = DistanceSensorResultPacket(packet.data)
            pk.decode()
            event_listener.on_distance_sensor_resulted(pk)

        elif packet.packet_id == LineTracerResultPacket.ID:
            pk = LineTracerResultPacket(packet.data)
            pk.decode()
            event_listener.on_line_tracer_resulted(pk)

        elif packet.packet_id == NineAxisSensorResultPacket.ID:
            pk = NineAxisSensorResultPacket(packet.data)
            pk.decode()
            event_listener.on_nine_axis_sensor_resulted(pk)

        elif packet.packet_id == UpperServoMotorFeedbackPacket.ID:
            pk = UpperServoMotorFeedbackPacket(packet.data)
            pk.decode()
            event_listener.on_upper_servo_motor_feedback(pk)

        elif packet.packet_id == BottomServoMotorFeedbackPacket.ID:
            pk = BottomServoMotorFeedbackPacket(packet.data)
            pk.decode()
            event_listener.on_bottom_servo_motor_feedback(pk)

    except AssertionError as e:
        logger.error(e)
        return



