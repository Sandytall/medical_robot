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

        # Note: All hardware control is integrated into robot_controller via HardwareManager
        # Note: All behaviors are integrated into robot_controller as modules
        # Note: Voice processing is handled by robot_controller and behavior_tree_executor
        # No additional standalone nodes needed - the architecture is monolithic by design
    ])