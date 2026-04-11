from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument(
            'robot_env',
            default_value='development',
            description='Robot environment (development/production)'
        ),

        DeclareLaunchArgument(
            'use_mock_hardware',
            default_value='true',
            description='Use mock hardware for development'
        ),

        # Core robot controller (includes command processing)
        Node(
            package='mars_core',
            executable='robot_controller',
            name='robot_controller',
            output='screen',
            parameters=[{
                'robot_env': LaunchConfiguration('robot_env'),
                'use_mock_hardware': LaunchConfiguration('use_mock_hardware'),
            }]
        ),

        # Behavior tree executor
        Node(
            package='mars_core',
            executable='behavior_tree_executor',
            name='behavior_tree_executor',
            output='screen'
        ),

        # Hardware nodes
        Node(
            package='mars_hardware',
            executable='camera_node',
            name='camera_node',
            output='screen'
        ),

        Node(
            package='mars_hardware',
            executable='motor_node',
            name='motor_node',
            output='screen'
        ),

        Node(
            package='mars_hardware',
            executable='servo_node',
            name='servo_node',
            output='screen'
        ),

        Node(
            package='mars_hardware',
            executable='audio_node',
            name='audio_node',
            output='screen'
        ),

        Node(
            package='mars_hardware',
            executable='display_node',
            name='display_node',
            output='screen'
        ),

        # Voice processing nodes
        Node(
            package='mars_voice',
            executable='wake_word_bridge',
            name='wake_word_bridge',
            output='screen'
        ),

        Node(
            package='mars_voice',
            executable='speech_processor',
            name='speech_processor',
            output='screen'
        ),

        Node(
            package='mars_voice',
            executable='tts_node',
            name='tts_node',
            output='screen'
        ),

        # Behavior nodes
        Node(
            package='mars_behaviors',
            executable='idle_behavior',
            name='idle_behavior',
            output='screen'
        ),

        Node(
            package='mars_behaviors',
            executable='follow_behavior',
            name='follow_behavior',
            output='screen'
        ),

        Node(
            package='mars_behaviors',
            executable='manual_control',
            name='manual_control',
            output='screen'
        ),
    ])