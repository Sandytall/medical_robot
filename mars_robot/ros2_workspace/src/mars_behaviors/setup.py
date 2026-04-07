from setuptools import setup

package_name = 'mars_behaviors'

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
    description='Behavior implementations for Mars hospital robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'idle_behavior = mars_behaviors.idle_behavior:main',
            'follow_behavior = mars_behaviors.follow_behavior:main',
            'manual_control = mars_behaviors.manual_control:main',
        ],
    },
)