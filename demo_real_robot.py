"""
Usage:
(robodiff)$ python demo_real_robot.py -o <demo_save_dir> --robot_ip <ip_of_ur5>

Robot movement:
Move your SpaceMouse to move the robot EEF (locked in xy plane).
Press SpaceMouse right button to unlock z axis.
Press SpaceMouse left button to enable rotation axes.

Recording control:
Click the opencv window (make sure it's in focus).
Press "C" to start recording.
Press "S" to stop recording.
Press "Q" to exit program.
Press "Backspace" to delete the previously recorded episode.
"""

# %%
import time
from multiprocessing.managers import SharedMemoryManager
import click
import cv2
import numpy as np
import scipy.spatial.transform as st
from diffusion_policy.real_world.real_env import RealEnv
# from diffusion_policy.real_world.spacemouse_shared_memory import Spacemouse
from diffusion_policy.common.precise_sleep import precise_wait
from diffusion_policy.real_world.keystroke_counter import (
    KeystrokeCounter, Key, KeyCode
)
# nscl
from pynput import keyboard

@click.command()
@click.option('--output', '-o', required=True, help="Directory to save demonstration dataset.")
@click.option('--robot_ip', '-ri', required=True, help="UR5's IP address e.g. 192.168.1.100")
@click.option('--vis_camera_idx', default=0, type=int, help="Which RealSense camera to visualize.")
@click.option('--init_joints', '-j', is_flag=True, default=False, help="Whether to initialize robot joint configuration in the beginning.")
@click.option('--frequency', '-f', default=10, type=float, help="Control frequency in Hz.")
@click.option('--command_latency', '-cl', default=0.01, type=float, help="Latency between receiving SapceMouse command to executing on Robot in Sec.")
def main(output, robot_ip, vis_camera_idx, init_joints, frequency, command_latency):
    dt = 1/frequency

    # nscl
    MOVE_STEP = 0.005
    dx, dy = 0.0, 0.0

    def on_press(key):
        nonlocal MOVE_STEP
        nonlocal dx, dy
        if hasattr(key, 'char') and key.char:
            if key.char == 'v':
                MOVE_STEP = 0.001
            elif key.char == 'b':
                MOVE_STEP = 0.005
            elif key.char == 'n':
                MOVE_STEP = 0.02

        if key == keyboard.Key.up:
            dy = -MOVE_STEP
        elif key == keyboard.Key.down:
            dy = MOVE_STEP
        elif key == keyboard.Key.left:
            dx = MOVE_STEP
        elif key == keyboard.Key.right:
            dx = -MOVE_STEP
    
    def on_release(key):
        nonlocal dx, dy
        if key in [keyboard.Key.up, keyboard.Key.down]:
            dy =0.0
        if key in [keyboard.Key.left, keyboard.Key.right]:
            dx =0.0
    
    listener = keyboard.Listener(on_press = on_press, on_release=on_release)
    listener.start()

    


    with SharedMemoryManager() as shm_manager:
        with KeystrokeCounter() as key_counter, \
            RealEnv(
                output_dir=output, 
                robot_ip=robot_ip, 
                # recording resolution
                obs_image_resolution=(1280,720),
                frequency=frequency,
                init_joints=init_joints,
                enable_multi_cam_vis=True,
                record_raw_video=True,
                # number of threads per camera view for video recording (H.264)
                thread_per_video=3,
                # video recording quality, lower is better (but slower).
                video_crf=21,
                shm_manager=shm_manager
            ) as env:
            cv2.setNumThreads(1)

            # realsense exposure
            env.realsense.set_exposure(exposure=120, gain=0)
            # realsense white balance
            env.realsense.set_white_balance(white_balance=5900)

            time.sleep(1.0)
            print('Ready!')
            base_pose = [-0.285, 0.283, 0.06, 1.610, -2.682, -0.022]
            plan_time = time.time() + 2.0
            env.exec_actions([base_pose], [plan_time])


            # 간단히 "5초 이내"로 기다리면서 도달 여부 검사
            print("Moving to the base_pose, please wait...")
            start_block = time.time()
            while True:
                if time.time() - start_block > 5.0:
                    break  # 최대 5초만 기다림
                # 현재 로봇 위치
                state = env.get_robot_state()
                actual_pose = state['ActualTCPPose']  # length=6
                dist = np.linalg.norm(np.array(actual_pose[:3]) - np.array(base_pose[:3]))
                if dist < 0.01:
                    # 어느정도 도달했다고 가정
                    break
                time.sleep(0.05)
            print("Base pose reached (or timed out).")

            # target_pose = state['TargetTCPPose']
            # 로봇 현재 타겟 pose를 base_pose로 설정
            target_pose = np.array(base_pose, dtype=float, copy=True)
            t_start = time.monotonic()
            iter_idx = 0
            stop = False
            is_recording = False
            while not stop:
                # calculate timing
                t_cycle_end = t_start + (iter_idx + 1) * dt
                t_sample = t_cycle_end - command_latency
                t_command_target = t_cycle_end + dt

                # pump obs
                obs = env.get_obs()

                # handle key presses
                press_events = key_counter.get_press_events()
                for key_stroke in press_events:
                    if key_stroke == KeyCode(char='q'):
                        # Exit program
                        stop = True
                    elif key_stroke == KeyCode(char='c'):
                        # Start recording
                        env.start_episode(t_start + (iter_idx + 2) * dt - time.monotonic() + time.time())
                        key_counter.clear()
                        is_recording = True
                        print('Recording!')
                    elif key_stroke == KeyCode(char='s'):
                        # Stop recording
                        env.end_episode()
                        key_counter.clear()
                        is_recording = False
                        print('Stopped.')
                    elif key_stroke == Key.backspace:
                        # Delete the most recent recorded episode
                        if click.confirm('Are you sure to drop an episode?'):
                            env.drop_episode()
                            key_counter.clear()
                            is_recording = False
                        # delete
                stage = key_counter[Key.space]

                # visualize
                vis_img = obs[f'camera_{vis_camera_idx}'][-1,:,:,::-1].copy()
                episode_id = env.replay_buffer.n_episodes
                text = f'Episode: {episode_id}, Stage: {stage}'
                if is_recording:
                    text += ', Recording!'
                cv2.putText(
                    vis_img,
                    text,
                    (10,30),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=1,
                    thickness=2,
                    color=(255,255,255)
                )

                cv2.imshow('default', vis_img)
                cv2.pollKey()

                precise_wait(t_sample)
                # get teleop command
                
                dpos = np.array([dx, dy, 0.0], dtype = float)
                drot_xyz = np.array([0.0, 0.0, 0.0], dtype= float)
                

                drot = st.Rotation.from_euler('xyz', drot_xyz)
                target_pose[:3] += dpos
                target_pose[3:] = (drot * st.Rotation.from_rotvec(
                    target_pose[3:])).as_rotvec()

                # execute teleop command
                env.exec_actions(
                    actions=[target_pose], 
                    timestamps=[t_command_target-time.monotonic()+time.time()],
                    stages=[stage])
                precise_wait(t_cycle_end)
                iter_idx += 1

# %%
if __name__ == '__main__':
    main()
