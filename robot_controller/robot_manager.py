import random
import struct
import math
import threading
import time
from connection import connection_manager
from connection.rpi_to_arduino_packets import *
from sensor.sensor_mamager import SensorManager


TIRE_RADIUS = 45.0  # タイヤ半径[mm]
ROTATION_DEGREE = 90.0  # 回転時にタイヤが回る角度[deg]

x = 0.0  # 自己位置の合計変位x
y = 0.0  # 自己位置の合計変位y
direction = 0.0  # degree
measuring_distance = False
measuring_line_tracer = False

# 右に90度回転
def rotate_right():
    pk_r = RightSteppingMotorPacket(rand())
    pk_r.locked = RightSteppingMotorPacket.MOTOR_LOCKED
    pk_r.direction = RightSteppingMotorPacket.ROTATE_LOCKED
    connection_manager.data_packet(pk_r)

    pk_l = LeftSteppingMotorPacket(rand())
    pk_l.locked = RightSteppingMotorPacket.MOTOR_UNLOCKED
    pk_l.direction = RaspberryPiPacket.ROTATE_LEFT_RETURN
    pk_l.data_1 = create_filled_data1(ROTATION_DEGREE)
    connection_manager.data_packet(pk_l)


# 左に90度回転
def rotate_left():
    pk_l = LeftSteppingMotorPacket(rand())
    pk_l.locked = LeftSteppingMotorPacket.MOTOR_LOCKED
    pk_l.direction = LeftSteppingMotorPacket.ROTATE_LOCKED
    connection_manager.data_packet(pk_l)

    pk_r = RightSteppingMotorPacket(rand())
    pk_r.locked = RightSteppingMotorPacket.MOTOR_UNLOCKED
    pk_r.direction = RaspberryPiPacket.ROTATE_LEFT_RETURN
    pk_r.data_1 = create_filled_data1(ROTATION_DEGREE)
    connection_manager.data_packet(pk_l)


# 指定された距離だけ直進
# @arg distance(mm)
def go_straight_distance(distance):
    pk = BothSteppingMotorPacket(rand())
    pk.locked = False
    pk.direction = BothSteppingMotorPacket.ROTATE_RIGHT_FORWARD
    pk.type = BothSteppingMotorPacket.DATA_TYPE_1
    # TODO 角速度と総角度 360 * distance / (TIRE_RADIUS * 2 * math.pi)
    connection_manager.data_packet(pk)


# 続けて前進
def go_straight():
    pk = BothSteppingMotorPacket(rand())
    pk.locked = False
    pk.direction = BothSteppingMotorPacket.ROTATE_RIGHT_FORWARD
    pk.type = BothSteppingMotorPacket.DATA_TYPE_3
    connection_manager.data_packet(pk)


# 停止
def stop():
    pk = BothSteppingMotorPacket(rand())
    pk.locked = False
    pk.direction = BothSteppingMotorPacket.ROTATE_LEFT_RETURN
    pk.type = BothSteppingMotorPacket.DATA_TYPE_4
    connection_manager.data_packet(pk)


# センサを計測する
def measure(method):
    thread = threading.Thread(target=method)
    thread.start()


# 壁との距離を計測し、実行結果をmethodに返す
def measure_distance(method):
    global measuring_distance
    measuring_distance = True
    while measuring_distance:
        SensorManager() \
            .set_packet(MeasureDistanceToBallPacket(rand())) \
            .send() \
            .set_on_receive(lambda pk: method(pk))
        time.sleep(1)  # 計測間隔


# ライントレーサの値を計測し、実行結果をmethodに返す
def measure_line_tracer(method):
    global measuring_line_tracer
    measuring_line_tracer = True
    while measuring_line_tracer:
        SensorManager() \
            .set_packet(MeasureLineTracerPacket(rand())) \
            .send() \
            .set_on_receive(lambda pk: method(pk))
        time.sleep(1)  # 計測間隔


def stop_measuring_distance():
    global measuring_distance
    measuring_distance = False


def stop_measuring_line_tracer():
    global measuring_line_tracer
    measuring_line_tracer = False


# 1つの単浮動小数点数を8byteの配列に変換する
def create_filled_data1(a: float):
    return create_filled_data2(a, 0.0)


# 2つの単浮動小数点数を8byteの配列に変換する
def create_filled_data2(a: float, b: float):
    return struct.pack("f", a) + struct.pack("f", b)


# 2つの単浮動小数点数からなる8byteのbyte配列を長さ2のfloat配列に変換する
def divide_data(data):
    return [struct.unpack("f", bytes(data[0:4]))[0], struct.unpack("f", bytes(data[4:8]))[0]]


# ランダムなパケットIDを生成
def rand():
    return random.randint(1000, 9999)


