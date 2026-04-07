from setuptools import setup

package_name = 'mars_voice'

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
    description='Voice command processing for Mars hospital robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'wake_word_bridge = mars_voice.wake_word_bridge:main',
            'speech_processor = mars_voice.speech_processor:main',
            'tts_node = mars_voice.tts_node:main',
        ],
    },
)