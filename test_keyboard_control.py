import rtde_control
import time
from pynput import keyboard

# 로봇 IP에 맞게 수정
rtde_c = rtde_control.RTDEControlInterface("192.168.1.100")

# 초기 기준 pose (예시)
base_pose = [-0.41444, 0.16316, 0.22722, 2.101, -2.321, -0.026]
MOVE_STEP = 0.005  # 한 번에 이동하는 오프셋 크기

# 현재 키 상태를 저장하는 집합
keys_pressed = set()

# 전역 오프셋 변수
dx, dy, dz = 0.0, 0.0, 0.0

def update_offsets():
    global dx, dy, dz
    # 초기화 후 현재 눌린 키에 따라 오프셋 결정
    dx, dy, dz = 0.0, 0.0, 0.0
    if 'up' in keys_pressed:
        dy += MOVE_STEP
    if 'down' in keys_pressed:
        dy -= MOVE_STEP
    if 'left' in keys_pressed:
        dx -= MOVE_STEP
    if 'right' in keys_pressed:
        dx += MOVE_STEP
    if 'o' in keys_pressed:
        dz -= MOVE_STEP
    if 'p' in keys_pressed:
        dz += MOVE_STEP
    # 'r' 키를 누른 경우에는 오프셋을 0으로 초기화하도록 처리할 수 있습니다.

def get_target_pose():
    # 기준 pose에 오프셋을 더한 pose 반환
    return [
        base_pose[0] + dx,
        base_pose[1] + dy,
        base_pose[2] + dz,
        base_pose[3],
        base_pose[4],
        base_pose[5],
    ]

def on_press(key):
    try:
        # 문자 키 처리
        if key.char == 'q':
            # q 키 누르면 종료
            return False
        elif key.char == 'r':
            # r 키 누르면 모든 키 상태 초기화 (오프셋 리셋)
            keys_pressed.clear()
        else:
            if key.char in ['o', 'p']:
                keys_pressed.add(key.char)
    except AttributeError:
        # 특수 키 처리 (방향키 등)
        if key == keyboard.Key.up:
            keys_pressed.add('up')
        elif key == keyboard.Key.down:
            keys_pressed.add('down')
        elif key == keyboard.Key.left:
            keys_pressed.add('left')
        elif key == keyboard.Key.right:
            keys_pressed.add('right')

def on_release(key):
    try:
        if key.char in ['o', 'p']:
            keys_pressed.discard(key.char)
    except AttributeError:
        if key == keyboard.Key.up:
            keys_pressed.discard('up')
        elif key == keyboard.Key.down:
            keys_pressed.discard('down')
        elif key == keyboard.Key.left:
            keys_pressed.discard('left')
        elif key == keyboard.Key.right:
            keys_pressed.discard('right')

def main():
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    try:
        # servoL 명령은 비블록킹 방식으로 목표 pose를 지속적으로 업데이트할 수 있습니다.
        while True:
            update_offsets()
            target_pose = get_target_pose()
            rtde_c.servoL(target_pose, 0.5, 0.3)  # 가속도 및 속도 값은 필요에 따라 조절
            # 10ms 정도의 짧은 주기로 명령 업데이트 (너무 짧으면 부하가 커질 수 있으므로 적절한 값을 선택)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("프로그램이 종료됩니다.")
    finally:
        listener.stop()
        rtde_c.stopScript()

if __name__ == '__main__':
    main()
