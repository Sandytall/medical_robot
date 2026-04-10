from setuptools import setup

package_name = 'mars_hardware'

setup(
    name=package_name,
    version='1.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Mars Robot Team',
    maintainer_email='dev@marsrobot.com',
    description='Hardware abstraction layer for Mars hospital robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Hardware nodes integrated into hardware_manager
            # Individual nodes can be added later if needed
        ],
    },
)