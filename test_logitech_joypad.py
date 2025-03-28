import pygame
import sys

# pygame 초기화
pygame.init()
pygame.joystick.init()

# 연결된 조이스틱 수 확인
joystick_count = pygame.joystick.get_count()
if joystick_count == 0:
    print("연결된 조이스틱이 없습니다.")
    sys.exit()

# 첫 번째 조이스틱 선택 및 초기화
joystick = pygame.joystick.Joystick(0)
joystick.init()
print("연결된 조이스틱 이름:", joystick.get_name())

# 이벤트 루프: 입력 이벤트 읽기
try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYAXISMOTION:
                # 축 움직임 출력
                axis = event.axis
                value = event.value
                print(f"축 {axis} 움직임: {value:.3f}")
            elif event.type == pygame.JOYBUTTONDOWN:
                # 버튼 누름 출력
                print(f"버튼 {event.button} 눌림")
            elif event.type == pygame.JOYBUTTONUP:
                # 버튼 떼어짐 출력
                print(f"버튼 {event.button} 해제")
except KeyboardInterrupt:
    print("\n프로그램 종료")
finally:
    pygame.quit()
