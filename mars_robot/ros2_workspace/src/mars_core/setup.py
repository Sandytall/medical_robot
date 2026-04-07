from setuptools import setup
import os
from glob import glob

package_name = 'mars_core'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mars Robot Team',
    maintainer_email='dev@marsrobot.com',
    description='Core robot control and state management for Mars hospital robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'robot_controller = mars_core.robot_controller:main',
            'command_processor = mars_core.command_processor:main',
            'behavior_executor = mars_core.behavior_executor:main',
        ],
    },
)